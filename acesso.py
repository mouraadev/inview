from base64 import urlsafe_b64encode
from hashlib import sha256
import re
from secrets import token_urlsafe
from urllib.parse import urlsplit

from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for

from supabase_api import ErroSupabase


ACESSO = 'inview_acesso'
RENOVACAO = 'inview_renovacao'
TROCA = 'inview_troca_senha'
VERIFICADOR_RECUPERACAO = 'inview_recuperacao'
CAMINHO_RECUPERACAO = '/api/auth/'
ROTA_TROCA = '/api/auth/senha'
AUTH = '/auth/v1'
MENSAGEM_LINK = 'Este link é inválido ou expirou. Solicite um novo para continuar.'


def origem_publica(url):
    if not url:
        return None
    parsed = urlsplit(url)
    local = parsed.hostname in {'localhost', '127.0.0.1'} and parsed.scheme == 'http'
    if ((parsed.scheme != 'https' and not local) or not parsed.netloc or parsed.username
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
        raise ValueError('INVIEW_PUBLIC_URL deve ser a origem HTTPS do Inview.')
    return url.rstrip('/')


def carregar_sessao(supabase):
    acesso = request.cookies.get(ACESSO)
    renovacao = request.cookies.get(RENOVACAO)
    if acesso:
        try:
            g.usuario = supabase.requisitar('GET', AUTH + '/user', token=acesso)
            g.token = acesso
            return True
        except ErroSupabase as exc:
            if exc.status not in {400, 401, 403}:
                raise
    if renovacao:
        try:
            sessao = supabase.requisitar('POST', AUTH + '/token', params={'grant_type': 'refresh_token'},
                                         dados={'refresh_token': renovacao})
        except ErroSupabase as exc:
            if exc.status not in {400, 401, 403, 422}:
                raise
        else:
            g.usuario = sessao['user']
            g.token = sessao['access_token']
            g.sessao = sessao
            return True
    if acesso or renovacao:
        g.sessao = None
    return False


def email_do_formulario(dados):
    email = dados.get('email')
    if not isinstance(email, str) or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+', email.strip()):
        raise ValueError('Informe um e-mail válido.')
    return email.strip()


def instalar_acesso(app, supabase, origem, seguro):
    auth = Blueprint('acesso', __name__)
    cookie = {'httponly': True, 'secure': seguro, 'samesite': 'Lax'}

    def corpo():
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ValueError('Informe os campos do formulário.')
        if request.content_length and request.content_length > 8192:
            raise ValueError('Os campos do formulário excedem o tamanho permitido.')
        return dados

    def tela(modo):
        return render_template('acesso.html', modo=modo,
                               disponivel=supabase is not None and origem is not None)

    @auth.get('/')
    def entrada():
        if supabase and origem and carregar_sessao(supabase):
            return redirect(url_for('area_privada'))
        return tela('entrar')

    @auth.get('/recuperar-senha')
    def recuperar():
        return tela('recuperar')

    @auth.get('/convite')
    def convite():
        return tela('invite')

    @auth.get('/nova-senha')
    def nova_senha():
        return tela('recovery')

    @auth.before_request
    def auth_configurado():
        if request.method == 'POST' and request.endpoint != 'acesso.sair' and not (supabase and origem):
            return jsonify(erro='O acesso privado ainda não está disponível neste ambiente.'), 503

    @auth.post('/api/auth/entrar')
    def entrar():
        dados = corpo()
        email = email_do_formulario(dados)
        senha = dados.get('senha')
        if not isinstance(senha, str) or not 1 <= len(senha) <= 1024:
            raise ValueError('Informe sua senha.')
        try:
            g.sessao = supabase.requisitar('POST', AUTH + '/token', params={'grant_type': 'password'},
                                           dados={'email': email, 'password': senha})
        except ErroSupabase as exc:
            if exc.status in {400, 401, 403, 422}:
                return jsonify(erro='E-mail ou senha incorretos. Confira os dados e tente novamente.'), 401
            raise
        return jsonify(destino=url_for('area_privada'))

    @auth.post('/api/auth/recuperar')
    def pedir_recuperacao():
        email = email_do_formulario(corpo())
        verificador = request.cookies.get(VERIFICADOR_RECUPERACAO, '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', verificador):
            verificador = token_urlsafe(32)
        desafio = urlsafe_b64encode(sha256(verificador.encode()).digest()).rstrip(b'=').decode()
        try:
            supabase.requisitar('POST', AUTH + '/recover', dados={
                                    'email': email, 'code_challenge': desafio, 'code_challenge_method': 's256'},
                                params={'redirect_to': origem + url_for('acesso.nova_senha')})
        except ErroSupabase as exc:
            if exc.status not in {400, 403, 404, 422, 429}:
                raise
        resposta = jsonify(mensagem='Se houver uma conta para esse e-mail, você receberá um link. '
                                   'Abra-o no mesmo navegador em que pediu a recuperação.')
        resposta.set_cookie(VERIFICADOR_RECUPERACAO, verificador, max_age=3600, path=CAMINHO_RECUPERACAO, **cookie)
        return resposta

    @auth.post(ROTA_TROCA)
    def senha():
        dados = corpo()
        senha_nova = dados.get('senha')
        tipo = dados.get('tipo')
        if not isinstance(senha_nova, str) or len(senha_nova) < 12 or len(senha_nova.encode(errors='replace')) > 72:
            raise ValueError('Use pelo menos 12 caracteres, com até 72 bytes.')
        if tipo not in ('invite', 'recovery'):
            raise ValueError(MENSAGEM_LINK)

        token_hash = dados.get('token_hash')
        codigo = dados.get('codigo')
        credencial = token_hash or codigo
        if credencial:
            if not isinstance(credencial, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,256}', credencial):
                raise ValueError(MENSAGEM_LINK)
            try:
                if token_hash:
                    sessao = supabase.requisitar('POST', AUTH + '/verify', dados={'token_hash': token_hash, 'type': tipo})
                else:
                    if tipo != 'recovery':
                        raise ValueError(MENSAGEM_LINK)
                    verificador = request.cookies.get(VERIFICADOR_RECUPERACAO, '')
                    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', verificador):
                        raise ValueError('Solicite um novo link e abra-o no mesmo navegador.')
                    sessao = supabase.requisitar('POST', AUTH + '/token', params={'grant_type': 'pkce'},
                                                 dados={'auth_code': codigo, 'code_verifier': verificador})
            except ErroSupabase as exc:
                if exc.status in {400, 401, 403, 404, 422}:
                    return jsonify(erro=MENSAGEM_LINK), 400
                raise
            novo_token = sessao['access_token']
        else:
            novo_token = request.cookies.get(TROCA)
            if not novo_token:
                raise ValueError(MENSAGEM_LINK)

        try:
            supabase.requisitar('PUT', AUTH + '/user', token=novo_token, dados={'password': senha_nova})
        except ErroSupabase as exc:
            if exc.status in {401, 403}:
                resposta = jsonify(erro=MENSAGEM_LINK)
                resposta.delete_cookie(TROCA, path=ROTA_TROCA, **cookie)
                return resposta, 400
            if exc.status in {400, 422}:
                resposta = jsonify(erro='Escolha uma senha diferente e tente novamente.', verificado=True)
                status = 400
            else:
                resposta = jsonify(erro='Não foi possível salvar a senha agora. Tente novamente.', verificado=True)
                status = 503
            if credencial:
                resposta.set_cookie(TROCA, novo_token, max_age=600, path=ROTA_TROCA, **cookie)
            return resposta, status

        encerrar_remota(supabase, novo_token)
        resposta = jsonify(destino=url_for('acesso.entrada', senha='definida'))
        resposta.delete_cookie(TROCA, path=ROTA_TROCA, **cookie)
        g.sessao = None
        return resposta

    @auth.post('/api/auth/sair')
    def sair():
        try:
            if supabase and carregar_sessao(supabase):
                encerrar_remota(supabase, g.token)
        except ErroSupabase:
            pass
        g.sessao = None
        return jsonify(destino=url_for('acesso.entrada'))

    @app.after_request
    def atualizar_cookies(resposta):
        if 'sessao' in g:
            if g.sessao:
                resposta.set_cookie(ACESSO, g.sessao['access_token'], **cookie)
                resposta.set_cookie(RENOVACAO, g.sessao['refresh_token'], **cookie)
            else:
                resposta.delete_cookie(ACESSO, **cookie)
                resposta.delete_cookie(RENOVACAO, **cookie)
        return resposta

    app.register_blueprint(auth)


def encerrar_remota(supabase, token):
    try:
        supabase.requisitar('POST', AUTH + '/logout', token=token, params={'scope': 'local'})
    except ErroSupabase:
        # A sessão no navegador é encerrada mesmo se a revogação remota falhar.
        pass
