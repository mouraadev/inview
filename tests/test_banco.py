import json
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

import banco
from tests.test_fluxo import entrada_valida


def preparar(monkeypatch, respostas, falhar_insert=False):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.side_effect = respostas
    cur.fetchall.return_value = []
    cur.lastrowid = 12
    if falhar_insert:
        def executar(sql, params=None):
            if sql.startswith('INSERT INTO faturas'):
                raise RuntimeError('Falha simulada após inserir documento')
        cur.execute.side_effect = executar
    monkeypatch.setattr(banco, 'conectar', lambda: conn)
    conteudo = b'%PDF-teste'
    extracao = {'sha256': sha256(conteudo).hexdigest(), 'valores': {'total': '89,00'}, 'candidatos': {}}
    return conn, cur, conteudo, extracao


def test_commit_e_correcao(monkeypatch):
    conn, cur, pdf, extracao = preparar(monkeypatch, [{'obtido': 1}, None])
    assert banco.salvar_fatura('teste.pdf', pdf, extracao, entrada_valida(), 'pt-BR', 'DMY', confirmar_tipo=True) == 12
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    params = next(c.args[1] for c in cur.execute.call_args_list if c.args[0].startswith('INSERT INTO faturas'))
    revisao = json.loads(params[-1])
    assert revisao['correcoes']['total'] == {'antes': '89,00', 'depois': '90,00'}
    assert extracao['valores']['total'] == '89,00'


def test_rollback_sem_confirmacao_parcial(monkeypatch):
    conn, cur, pdf, extracao = preparar(monkeypatch, [{'obtido': 1}, None], True)
    with pytest.raises(RuntimeError):
        banco.salvar_fatura('teste.pdf', pdf, extracao, entrada_valida(), 'pt-BR', 'DMY', confirmar_tipo=True)
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_mesmo_arquivo(monkeypatch):
    conn, cur, pdf, extracao = preparar(monkeypatch, [{'obtido': 1}, {'id': 1}])
    with pytest.raises(banco.ArquivoRepetido):
        banco.salvar_fatura('teste.pdf', pdf, extracao, entrada_valida(), 'pt-BR', 'DMY', confirmar_tipo=True)
    assert not any(c.args[0].startswith('INSERT') for c in cur.execute.call_args_list)


def test_duplicidade_negocio(monkeypatch):
    conn, cur, pdf, extracao = preparar(monkeypatch, [{'obtido': 1}, None])
    cur.fetchall.return_value = [{'id': 3}]
    with pytest.raises(banco.DuplicidadeNegocio):
        banco.salvar_fatura('teste.pdf', pdf, extracao, entrada_valida(), 'pt-BR', 'DMY', confirmar_tipo=True)
    conn.commit.assert_not_called()


def test_chave_negocio():
    a = entrada_valida()
    b = dict(a, fornecedor=' FORNECEDOR  DE TESTE ', numero_fatura='f-1')
    assert banco.chave_negocio(a) == banco.chave_negocio(b)
