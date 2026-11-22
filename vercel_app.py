"""Entrada hospedada com área privada e demonstração pública."""
import os
from datetime import date

from flask import Blueprint, abort, current_app, g, jsonify, redirect, request, url_for

from acesso import carregar_sessao, instalar_acesso, origem_publica
from build_vercel import pagina_publica
from dashboard import criar_app
from estado_publico import validar_estado
from financeiro import demonstracao, validar_lancamento, realizar
from gestao import editar, lixeira
from repositorio_supabase import ConflitoFinanceiro, RepositorioHospedado
from supabase_api import ErroSupabase, Supabase


demo = Blueprint('demo', __name__)


@demo.get('/demo')
def pagina_demo():
    return pagina_publica()


@demo.get('/api/demo/dashboard')
def dashboard_demo():
    g.demo_estado = demonstracao()
    return current_app.view_functions['dados']()


def estado_do_navegador():
    """Valida a lista pessoal sem gravar ou compartilhar estado no servidor."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValueError('Informe um objeto com os lançamentos.')
    if 'estado' in body:
        estado = validar_estado(body['estado'])
        return body, estado, []
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


@demo.post('/api/demo/dashboard')
def dashboard_navegador():
    _, g.demo_estado, _ = estado_do_navegador()
    resposta = current_app.view_functions['dados']()
    payload = resposta.get_json()
    payload['estado_navegador'] = g.demo_estado
    resposta.set_data(current_app.json.dumps(payload))
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@demo.post('/api/demo/lancamentos')
def lancamento_navegador():
    body, estado, novos = estado_do_navegador()
    if len(novos) >= 1000:
        raise ValueError('Limite de 1000 lançamentos neste navegador atingido.')
    novo = validar_lancamento(body.get('novo'), estado)
    resposta = jsonify(lancamentos=[*novos, novo])
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta, 201


@demo.post('/api/demo/acao')
def acao_navegador():
    body, estado, _ = estado_do_navegador()
    action = body.get('acao')
    values = body.get('dados', {})
    ident = body.get('id')
    collection = body.get('colecao', 'lancamentos')
    if collection not in {'lancamentos', 'recorrencias'}:
        raise ValueError('Cadastro não permitido.')
    if action == 'criar':
        if len(estado[collection]) >= (200 if collection == 'recorrencias' else 2000):
            raise ValueError('Limite de registros atingido.')
        item = validar_lancamento(values, estado, collection == 'recorrencias')
        estado[collection].append(item)
    elif action == 'realizar':
        item = realizar(estado, ident)
    elif action == 'alternar':
        item = next((r for r in estado['recorrencias'] if r['id'] == ident and not r.get('excluido')), None)
        if item is None:
            raise ValueError('Recorrência não encontrada.')
        item['ativa'] = not item['ativa']
    elif action == 'editar':
        item = editar(estado, collection, ident, values)
    elif action == 'lixeira':
        if not isinstance(values, dict):
            raise ValueError('Campos inválidos.')
        item = lixeira(estado, collection, ident, values.get('restaurar') is True)
    else:
        raise ValueError('Ação inválida.')
    resposta = jsonify(estado=estado, item=item)
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


def criar_app_hospedado(supabase=None, url=None, *, seguro=True):
    origem = origem_publica(url)
    app = criar_app(RepositorioHospedado(supabase), publicar_index=False)
    if origem and seguro:
        app.config['INVIEW_PUBLIC_URL'] = origem
    instalar_acesso(app, supabase, origem, seguro)
    app.register_blueprint(demo)

    @app.get('/app')
    def area_privada():
        return app.send_static_file('index.html')

    @app.before_request
    def proteger_area_privada():
        if request.endpoint == 'static' and request.view_args['filename'] == 'index.html':
            abort(404)
        if request.blueprint in {'demo', 'acesso'} or request.endpoint is None:
            return None
        if request.endpoint != 'area_privada' and not request.path.startswith('/api/'):
            return None
        if not (supabase and origem and carregar_sessao(supabase)):
            if request.endpoint == 'area_privada':
                return redirect(url_for('acesso.entrada'))
            return jsonify(erro='Entre para acessar seu espaço financeiro.'), 401
        if request.endpoint in {'analisar', 'confirmar_pdf', 'documento', 'espaco'}:
            return jsonify(erro='Esta função está disponível na versão local do Inview.'), 404

    @app.after_request
    def cache_hospedado(resposta):
        if request.endpoint != 'static':
            resposta.headers['Cache-Control'] = 'private, no-store'
            resposta.headers['Referrer-Policy'] = 'no-referrer'
            resposta.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        if request.blueprint == 'acesso' and resposta.mimetype == 'text/html':
            resposta.headers['Content-Security-Policy'] = (
                "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
        return resposta

    @app.errorhandler(ConflitoFinanceiro)
    def conflito(exc):
        return jsonify(erro='Seus dados mudaram em outra sessão. Recarregue e confirme a operação novamente.'), 409

    @app.errorhandler(ErroSupabase)
    def indisponivel(exc):
        if exc.status == 429:
            return jsonify(erro='Muitas tentativas. Aguarde alguns minutos e tente novamente.'), 429
        return jsonify(erro='O serviço está temporariamente indisponível. Tente novamente.'), 503

    return app


url = os.getenv('INVIEW_PUBLIC_URL')
app = criar_app_hospedado(Supabase.do_ambiente(), url, seguro=not (url and url.startswith('http://')))
