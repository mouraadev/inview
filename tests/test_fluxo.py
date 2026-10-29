from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from extracao import extrair_documento, buscar_campo
from validacao import normalizar_valor, normalizar_data, validar_fatura


@pytest.mark.parametrize('texto,formato,esperado', [
    ('3.325,00', 'pt-BR', '3325.00'), ('2,181.60', 'en-US', '2181.60'),
    ('0,00', 'pt-BR', '0.00'), ('10', 'en-US', '10.00'), ('', 'pt-BR', None),
])
def test_decimal_exato(texto, formato, esperado):
    valor = normalizar_valor(texto, formato)
    assert valor == (Decimal(esperado) if esperado is not None else None)
    if valor is not None:
        assert isinstance(valor, Decimal)


@pytest.mark.parametrize('texto', ['12,34', 'NaN', 'Infinity', '3.325,00', '1.005', '10000000000000000'])
def test_valor_invalido_ou_arredondamento_silencioso(texto):
    with pytest.raises(ValueError):
        normalizar_valor(texto, 'en-US')


def test_datas_explicitas():
    assert normalizar_data('03/04/2026', 'DMY').isoformat() == '2026-04-03'
    assert normalizar_data('03/04/2026', 'MDY').isoformat() == '2026-03-04'
    assert normalizar_data('2026-10-15', 'DMY').isoformat() == '2026-10-15'
    with pytest.raises(ValueError):
        normalizar_data('31/02/2026')


def entrada_valida():
    return dict(fornecedor='Fornecedor de teste', numero_fatura='F-1', data_emissao='2026-10-01',
                moeda='BRL', total='90,00', subtotal='100,00', desconto='10,00', tributos='0,00')


def test_validacao_preserva_original_e_zero():
    entrada = entrada_valida()
    antes = deepcopy(entrada)
    dados, erros, avisos = validar_fatura(entrada)
    assert not erros and not avisos
    assert entrada == antes
    assert dados['tributos'] == Decimal('0.00')
    assert dados['identificador_fiscal'] is None
    assert dados['data_vencimento'] is None


def test_ausencias_e_inconsistencia():
    assert len(validar_fatura({})[1]) == 5
    entrada = entrada_valida()
    entrada['total'] = '91,00'
    assert validar_fatura(entrada)[2]
    entrada['desconto'] = ''
    assert not validar_fatura(entrada)[2]  # Não inventa desconto zero.


def palavra(texto, x0, top, x1):
    return {'text': texto, 'x0': x0, 'x1': x1, 'top': top, 'bottom': top + 10}


def test_rotulo_composto_e_pagina():
    paginas = [{'pagina': 1, 'palavras': [palavra('DUE', 10, 10, 30), palavra('DATE', 33, 10, 60),
                                         palavra('2026-11-14', 10, 30, 80)]},
               {'pagina': 2, 'palavras': [palavra('2026-12-14', 10, 30, 80)]}]
    r = buscar_campo(paginas, 'data_vencimento')
    assert [(c['valor'], c['pagina']) for c in r] == [('2026-11-14', 1)]
    paginas[0]['palavras'][1]['top'] = 100
    paginas[0]['palavras'][1]['bottom'] = 110
    assert buscar_campo(paginas, 'data_vencimento') == []


def test_pdf_invalido():
    with pytest.raises(ValueError, match='cabeçalho'):
        extrair_documento(b'nao e pdf')
    with pytest.raises(ValueError, match='possível ler'):
        extrair_documento(b'%PDF-danificado')


@pytest.mark.parametrize('nome,formato,esperado', [
    ('inview_invoice_01_brl.pdf', 'pt-BR', dict(fornecedor='Aurora Dados Serviços Ltda.', numero_fatura='FAT-2026-001',
         data_emissao='01/10/2026', data_vencimento='31/10/2026', moeda='BRL', total='3.325,00',
         subtotal='3.500,00', desconto='175,00', tributos='0,00', pedido_compra='PC-2026-042', identificador_fiscal='')),
    ('inview_invoice_02_usd.pdf', 'en-US', dict(fornecedor='Northstar Studio LLC', numero_fatura='INV-2026-108',
         data_emissao='2026-10-15', data_vencimento='2026-11-14', moeda='USD', total='2,181.60',
         subtotal='2,020.00', desconto='0.00', tributos='161.60', pedido_compra='PO-2026-089', identificador_fiscal='')),
])
def test_amostras(nome, formato, esperado):
    import os
    pasta = Path(os.environ.get('INVIEW_PDFS_TESTE', str(Path.home() / 'Downloads')))
    arquivo = pasta / nome
    if not arquivo.exists():
        pytest.skip('Amostra sintética não disponível; configure INVIEW_PDFS_TESTE.')
    resultado = extrair_documento(arquivo.read_bytes())
    assert resultado['valores'] == esperado
    assert not resultado['avisos']
    assert not validar_fatura(resultado['valores'], formato)[1:][0]
    assert all(c['pagina'] == 1 and c['caixa'] for lista in resultado['candidatos'].values() for c in lista)
