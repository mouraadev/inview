"""Normalização explícita. Ausente é None; dinheiro nunca passa por float."""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import re

from extracao import CAMPOS

MONETARIOS = {"total", "subtotal", "desconto", "tributos"}
OBRIGATORIOS = {"fornecedor", "numero_fatura", "data_emissao", "moeda", "total"}


def normalizar_valor(texto, formato="pt-BR"):
    if not str(texto).strip():
        return None
    if formato not in {"pt-BR", "en-US"}:
        raise ValueError("Formato monetário desconhecido.")
    texto = str(texto).strip()
    padrao = (r"[+-]?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)(?:,[0-9]{1,2})?"
              if formato == "pt-BR" else
              r"[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]{1,2})?")
    if not re.fullmatch(padrao, texto):
        raise ValueError(f"Valor inválido para {formato}; use no máximo duas casas decimais, sem símbolo.")
    canonico = texto.replace(".", "").replace(",", ".") if formato == "pt-BR" else texto.replace(",", "")
    valor = Decimal(canonico)
    if abs(valor) >= Decimal("10000000000000000"):
        raise ValueError("Valor excede DECIMAL(18,2).")
    # Apenas acrescenta zeros; mais de duas casas já foram rejeitadas (sem arredondamento silencioso).
    return valor.quantize(Decimal("0.01"))


def normalizar_data(texto, ordem="DMY"):
    if not str(texto).strip():
        return None
    texto = str(texto).strip()
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", texto):
        return date.fromisoformat(texto)
    if ordem not in {"DMY", "MDY"}:
        raise ValueError("Escolha DMY ou MDY.")
    if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", texto):
        raise ValueError("Use AAAA-MM-DD ou uma data com barras.")
    return datetime.strptime(texto, "%d/%m/%Y" if ordem == "DMY" else "%m/%d/%Y").date()


def validar_fatura(entrada, formato="pt-BR", ordem="DMY"):
    dados, erros, avisos = {}, [], []
    for campo in CAMPOS:
        texto = str(entrada.get(campo) or "").strip()
        try:
            if campo in MONETARIOS:
                dados[campo] = normalizar_valor(texto, formato)
            elif campo in {"data_emissao", "data_vencimento"}:
                dados[campo] = normalizar_data(texto, ordem)
            else:
                dados[campo] = texto or None
        except (ValueError, InvalidOperation) as exc:
            dados[campo] = None
            erros.append(f"{campo}: {exc}")
        if campo in OBRIGATORIOS and not texto:
            erros.append(f"{campo}: obrigatório para confirmação.")
        if campo not in MONETARIOS and campo not in {"data_emissao", "data_vencimento"} and len(texto) > 255:
            erros.append(f"{campo}: limite de 255 caracteres.")
    if dados["moeda"]:
        dados["moeda"] = dados["moeda"].upper()
        if dados["moeda"] not in {"BRL", "USD", "EUR"}:
            erros.append("Moeda não suportada nesta versão: use BRL, USD ou EUR.")
    for campo in MONETARIOS:
        if dados[campo] is not None and dados[campo] < 0:
            erros.append(f"{campo}: valor negativo não suportado neste recorte de faturas.")
    if dados["data_emissao"] and dados["data_vencimento"] and dados["data_vencimento"] < dados["data_emissao"]:
        avisos.append("Vencimento anterior à emissão: confira as datas.")
    if all(dados[c] is not None for c in MONETARIOS):
        esperado = dados["subtotal"] - dados["desconto"] + dados["tributos"]
        if esperado != dados["total"]:
            avisos.append("Subtotal − desconto + tributos difere do total. Confira se os tributos são adicionais ou já estão incluídos.")
    return dados, erros, avisos
