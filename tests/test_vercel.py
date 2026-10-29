import json

import pytest

from vercel_app import app


def test_demo_nao_acessa_arquivos_pessoais(monkeypatch):
    from repositorio_financeiro import Repositorio
    def proibido(*args, **kwargs):
        raise AssertionError('A demo pública não pode acessar o repositório persistente')
    monkeypatch.setattr(Repositorio, 'transacao', proibido)
    client = app.test_client()
    client.set_cookie('inview_espaco', 'local')
    assert client.get('/').status_code == 200
    assert b'public-demo.js' in client.get('/').data
    result = client.get('/api/dashboard')
    assert result.status_code == 200
    assert result.json['modo'] == 'demo'
    assert result.json['documentos'] == []
    assert json.loads(client.get('/api/backup').data)['documentos'] == []


@pytest.mark.parametrize('method,path', [
    ('POST', '/api/lancamentos'), ('POST', '/api/espaco'),
    ('POST', '/api/pdf/extrair'), ('POST', '/api/pdf/confirmar'),
    ('PUT', '/api/contas/principal'), ('POST', '/api/recorrencias/id/alternar'),
    ('DELETE', '/api/contas/principal'),
])
def test_mutacoes_bloqueadas(method, path):
    response = app.test_client().open(path, method=method, headers={'X-Inview': 'local'}, json={})
    assert response.status_code == 403
    assert 'somente para consulta' in response.json['erro']


def test_build_publica_apenas_interface(tmp_path, monkeypatch):
    import build_vercel
    from shutil import copytree
    copytree(build_vercel.ROOT / 'web', tmp_path / 'web')
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'segredo.json').write_text('privado')
    monkeypatch.setattr(build_vercel, 'ROOT', tmp_path)
    build_vercel.build()
    public = tmp_path / 'public'
    assert (public / 'assets' / 'app.js').exists()
    assert (public / 'assets' / 'brand' / 'icon.svg').exists()
    assert not (public / 'data').exists()
    html = (public / 'index.html').read_text(encoding='utf-8')
    assert 'public-demo.js' in html
    assert 'neste navegador' in html
    assert html.index('public-demo.js') < html.index('/assets/app.js')


@pytest.mark.parametrize('tipo,sinal', [('entrada', 1), ('saida', -1)])
@pytest.mark.parametrize('status', ['previsto', 'realizado'])
def test_novo_lancamento_publico_recalcula_sem_compartilhar(tipo, sinal, status):
    from decimal import Decimal
    from financeiro import hoje, demonstracao
    client = app.test_client()
    headers = {'X-Inview': 'local'}
    before = client.get('/api/dashboard').json
    item = dict(tipo=tipo, valor='123.45', descricao='Teste navegador',
                categoria='Outros', conta_id=demonstracao()['contas'][0]['id'],
                data=hoje().isoformat(), status=status)
    response = client.post('/api/demo/lancamentos', headers=headers,
                           json={'lancamentos': [], 'novo': item})
    assert response.status_code == 201
    items = response.json['lancamentos']
    assert len(items) == 1
    assert items[0]['tipo'] == tipo and items[0]['status'] == status
    # O navegador reenvia a lista salva inclusive após recarregar a página.
    for _ in range(2):
        after = client.post('/api/demo/dashboard', headers=headers,
                            json={'lancamentos': items}).json
        delta = Decimal('123.45') * sinal
        assert Decimal(after['saldo_final']) == Decimal(before['saldo_final']) + delta
        assert Decimal(after['saldo_atual']) == Decimal(before['saldo_atual']) + (delta if status == 'realizado' else 0)
    other = app.test_client().get('/api/dashboard').json
    assert other['saldo_atual'] == before['saldo_atual']
    assert other['saldo_final'] == before['saldo_final']


