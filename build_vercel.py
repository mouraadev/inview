"""Prepara os arquivos públicos da demonstração hospedada na Vercel."""
from pathlib import Path
from shutil import copytree

ROOT = Path(__file__).resolve().parent


def pagina_publica():
    html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<script defer src="/assets/app.js">', '<script defer src="/assets/public-demo.js"></script><script defer src="/assets/app.js">')
    return html.replace(
        'Dados fictícios para explorar. Suas alterações ficam salvas neste computador.',
        'Demonstração com dados fictícios. Lançamentos, pagamentos e recorrências ficam salvos apenas neste navegador. '
        'Sem sincronização; limpar os dados do navegador apaga seus lançamentos.')


def build():
    public = ROOT / 'public'
    copytree(ROOT / 'web', public / 'assets', dirs_exist_ok=True)
    (public / 'index.html').write_text(pagina_publica(), encoding='utf-8')


if __name__ == '__main__':
    build()
