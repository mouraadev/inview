"""Opt-in: rode exclusivamente em banco de teste, conforme README."""
import json
import os
from hashlib import sha256
from uuid import uuid4

import pytest

import banco
from tests.test_fluxo import entrada_valida

pytestmark = pytest.mark.skipif(os.environ.get('INVIEW_TEST_MYSQL') != '1',
                                reason='Integração requer MySQL de teste e INVIEW_TEST_MYSQL=1.')


def test_mysql_confirmacao_reimportacao_e_historico():
    banco.inicializar()
    entrada = dict(entrada_valida(), numero_fatura='TEST-' + uuid4().hex)
    chave = banco.chave_negocio(entrada)
    pdf = b'%PDF-teste-' + uuid4().hex.encode()
    digest = sha256(pdf).hexdigest()
    extracao = {'sha256': digest, 'valores': {'total': '89,00'}, 'candidatos': {}}
    try:
        identificador = banco.salvar_fatura('sintetico.pdf', pdf, extracao, entrada, 'pt-BR', 'DMY', confirmar_tipo=True)
        doc = banco.obter_documento(identificador)
        assert doc['conteudo'] == pdf
        revisao = json.loads(doc['revisao'])
        assert revisao['correcoes']['total']['antes'] == '89,00'
        with pytest.raises(banco.ArquivoRepetido):
            banco.salvar_fatura('sintetico.pdf', pdf, extracao, entrada, 'pt-BR', 'DMY', confirmar_tipo=True)
        outro_pdf = pdf + b'-outra-versao'
        outra = dict(extracao, sha256=sha256(outro_pdf).hexdigest())
        with pytest.raises(banco.DuplicidadeNegocio):
            banco.salvar_fatura('outra.pdf', outro_pdf, outra, entrada, 'pt-BR', 'DMY', confirmar_tipo=True)
        with banco.conectar() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) AS n FROM documentos WHERE sha256=%s', (outra['sha256'],))
                assert cur.fetchone()['n'] == 0
    finally:
        # Remove somente o registro identificado pelo UUID deste teste.
        with banco.conectar() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM faturas WHERE chave_negocio=%s', (chave,))
                cur.execute('DELETE FROM documentos WHERE sha256=%s', (digest,))
            conn.commit()