def test_publico_rejeita_lista_invalida_e_origem_externa():
    client = app.test_client()
    assert client.post('/api/demo/dashboard', json={'lancamentos': []}).status_code == 403
    headers = {'X-Inview': 'local'}
    for items in ['errado', [{}], [{}] * 1001]:
        assert client.post('/api/demo/dashboard', headers=headers,
                           json={'lancamentos': items}).status_code == 400
    assert client.post('/api/demo/dashboard', headers={**headers, 'Origin': 'https://outro.example'},
                       json={'lancamentos': []}).status_code == 403


def test_pagar_receber_recorrencias_e_recarga(monkeypatch):
    from datetime import date
    from decimal import Decimal
    import financeiro
    monkeypatch.setattr(financeiro, 'hoje', lambda: date(2026, 10, 28))
    client = app.test_client()
    headers = {'X-Inview': 'local'}
    def dashboard(state=None):
        r = client.post('/api/demo/dashboard', headers=headers,
                        json={'estado': state} if state else {'lancamentos': []})
        assert r.status_code == 200, r.json
        return r.json
    initial = dashboard()
    state = initial['estado_navegador']
    def action(**values):
        nonlocal state
        r = client.post('/api/demo/acao', headers=headers, json={'estado':state, **values})
        assert r.status_code == 200, r.json
        state = r.json['estado']
        # Simula recarga com o estado devolvido à persistência do navegador.
        state = dashboard(state)['estado_navegador']
        return r.json['item']
    action(acao='realizar', id='icloud:2026-10-29')
    action(acao='realizar', id='freela:2026-10-30')
    current = dashboard(state)
    assert Decimal(current['saldo_atual']) == Decimal(initial['saldo_atual']) - Decimal('14.90') + Decimal('1800.00')
    r = client.post('/api/demo/acao', headers=headers, json={'estado':state,'acao':'realizar','id':'icloud:2026-10-29'})
    assert r.status_code == 400
    action(acao='alternar', id='aluguel')
    assert not next(r for r in state['recorrencias'] if r['id']=='aluguel')['ativa']
    action(acao='alternar', id='aluguel')
    assert next(r for r in state['recorrencias'] if r['id']=='aluguel')['ativa']
    item = action(acao='criar', colecao='lancamentos', dados=dict(tipo='saida', valor='5000.00',
        descricao='MacBook', categoria='Outros', conta_id='principal', data='2026-10-28',status='previsto'))
    action(acao='realizar', id=item['id'])
    action(acao='editar', id=item['id'], colecao='lancamentos', dados=dict(item, valor='4900.00',status='realizado'))
    action(acao='lixeira', id=item['id'], colecao='lancamentos')
    assert dashboard(state)['lixeira']
    action(acao='lixeira', id=item['id'], colecao='lancamentos', dados={'restaurar':True})
    assert not dashboard(state)['lixeira']
    assert dashboard()['saldo_atual'] == initial['saldo_atual']


def test_migracao_preserva_lancamento_existente_e_cria_recorrencia():
    from financeiro import hoje
    client = app.test_client()
    headers = {'X-Inview':'local'}
    saved = dict(id='a'*32, tipo='entrada',valor='100.00',descricao='Já salvo',categoria='Outros',
                 conta_id='principal',data=hoje().isoformat(),status='previsto')
    response = client.post('/api/demo/dashboard', headers=headers,json={'lancamentos':[saved]})
    state = response.json['estado_navegador']
    assert any(r['id']==saved['id'] for r in state['lancamentos'])
    response = client.post('/api/demo/acao',headers=headers,json={'estado':state,'acao':'criar',
        'colecao':'recorrencias','dados':dict(tipo='saida',valor='50.00',descricao='Assinatura',
        categoria='Assinaturas',conta_id='principal',dia=15,inicio=hoje().isoformat())})
    assert response.status_code == 200
    state = response.json['estado']
    assert client.post('/api/demo/dashboard',headers=headers,json={'estado':state}).status_code == 200
