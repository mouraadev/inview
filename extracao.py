from hashlib import sha256
from io import BytesIO
import re
import unicodedata

from inspecionar_pdf import ler_pdf

CAMPOS = (
    "fornecedor", "identificador_fiscal", "numero_fatura", "data_emissao",
    "data_vencimento", "moeda", "total", "subtotal", "desconto", "tributos",
    "pedido_compra",
)
ROTULOS = {
    "fornecedor": ["EMISSOR", "FORNECEDOR", "FROM", "SUPPLIER", "ISSUED BY"],
    "identificador_fiscal": ["CNPJ", "VAT ID", "VAT NUMBER", "TAX ID"],
    "numero_fatura": ["NUMERO DA FATURA", "INVOICE NUMBER", "INVOICE NO", "FATURA", "INVOICE"],
    "data_emissao": ["DATA DE EMISSAO", "EMISSAO", "ISSUE DATE", "INVOICE DATE"],
    "data_vencimento": ["VENCIMENTO", "DUE DATE"],
    "moeda": ["MOEDA", "CURRENCY"],
    "total": ["TOTAL DUE", "GRAND TOTAL", "VALOR TOTAL", "TOTAL"],
    "subtotal": ["SUBTOTAL", "SUB TOTAL"],
    "desconto": ["DESCONTO", "DISCOUNT"],
    "tributos": ["TRIBUTOS ADICIONAIS", "TRIBUTOS", "SALES TAX", "TAX TOTAL"],
    "pedido_compra": ["PEDIDO DE COMPRA", "PO REFERENCE", "PURCHASE ORDER", "PO NUMBER"],
}
DATA = re.compile(r"(?:[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})")
DINHEIRO = re.compile(r"[+-]?(?:[0-9]{1,3}(?:[.,][0-9]{3})+|[0-9]+)[.,][0-9]{2}")


def normalizar_rotulo(texto):
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip().rstrip(":.#")


def mesma_linha(a, b):
    return min(a["bottom"], b["bottom"]) > max(a["top"], b["top"])


def unir(palavras):
    return {
        "text": " ".join(p["text"] for p in palavras),
        "x0": min(p["x0"] for p in palavras),
        "x1": max(p["x1"] for p in palavras),
        "top": min(p["top"] for p in palavras),
        "bottom": max(p["bottom"] for p in palavras),
    }


def localizar_rotulos(palavras, aliases):
    encontrados = []
    for palavra in palavras:
        for alias in sorted(aliases, key=len, reverse=True):
            partes = alias.split()
            if normalizar_rotulo(palavra["text"]) != partes[0]:
                continue
            grupo = [palavra]
            for parte in partes[1:]:
                anterior = grupo[-1]
                direita = [p for p in palavras if mesma_linha(anterior, p)
                           and 0 <= p["x0"] - anterior["x1"] <= 25]
                proxima = min(direita, key=lambda p: p["x0"], default=None)
                if proxima is None or normalizar_rotulo(proxima["text"]) != parte:
                    break
                grupo.append(proxima)
            if len(grupo) == len(partes):
                encontrados.append(unir(grupo))
                break
    return encontrados


def vizinhos(rotulo, palavras):
    return [p for p in palavras if
            (mesma_linha(rotulo, p) and 0 <= p["x0"] - rotulo["x1"] <= 360)
            or (0 <= p["top"] - rotulo["bottom"] <= 40
                and p["x0"] < rotulo["x1"] and p["x1"] > rotulo["x0"])]


def evidencia(valor, pagina, rotulo, caixa):
    return {"valor": valor, "pagina": pagina, "rotulo": rotulo["text"],
            "trecho": caixa["text"],
            "caixa": {k: caixa[k] for k in ("x0", "x1", "top", "bottom")}}


