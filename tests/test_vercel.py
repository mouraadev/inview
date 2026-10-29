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
    assert 'somente para consulta' in html
