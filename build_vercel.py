"""Prepara os assets públicos do Inview para a Vercel."""
from pathlib import Path
from shutil import copytree

ROOT = Path(__file__).resolve().parent


def pagina_publica():
    html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<script defer src="/assets/app.js">', '<script defer src="/assets/public-demo.js"></script><script defer src="/assets/app.js">')
    html = html.replace('</nav>', '</nav>\n    <a class="demo-login" href="/">Entrar</a>', 1)
    return html.replace(
        'Dados fictícios para explorar. Suas alterações ficam salvas neste computador.',
        'Demonstração com dados fictícios. Lançamentos, pagamentos e recorrências ficam salvos apenas neste navegador. '
        'Sem sincronização; limpar os dados do navegador apaga seus lançamentos.')


def build():
    public = ROOT / 'public'
    # O Flask precisa receber a raiz para decidir se mostra o login ou abre o espaço.
    (public / 'index.html').unlink(missing_ok=True)
    (public / 'assets' / 'index.html').unlink(missing_ok=True)
    copytree(ROOT / 'web', public / 'assets', dirs_exist_ok=True,
             ignore=lambda pasta, _: {'index.html'} if Path(pasta) == ROOT / 'web' else set())


if __name__ == '__main__':
    build()