def buscar_campo(paginas, campo):
    candidatos = []
    for pagina in paginas:
        palavras = pagina["palavras"]
        for rotulo in localizar_rotulos(palavras, ROTULOS[campo]):
            linha = [p for p in palavras if mesma_linha(rotulo, p)]
            if campo == "identificador_fiscal":
                antes = " ".join(p["text"] for p in sorted(linha, key=lambda p: p["x0"]) if p["x1"] <= rotulo["x0"])
                if re.search(r"(?:NAO E|NOT A|NOT)\s*$", normalizar_rotulo(antes)):
                    continue
            if campo == "total" and any(normalizar_rotulo(p["text"]) in
                    {"QTD", "UNIT", "HOURS", "RATE", "DESCRIPTION", "DESCRICAO"} for p in linha):
                continue  
            proximos = vizinhos(rotulo, palavras)
            if campo == "fornecedor":
                abaixo = [p for p in palavras if 0 <= p["top"] - rotulo["bottom"] <= 40
                          and abs(p["x0"] - rotulo["x0"]) <= 12]
                inicio = min(abaixo, key=lambda p: p["top"], default=None)
                if inicio:
                    limite = min((p["x0"] for p in linha if p["x0"] > rotulo["x1"] + 10), default=rotulo["x0"] + 300)
                    grupo = sorted([p for p in palavras if mesma_linha(inicio, p)
                                    and rotulo["x0"] - 12 <= p["x0"] < limite - 5], key=lambda p: p["x0"])
                    if grupo:
                        caixa = unir(grupo)
                        candidatos.append(evidencia(caixa["text"], pagina["pagina"], rotulo, caixa))
                continue
            for p in proximos:
                valor = p["text"].strip().rstrip(";:")
                if campo in {"numero_fatura", "identificador_fiscal", "pedido_compra"} and mesma_linha(rotulo, p):
                    intermediarias = [q for q in linha if q["x0"] >= rotulo["x1"]
                                      and q["x1"] <= p["x0"] and q["text"] not in {":", "#"}]
                    if intermediarias:
                        continue
                if campo in {"total", "subtotal", "desconto", "tributos"}:
                    valido = bool(DINHEIRO.fullmatch(valor))
                elif campo in {"data_emissao", "data_vencimento"}:
                    valido = bool(DATA.fullmatch(valor))
                elif campo == "moeda":
                    valido = valor.upper() in {"BRL", "USD", "EUR"}
                    valor = valor.upper()
                elif campo == "identificador_fiscal":
                    valido = bool(re.fullmatch(r"[A-Z0-9][A-Z0-9./-]{4,30}", valor.upper())) and any(c.isdigit() for c in valor)
                else:
                    valido = bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./-]{1,79}", valor)) and any(c.isdigit() for c in valor) and not DATA.fullmatch(valor)
                if valido:
                    candidatos.append(evidencia(valor, pagina["pagina"], rotulo, p))
    unicos = {}
    for c in candidatos:
        unicos[(c["valor"], c["pagina"], tuple(c["caixa"].values()))] = c
    return list(unicos.values())


def buscar_totais(paginas): return buscar_campo(paginas, "total")
def buscar_numeros_fatura(paginas): return buscar_campo(paginas, "numero_fatura")
def buscar_fornecedores(paginas): return buscar_campo(paginas, "fornecedor")
def buscar_identificadores_fiscais(paginas): return buscar_campo(paginas, "identificador_fiscal")
def buscar_subtotais(paginas): return buscar_campo(paginas, "subtotal")
def buscar_descontos(paginas): return buscar_campo(paginas, "desconto")
def buscar_tributos(paginas): return buscar_campo(paginas, "tributos")
def buscar_pedidos_compra(paginas): return buscar_campo(paginas, "pedido_compra")


def extrair_documento(conteudo: bytes):
    if len(conteudo) > 10 * 1024 * 1024:
        raise ValueError("Limite desta versão: 10 MB por PDF.")
    if not conteudo.startswith(b"%PDF-"):
        raise ValueError("O arquivo não tem um cabeçalho PDF válido.")
    try:
        paginas = ler_pdf(BytesIO(conteudo))
    except Exception as exc:
        raise ValueError("Não foi possível ler o PDF. Verifique se está íntegro e sem senha.") from exc
    if not any(p["texto"].strip() for p in paginas):
        raise ValueError("PDF sem texto extraível. OCR ainda não está disponível.")
    candidatos = {campo: buscar_campo(paginas, campo) for campo in CAMPOS}
    valores = {}
    avisos = []
    for campo, lista in candidatos.items():
        distintos = {c["valor"] for c in lista}
        valores[campo] = next(iter(distintos)) if len(distintos) == 1 else ""
        if len(distintos) > 1:
            avisos.append(f"{campo}: há mais de um candidato; escolha na conferência.")
    texto = "\n".join(p["texto"] for p in paginas)
    if not re.search(r"\b(FATURA|INVOICE)\b", normalizar_rotulo(texto)):
        avisos.append("Tipo de documento não reconhecido como fatura. Confirme o tipo antes de salvar.")
    if any(not p["texto"].strip() for p in paginas):
        avisos.append("Há páginas sem texto extraível; confira o documento original.")
    return {"sha256": sha256(conteudo).hexdigest(), "valores": valores,
            "candidatos": candidatos, "avisos": avisos,
            "paginas": [{"pagina": p["pagina"], "texto": p["texto"]} for p in paginas],
            "versao_extrator": "1.0"}
