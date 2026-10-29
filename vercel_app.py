"""Entrada da Vercel: demonstração pública sem persistência nem dados pessoais."""
from contextlib import contextmanager

from flask import jsonify, request

from build_vercel import pagina_publica
from dashboard import criar_app
from financeiro import demonstracao


class DemonstracaoPublica:
    modo = 'demo'

    @contextmanager
    def transacao(self, gravar=True):
        # Estado novo por requisição: não lê JSON local, MySQL ou cookies.
        yield demonstracao()


app = criar_app(repositorio=DemonstracaoPublica())
app.view_functions['index'] = pagina_publica


def somente_consulta():
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        return jsonify(erro='Demonstração pública somente para consulta. '
                       'Execute o Inview localmente para importar faturas e salvar alterações.'), 403


# Bloqueia mutações antes de analisar uploads ou executar qualquer rota.
app.before_request_funcs.setdefault(None, []).insert(0, somente_consulta)
