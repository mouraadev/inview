"""Entrada da Vercel: demonstração com lançamentos salvos no navegador."""
from contextlib import contextmanager

from flask import g, jsonify, request
from datetime import date

from build_vercel import pagina_publica
from dashboard import criar_app
from financeiro import demonstracao, validar_lancamento


class DemonstracaoPublica:
    modo = 'demo'

    @contextmanager
    def transacao(self, gravar=True):
        # Estado novo por requisição: não lê JSON local, MySQL ou cookies.
        yield getattr(g, 'demo_estado', None) or demonstracao()


app = criar_app(repositorio=DemonstracaoPublica())
app.view_functions['index'] = pagina_publica


def somente_consulta():
    if request.method == 'POST' and request.path in {'/api/demo/dashboard', '/api/demo/lancamentos'}:
        return None
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        return jsonify(erro='Demonstração pública somente para consulta. '
                       'Execute o Inview localmente para importar faturas e salvar alterações.'), 403


# Permite apenas validação/cálculo sem persistência; bloqueia outras mutações.
app.before_request_funcs.setdefault(None, []).insert(0, somente_consulta)


def estado_do_navegador():
    """Valida a lista pessoal sem gravar ou compartilhar estado no servidor."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError('Informe um objeto com os lançamentos.')
    items = body.get('lancamentos', [])
    if not isinstance(items, list) or len(items) > 1000:
        raise ValueError('Informe até 1000 lançamentos por navegador.')
    estado = demonstracao()
    novos = []
    ids = {i['id'] for i in estado['lancamentos']}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Lançamento salvo inválido.')
        ident = item.get('id', '')
        if not isinstance(ident, str) or len(ident) != 32 or any(c not in '0123456789abcdef' for c in ident) or ident in ids:
            raise ValueError('Identificador de lançamento inválido ou repetido.')
        try:
            dia = date.fromisoformat(item.get('data', ''))
        except (TypeError, ValueError):
            raise ValueError('Data do lançamento salvo inválida.')
        # Mantém movimentos salvos quando o mês da demonstração muda.
        for conta in estado['contas']:
            if conta['id'] == item.get('conta_id'):
                conta['data_inicial'] = min(conta['data_inicial'], dia.isoformat())
        validado = validar_lancamento(item, estado)
        validado['id'] = ident
        ids.add(ident)
        novos.append(validado)
    estado['lancamentos'].extend(novos)
    return body, estado, novos


@app.post('/api/demo/dashboard')
def dashboard_navegador():
    _, g.demo_estado, _ = estado_do_navegador()
    resposta = app.view_functions['dados']()
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@app.post('/api/demo/lancamentos')
def lancamento_navegador():
    body, estado, novos = estado_do_navegador()
    if len(novos) >= 1000:
        raise ValueError('Limite de 1000 lançamentos neste navegador atingido.')
    novo = validar_lancamento(body.get('novo'), estado)
    resposta = jsonify(lancamentos=[*novos, novo])
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta, 201
