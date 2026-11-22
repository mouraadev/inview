"""Reconhecimento de faturas digitalizadas com Apple Vision no macOS."""
from contextlib import closing
from functools import lru_cache
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock

import pypdfium2 as pdfium

from extracao import estruturar_extracao, normalizar_rotulo, validar_arquivo_pdf


LIMITE_PAGINAS = 5
ANALISE_EM_ANDAMENTO = Lock()
LEITOR = Path(__file__).with_name('ocr_vision.swift')
MACOS = sys.platform == 'darwin'
DATA_OCR = r'([0-9]{2}[ \t]*/[ \t]*[0-9]{2}[ \t]*/[ \t]*[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})'
ROTULOS_EXPLICITOS = {
    'fornecedor': re.compile(r'(?im)^(?:fornecedor|emissor|supplier|from)[ \t]*:[ \t]*(\S[^\r\n]*)$'),
    'data_emissao': re.compile(r'(?im)^(?:data de emiss[ãa]o|emiss[ãa]o|issue date|invoice date)[ \t:]*' + DATA_OCR),
    'data_vencimento': re.compile(r'(?im)^(?:data de vencimento|vencimento|due date)[ \t:]*' + DATA_OCR),
}
DATA_ROTULADA = re.compile(r'(?m)^([^:\r\n]{3,40}):[ \t]*' + DATA_OCR)
ROTULOS_DATAS = {'EMISSAO': 'data_emissao', 'DATA DE EMISSAO': 'data_emissao', 'ISSUE DATE': 'data_emissao',
                 'INVOICE DATE': 'data_emissao', 'VENCIMENTO': 'data_vencimento',
                 'DATA DE VENCIMENTO': 'data_vencimento', 'DUE DATE': 'data_vencimento'}


class ErroAnaliseIA(Exception):
    def __init__(self, mensagem, status=503):
        super().__init__(mensagem)
        self.status = status


@lru_cache(maxsize=1)
def cache_vision():
    # O Swift reaproveita os módulos compilados durante a execução do Inview.
    return TemporaryDirectory(prefix='inview-ocr-')


def ler_pagina(imagem, cache):
    ambiente = {**os.environ, 'CLANG_MODULE_CACHE_PATH': cache, 'SWIFT_MODULECACHE_PATH': cache}
    try:
        resultado = subprocess.run(['/usr/bin/swift', str(LEITOR)], input=imagem,
                                   capture_output=True, env=ambiente, timeout=60, check=True)
    except subprocess.TimeoutExpired:
        raise ErroAnaliseIA('A leitura local demorou para responder. Tente novamente.', 504) from None
    except (OSError, subprocess.CalledProcessError):
        raise ErroAnaliseIA('A leitura local requer o Apple Vision e as ferramentas de linha de comando do macOS.') from None
    try:
        return json.loads(resultado.stdout)
    except ValueError:
        raise ErroAnaliseIA('O leitor devolveu uma resposta inválida. Tente novamente.', 502) from None


def imagem_da_pagina(pagina, escala):
    with closing(pagina.render(scale=escala, fill_color=(255, 255, 255, 255))) as bitmap:
        destino = BytesIO()
        bitmap.to_pil().convert('RGB').save(destino, format='JPEG', quality=94)
        return destino.getvalue()


def candidatos_por_rotulo(paginas):
    encontrados = {campo: [] for campo in ROTULOS_EXPLICITOS}
    for pagina in paginas:
        for campo, padrao in ROTULOS_EXPLICITOS.items():
            for match in padrao.finditer(pagina['texto']):
                valor = match[1].strip() if campo == 'fornecedor' else re.sub(r'[ \t]', '', match[1])
                encontrados[campo].append({'valor': valor, 'pagina': pagina['pagina']})
        for rotulo, data in DATA_ROTULADA.findall(pagina['texto']):
            lido = normalizar_rotulo(rotulo)
            if lido in ROTULOS_DATAS:
                continue
            # Tolera um caractere trocado no rótulo. A data precisa estar legível e completa.
            campos = {campo for alias, campo in ROTULOS_DATAS.items()
                      if len(lido) == len(alias) and sum(a != b for a, b in zip(lido, alias)) == 1}
            if len(campos) == 1:
                encontrados[campos.pop()].append({'valor': re.sub(r'[ \t]', '', data), 'pagina': pagina['pagina']})
    return encontrados


def extrair_com_ia(conteudo):
    validar_arquivo_pdf(conteudo)
    if not MACOS:
        raise ErroAnaliseIA('A leitura por IA local está disponível no macOS.')
    if not ANALISE_EM_ANDAMENTO.acquire(blocking=False):
        raise ErroAnaliseIA('Já há um PDF em análise. Aguarde e tente novamente.', 429)

    paginas = []
    try:
        with pdfium.PdfDocument(conteudo) as documento:
            if not 1 <= len(documento) <= LIMITE_PAGINAS:
                raise ValueError(f'A IA local lê PDFs de até {LIMITE_PAGINAS} páginas. Para PDFs maiores com texto, use Texto do PDF.')
            for indice in range(len(documento)):
                with closing(documento[indice]) as pagina:
                    largura, altura = pagina.get_size()
                    imagem = imagem_da_pagina(pagina, min(3, 2000 / max(largura, altura)))
                leitura = ler_pagina(imagem, cache_vision().name)
                for palavra in leitura['palavras']:
                    for eixo in ('x0', 'x1'):
                        palavra[eixo] *= largura
                    for eixo in ('top', 'bottom'):
                        palavra[eixo] *= altura
                paginas.append(dict(leitura, pagina=indice + 1))
    except pdfium.PdfiumError as exc:
        raise ValueError('Não foi possível abrir ou renderizar o PDF. Confira se está íntegro e sem senha.') from exc
    finally:
        ANALISE_EM_ANDAMENTO.release()

    if not any(pagina['texto'].strip() for pagina in paginas):
        raise ValueError('A IA local não encontrou texto legível. Tente uma digitalização mais nítida.')
    resultado = estruturar_extracao(conteudo, paginas)
    for campo, candidatos in candidatos_por_rotulo(paginas).items():
        if candidatos:
            resultado['candidatos'][campo] = candidatos
            distintos = {candidato['valor'] for candidato in candidatos}
            resultado['avisos'] = [aviso for aviso in resultado['avisos'] if not aviso.startswith(campo + ':')]
            resultado['valores'][campo] = next(iter(distintos)) if len(distintos) == 1 else ''
            if len(distintos) > 1:
                resultado['avisos'].append(f'{campo}: há mais de um candidato; escolha na conferência.')
    resultado.update(versao_extrator='ia-local-1.0', modelo='Apple Vision')
    resultado['avisos'].insert(0, 'Sugestões a partir da digitalização. Compare cada campo com o PDF original.')
    return resultado
