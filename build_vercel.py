"""Prepara os arquivos públicos da demonstração hospedada na Vercel."""
from pathlib import Path
from shutil import copytree

ROOT = Path(__file__).resolve().parent


def pagina_publica():
    html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    html = html.replace('</head>', '<script defer src="/assets/public-demo.js"></script></head>')
    return html.replace(
        'Dados fictícios para explorar. Suas alterações ficam salvas neste computador.',
        'Demonstração pública com dados fictícios, somente para consulta. '
        'Para importar faturas e salvar alterações, execute o projeto localmente.')


def build():
    public = ROOT / 'public'
    copytree(ROOT / 'web', public / 'assets', dirs_exist_ok=True)
    (public / 'index.html').write_text(pagina_publica(), encoding='utf-8')


if __name__ == '__main__':
    build()
