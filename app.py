import json
from hashlib import sha256

import pymysql
import streamlit as st

from banco import (inicializar, listar_faturas, obter_documento, salvar_fatura,
                   consultar_duplicidades)
from extracao import CAMPOS, extrair_documento
from validacao import OBRIGATORIOS, validar_fatura

st.set_page_config(page_title="Inview — conferência de faturas", layout="wide")
st.title("Inview")
st.caption("Importe uma fatura, confira os dados e confirme a gravação no MySQL.")
rotulos = {
    "fornecedor": "Fornecedor", "identificador_fiscal": "Identificador fiscal",
    "numero_fatura": "Número da fatura", "data_emissao": "Emissão",
    "data_vencimento": "Vencimento", "moeda": "Moeda", "total": "Total",
    "subtotal": "Subtotal", "desconto": "Desconto", "tributos": "Tributos adicionais",
    "pedido_compra": "Pedido de compra",
}


def erro_banco(exc):
    if isinstance(exc, ValueError):
        st.error(str(exc))
    else:
        st.error("Não foi possível concluir a operação no MySQL. Confira o serviço, as variáveis MYSQL_* e as permissões do usuário.")


pagina_app = st.sidebar.radio("Navegação", ["Importar e conferir", "Faturas confirmadas"])
if st.sidebar.button("Preparar tabelas MySQL"):
    try:
        inicializar()
        st.sidebar.success("Tabelas prontas.")
    except (ValueError, pymysql.MySQLError) as exc:
        erro_banco(exc)

if pagina_app == "Faturas confirmadas":
    try:
        faturas = listar_faturas()
        st.dataframe(faturas, hide_index=True)
        if faturas:
            escolhido = st.selectbox("Abrir documento e histórico", [f["id"] for f in faturas])
            doc = obter_documento(escolhido)
            if doc:
                st.download_button("Baixar PDF original", doc["conteudo"], doc["nome_original"], "application/pdf")
                with st.expander("Extração original"):
                    st.json(json.loads(doc["extracao"]))
                with st.expander("Conferência e correções"):
                    st.json(json.loads(doc["revisao"]))
        else:
            st.info("Nenhuma fatura confirmada.")
    except (ValueError, pymysql.MySQLError) as exc:
        erro_banco(exc)
    st.stop()

arquivo = st.file_uploader("Fatura em PDF (até 10 MB)", type=["pdf"])
if arquivo is None:
    st.info("Escolha um PDF com texto selecionável. Campos não reconhecidos podem ser preenchidos na conferência.")
    st.stop()

conteudo = arquivo.getvalue()
digest = sha256(conteudo).hexdigest()
if st.session_state.get("documento_atual") != digest:
    for chave in list(st.session_state):
        if chave.startswith("revisao_"):
            del st.session_state[chave]
    st.session_state["documento_atual"] = digest
    try:
        st.session_state["extracao"] = extrair_documento(conteudo)
        st.session_state.pop("falha_extracao", None)
    except ValueError as exc:
        st.session_state["falha_extracao"] = str(exc)
        st.session_state.pop("extracao", None)

if "falha_extracao" in st.session_state:
    st.error(st.session_state["falha_extracao"])
    st.stop()

extracao = st.session_state["extracao"]
if st.session_state.get("revisao_salva"):
    st.success(f"Fatura {st.session_state['revisao_salva']} confirmada. Consulte-a em Faturas confirmadas.")
    st.stop()

for aviso in extracao["avisos"]:
    st.warning(aviso)
origem, conferencia = st.columns(2)
with origem:
    st.subheader("Documento de origem")
    st.download_button("Abrir/baixar PDF para conferir", conteudo, arquivo.name, "application/pdf")
    for p in extracao["paginas"]:
        with st.expander(f"Texto da página {p['pagina']}", expanded=True):
            st.text(p["texto"])
    with st.expander("Todos os candidatos e suas evidências"):
        st.json(extracao["candidatos"])

with conferencia:
    st.subheader("Conferência")
    st.caption("* Obrigatório. Valores sem símbolo de moeda. Datas ISO (AAAA-MM-DD) ou com barras conforme a ordem escolhida. Formatos não são inferidos da moeda.")
    with st.form("conferencia", enter_to_submit=False):
        formato = st.selectbox("Formato dos valores", ["Selecione", "pt-BR", "en-US"], key="revisao_formato",
                              help="pt-BR: 3.325,00. en-US: 2,181.60. Confirme o formato dos valores digitados.")
        ordem = st.selectbox("Ordem das datas com barras", ["Selecione", "DMY", "MDY"], key="revisao_ordem")
        entrada = {}
        for campo in CAMPOS:
            entrada[campo] = st.text_input(rotulos[campo] + (" *" if campo in OBRIGATORIOS else ""),
                                           value=extracao["valores"][campo], key=f"revisao_{campo}")
        tipo_confirmado = st.checkbox("Conferi o documento e confirmo que é uma fatura.", key="revisao_tipo")
        aceitar_avisos = st.checkbox("Revisei os avisos de consistência apresentados e desejo manter os valores.", key="revisao_avisos")
        aceitar_duplicidade = st.checkbox("Se houver suspeita de duplicidade, conferi os registros e quero manter ambas as faturas.", key="revisao_duplicidade")
        verificar = st.form_submit_button("Validar e verificar duplicidade")
        confirmar = st.form_submit_button("Confirmar e salvar no MySQL")

    if verificar or confirmar:
        if formato == "Selecione" or ordem == "Selecione":
            st.error("Escolha o formato monetário e a ordem das datas antes de continuar.")
        else:
            dados, erros, avisos = validar_fatura(entrada, formato, ordem)
            for erro in erros:
                st.error(erro)
            for aviso in avisos:
                st.warning(aviso)
            if not erros:
                st.write("Dados normalizados para confirmação")
                st.json({k: str(v) if v is not None else None for k, v in dados.items()})
                try:
                    duplicatas = consultar_duplicidades(dados)
                    if duplicatas:
                        st.warning("Possível duplicidade: mesmo fornecedor e número.")
                        st.dataframe(duplicatas, hide_index=True)
                    if confirmar:
                        identificador = salvar_fatura(arquivo.name, conteudo, extracao, entrada, formato, ordem,
                                                      aceitar_avisos, aceitar_duplicidade, tipo_confirmado)
                        st.session_state["revisao_salva"] = identificador
                        st.rerun()
                    elif not duplicatas:
                        st.success("Validação concluída; nenhuma duplicidade de negócio encontrada.")
                except (ValueError, pymysql.MySQLError) as exc:
                    erro_banco(exc)
