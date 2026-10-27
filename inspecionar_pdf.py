from pathlib import Path
import re
import pdfplumber


def ler_pdf(caminho: Path) -> list[dict]:
    paginas = []

    with pdfplumber.open(caminho) as pdf:
        for numero, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            palavras = pagina.extract_words()

            if not texto.strip():
                print(f"Aviso: página {numero} sem texto extraído.")

            paginas.append({"pagina": numero, "texto": texto, "palavras": palavras})

    return paginas

def buscar_moedas(paginas: list[dict]) -> list[dict]:
    moedas = []

    for pagina in paginas:
        for linha in pagina["texto"].splitlines():
            linha_normalizada = linha.strip().upper()

            if linha_normalizada.startswith(("MOEDA:", "CURRENCY:")):
                moeda = linha_normalizada.split(":", 1)[1].strip()

                if moeda in {"BRL", "USD", "EUR"}:
                    moedas.append({
                        "moeda": moeda,
                        "pagina": pagina["pagina"],
                        "trecho": linha,
                    })
    return moedas

def buscar_datas(paginas: list[dict]) -> list[dict]:
    datas = []
    padrao = r"(?:[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})"

    for pagina in paginas:
        for palavra in pagina["palavras"]:
            texto = palavra["text"]

            if re.fullmatch(padrao, texto):
                datas.append({
                    "data": texto,
                    "pagina": pagina["pagina"],
                    "x0": palavra["x0"],
                    "x1": palavra["x1"],
                    "top": palavra["top"],
                    "bottom": palavra["bottom"],
                })
    
    return datas

def associar_datas(paginas: list[dict], datas: list[dict]) -> list[dict]:
    associacoes = []

    tipos = {
        "EMISSÃO": "emissão",
        "VENCIMENTO": "vencimento",
        "ISSUE DATE": "emissão",
        "DUE DATE": "vencimento",
    }

    for pagina in paginas:
        for palavra in pagina["palavras"]:
            rotulo = palavra["text"].strip().upper().rstrip(":")
            caixa_rotulo = palavra
            trecho_rotulo = palavra["text"]

            if rotulo in {"ISSUE", "DUE"}:
                seguinte = None
                for candidata in pagina["palavras"]:
                    mesma_linha = abs(candidata["top"] - palavra["top"]) <= 3
                    distancia_horizontal = candidata["x0"] - palavra["x1"]

                    if mesma_linha and 0 <= distancia_horizontal <= 20:
                        if seguinte is None or candidata["x0"] < seguinte["x0"]:
                            seguinte = candidata

                if seguinte is None:
                    continue
                if seguinte["text"].strip().upper().rstrip(":") != "DATE":
                    continue

                rotulo = f"{rotulo} DATE"
                trecho_rotulo = f"{palavra['text']} {seguinte['text']}"
                # Usa a área das duas palavras sem alterar os dados originais.
                caixa_rotulo = {
                    "x0": min(palavra["x0"], seguinte["x0"]),
                    "x1": max(palavra["x1"], seguinte["x1"]),
                    "bottom": max(palavra["bottom"], seguinte["bottom"]),
                }

            if rotulo not in tipos:
                continue

            for data in datas:
                if data["pagina"] != pagina["pagina"]: 
                    continue

                distancia_vertical = data["top"] - caixa_rotulo["bottom"]

                alinhada = (
                    data["x0"] < caixa_rotulo["x1"]
                    and data["x1"] > caixa_rotulo["x0"]
                )

                if alinhada and 0 <= distancia_vertical <= 40:
                    associacoes.append({
                        "tipo": tipos[rotulo],
                        "data": data["data"],
                        "pagina": data["pagina"],
                        "rotulo": trecho_rotulo,
                        "distancia_vertical": distancia_vertical,
                    })
    return associacoes

if __name__ == "__main__":
    arquivos = [
        Path(r"C:\Users\Ryan Moura\Downloads\inview_invoice_01_brl.pdf"),
        Path(r"C:\Users\Ryan Moura\Downloads\inview_invoice_02_usd.pdf"),
    ]

    for arquivo in arquivos:
        resultado = ler_pdf(arquivo)
        moedas = buscar_moedas(resultado)
        datas = buscar_datas(resultado)
        associacoes = associar_datas(resultado, datas)
        
        print(f"\nArquivo: {arquivo.name}")
        print(f"Páginas: {len(resultado)}")
        print("Moedas encontradas:", moedas)
        print("Datas encontradas:", datas)
        print("Datas associadas:", associacoes)


        for pagina in resultado:
            print(f"--- Página {pagina['pagina']} ---")
            print(pagina["texto"][:200])

