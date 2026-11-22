"""Prepara os assets públicos do Inview para a Vercel."""
from pathlib import Path
from shutil import copy2, copytree

ROOT = Path(__file__).resolve().parent


def pagina_publica():
    html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<script defer src="/assets/app.js">', '<script defer src="/assets/public-demo.js"></script><script defer src="/assets/app.js">')
    html = html.replace('</nav>', '</nav>\n    <a class="demo-login" href="/">Entrar</a>', 1)
    return html.replace(
        'Dados fictícios para explorar. Suas alterações ficam salvas neste computador.',
        'Demonstração com dados fictícios. Lançamentos, pagamentos e recorrências ficam salvos apenas neste navegador. '
        'Sem sincronização; limpar os dados do navegador apaga seus lançamentos.')


def publicar_leitor_pdf(destino):
    modulos = ROOT / 'node_modules'
    pdfjs = modulos / 'pdfjs-dist'
    tesseract = modulos / 'tesseract.js'
    core = modulos / 'tesseract.js-core'
    grupos = {
        'pdfjs': [(pdfjs / 'legacy' / 'build' / nome, nome) for nome in ('pdf.min.mjs', 'pdf.worker.min.mjs')]
                 + [(pdfjs / 'LICENSE', 'LICENSE')],
        'ocr': [(tesseract / 'dist' / nome, nome) for nome in
                ('tesseract.esm.min.js', 'worker.min.js', 'worker.min.js.LICENSE.txt')]
               + [(tesseract / 'LICENSE.md', 'LICENSE.md')],
        'ocr/core': [(core / nome, nome) for nome in ('LICENSE', 'tesseract-core-lstm.wasm.js',
                      'tesseract-core-simd-lstm.wasm.js', 'tesseract-core-relaxedsimd-lstm.wasm.js')],
        'ocr/idiomas': [(modulos / '@tesseract.js-data' / 'por' / '4.0.0_best_int' / 'por.traineddata.gz',
                        'por.traineddata.gz')],
    }
    for pasta, arquivos in grupos.items():
        (destino / pasta).mkdir(parents=True, exist_ok=True)
        for origem, nome in arquivos:
            copy2(origem, destino / pasta / nome)
    for pasta in ('cmaps', 'standard_fonts', 'wasm', 'iccs'):
        copytree(pdfjs / pasta, destino / 'pdfjs' / pasta, dirs_exist_ok=True)


def build(*, incluir_pdf=False):
    public = ROOT / 'public'
    # O Flask precisa receber a raiz para decidir se mostra o login ou abre o espaço.
    (public / 'index.html').unlink(missing_ok=True)
    (public / 'assets' / 'index.html').unlink(missing_ok=True)
    copytree(ROOT / 'web', public / 'assets', dirs_exist_ok=True,
             ignore=lambda pasta, _: {'index.html'} if Path(pasta) == ROOT / 'web' else set())
    if incluir_pdf:
        publicar_leitor_pdf(public / 'assets' / 'pdf-engine')


if __name__ == '__main__':
    build(incluir_pdf=True)
