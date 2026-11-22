"""Cliente HTTP sem sessão global para Auth e Data API do Supabase."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ErroSupabase(Exception):
    def __init__(self, status, codigo=''):
        self.status = status
        self.codigo = codigo


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Supabase:
    def __init__(self, url, chave):
        origem = urlsplit(url)
        if origem.scheme != 'https' or not origem.netloc or origem.path not in {'', '/'} or origem.query or origem.fragment or origem.username:
            raise ValueError('SUPABASE_URL deve ser a origem HTTPS do projeto Supabase.')
        if not chave.startswith('sb_publishable_'):
            raise ValueError('Use uma chave publicável em SUPABASE_PUBLISHABLE_KEY.')
        self.url = url.rstrip('/')
        self.chave = chave
        self.opener = build_opener(SemRedirecionamento())

    @classmethod
    def do_ambiente(cls):
        url = os.getenv('SUPABASE_URL')
        chave = os.getenv('SUPABASE_PUBLISHABLE_KEY')
        return cls(url, chave) if url and chave else None

    def requisitar(self, metodo, rota, *, token=None, params=None, dados=None, prefer=None):
        url = self.url + rota
        if params:
            url += '?' + urlencode(params)
        cabecalhos = {'apikey': self.chave, 'Accept': 'application/json'}
        if token:
            cabecalhos['Authorization'] = f'Bearer {token}'
        if dados is not None:
            cabecalhos['Content-Type'] = 'application/json'
            dados = json.dumps(dados, ensure_ascii=False).encode('utf-8')
        if prefer:
            cabecalhos['Prefer'] = prefer
        mensagem = Request(url, dados, cabecalhos, method=metodo)
        try:
            with self.opener.open(mensagem, timeout=8) as resposta:
                conteudo = resposta.read()
                return json.loads(conteudo) if conteudo else None
        except HTTPError as exc:
            with exc:
                try:
                    erro = json.load(exc)
                except (UnicodeError, ValueError):
                    erro = {}
            codigo = erro.get('code', erro.get('error_code', '')) if isinstance(erro, dict) else ''
            raise ErroSupabase(exc.code, codigo) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ErroSupabase(503) from None
