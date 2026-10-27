from datetime import date
from decimal import Decimal

import pytest

import financeiro as f
from dashboard import criar_app
from repositorio_financeiro import Repositorio


@pytest.fixture
def estado(monkeypatch):
    monkeypatch.setattr(f, 'hoje', lambda: date(2026, 10, 27))
    return f.demonstracao()


def test_previsao_sem_alterar_saldo_real(estado):
    r = f.resumo(estado, '2026-10')
    assert Decimal(r['saldo_atual']) == Decimal('18634.45')
    assert Decimal(r['saldo_final']) == Decimal('20397.65')
    assert len(r['proximos']) == 3
    assert f.resumo(estado, '2026-10', moeda='USD')['saldo_atual'] == '0'
    assert f.resumo(estado, '2026-10', conta_id='reserva')['saldo_final'] == '8200.00'


def test_confirmacao_unica_preserva_previsao(estado):
    antes = f.resumo(estado, '2026-10')
    chave = 'spotify:2026-10-28'
    f.realizar(estado, chave)
    depois = f.resumo(estado, '2026-10')
    assert depois['saldo_final'] == antes['saldo_final']
    assert Decimal(depois['saldo_atual']) == Decimal(antes['saldo_atual']) - Decimal('21.90')
    with pytest.raises(ValueError):
        f.realizar(estado, chave)


def test_pausa_e_dia_31(estado):
    assert f.mes_data('2028-02', 31) == date(2028, 2, 29)
    regra = next(r for r in estado['recorrencias'] if r['id'] == 'spotify')
    regra['ativa'] = False
    assert f.resumo(estado, '2026-10')['saldo_final'] == '20419.55'
    assert not any(t['id'].startswith('spotify:') for t in f.ocorrencias(estado, date(2026, 11, 30)))


def test_vencimento_hoje_no_ultimo_dia(monkeypatch):
    monkeypatch.setattr(f, 'hoje', lambda: date(2026, 10, 31))
    e = f.vazio()
    e['lancamentos'] = [dict(id='a', conta_id='principal', descricao='Salário', categoria='Salário',
                             data='2026-10-31', tipo='entrada', valor='100.00', status='previsto')]
    r = f.resumo(e, '2026-10')
    assert Decimal(r['saldo_atual']) == 0
    assert r['saldo_final'] == '100.00'


def test_api_persistencia_e_validacao(tmp_path, estado):
    repo = Repositorio(caminho=tmp_path / 'teste.json')
    with repo.transacao() as e:
        e.update(estado)
    client = criar_app(repo).test_client()
    entrada = dict(descricao='Teste', tipo='saida', valor='12.34', categoria='Outros',
                   conta_id='principal', data='2026-10-28', status='previsto')
    assert client.post('/api/lancamentos', json=entrada).status_code == 403
    h = {'X-Inview': 'local'}
    assert client.post('/api/lancamentos', json=dict(entrada, valor='12.345'), headers=h).status_code == 400
    assert client.post('/api/lancamentos', json=entrada, headers=h).status_code == 201
    with Repositorio(caminho=repo.caminho).transacao(gravar=False) as e:
        assert e['lancamentos'][-1]['valor'] == '12.34'
    r = client.get('/api/dashboard?mes=2026-10').get_json()
    assert r['saldo_final'] == '20385.31'
    assert client.get('/').status_code == 200


def test_rollback_local(tmp_path, estado):
    repo = Repositorio(caminho=tmp_path / 'teste.json')
    with repo.transacao() as e:
        e.update(estado)
    with pytest.raises(ValueError), repo.transacao() as e:
        e['contas'].clear()
        raise ValueError('abortado')
    with repo.transacao(gravar=False) as e:
        assert len(e['contas']) == 2


def test_pdf_revisado_gera_previsao_e_bloqueia_reimportacao(tmp_path, estado):
    import json
    from io import BytesIO
    from pathlib import Path
    pdf = Path.home() / 'Downloads' / 'inview_invoice_01_brl.pdf'
    if not pdf.exists():
        pytest.skip('Amostra sintética indisponível')
    repo = Repositorio(caminho=tmp_path / 'pdf.json')
    with repo.transacao() as e:
        e.update(estado)
    client = criar_app(repo).test_client()
    revisao = dict(confirmado=True, formato='pt-BR', ordem='DMY', tipo='saida',
        categoria='Outros', conta_id='principal', data_prevista='2026-10-31',
        campos=dict(fornecedor='Aurora Dados Serviços Ltda.', numero_fatura='FAT-2026-001',
                    data_emissao='2026-10-01', moeda='BRL', total='3.325,00'))
    def enviar():
        return client.post('/api/pdf/confirmar', headers={'X-Inview': 'local'},
            data={'arquivo': (BytesIO(pdf.read_bytes()), pdf.name), 'revisao': json.dumps(revisao)})
    r = enviar()
    assert r.status_code == 201, r.get_json()
    assert r.get_json()['status'] == 'previsto'
    assert enviar().status_code == 400
    with repo.transacao(gravar=False) as e:
        assert len(e['documentos']) == 1
        assert f.resumo(e, '2026-10')['saldo_atual'] == '18634.45'
        ident = e['documentos'][0]['id']
    assert client.get('/api/documentos/' + ident).data == pdf.read_bytes()
