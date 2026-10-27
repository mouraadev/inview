from datetime import date
import pytest
import financeiro as f
from dashboard import criar_app
from repositorio_financeiro import Repositorio
from gestao import editar, lixeira


@pytest.fixture
def estado(monkeypatch):
    monkeypatch.setattr(f, 'hoje', lambda: date(2026, 10, 27))
    return f.demonstracao()


def test_editar_excluir_restaurar_ocorrencia(estado):
    chave = 'spotify:2026-10-28'
    item = next(t for t in f.ocorrencias(estado, date(2026, 10, 31)) if t['id'] == chave)
    editar(estado, 'lancamentos', chave, dict(item, valor='30.00', data='2026-10-30'))
    assert f.resumo(estado, '2026-10')['saldo_final'] == '20389.55'
    assert not any(t['id'] == chave for t in f.ocorrencias(estado, date(2026, 10, 31)))
    lixeira(estado, 'lancamentos', chave)
    assert f.resumo(estado, '2026-10')['saldo_final'] == '20419.55'
    lixeira(estado, 'lancamentos', chave, True)
    assert f.resumo(estado, '2026-10')['saldo_final'] == '20389.55'


def test_editar_regra_nao_duplica_mes_confirmado(estado):
    f.realizar(estado, 'spotify:2026-10-28')
    regra = next(r for r in estado['recorrencias'] if r['id'] == 'spotify')
    editar(estado, 'recorrencias', 'spotify', dict(regra, dia=30, valor='50.00'))
    futuros = f.ocorrencias(estado, date(2026, 11, 30))
    assert not any(t['id'] == 'spotify:2026-10-30' for t in futuros)
    assert next(t for t in futuros if t['id'] == 'spotify:2026-11-30')['valor'] == '50.00'


def test_conta_com_historico_nao_pode_sumir(estado):
    with pytest.raises(ValueError):
        lixeira(estado, 'contas', 'principal')
    conta = estado['contas'][0]
    with pytest.raises(ValueError):
        editar(estado, 'contas', conta['id'], dict(conta, moeda='USD'))
    with pytest.raises(ValueError):
        editar(estado, 'contas', conta['id'], dict(conta, data_inicial='2026-10-20'))


def test_api_crud_e_backup(tmp_path, estado):
    repo = Repositorio(caminho=tmp_path/'teste.json')
    with repo.transacao() as e:
        e.update(estado)
    client = criar_app(repo).test_client()
    h = {'X-Inview': 'local'}
    regra = estado['recorrencias'][0]
    assert client.put('/api/recorrencias/salario', json=dict(regra, valor='9000.00'), headers=h).status_code == 200
    assert client.post('/api/recorrencias/salario/lixeira', json={}, headers=h).status_code == 200
    dados = client.get('/api/dashboard?mes=2026-10').get_json()
    assert dados['lixeira'][0]['id'] == 'salario'
    assert len(dados['recorrencias']) == 5
    assert client.post('/api/recorrencias/salario/lixeira', json={'restaurar':True}, headers=h).status_code == 200
    assert client.get('/api/backup').get_json()['recorrencias'][0]['valor'] == '9000.00'
    assert client.post('/api/lancamentos', json=[], headers=h).status_code == 400


def test_local_vazio_separado(tmp_path):
    repo = Repositorio('local', tmp_path/'pessoal.json')
    with repo.transacao() as e:
        assert not e['recorrencias'] and not e['lancamentos']
        assert e['contas'][0]['saldo_inicial'] == '0.00'
    assert repo.caminho.exists()
