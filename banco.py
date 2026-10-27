import json
import os
from hashlib import sha256
from pathlib import Path
import unicodedata

import pymysql

from extracao import CAMPOS
from validacao import validar_fatura


class ArquivoRepetido(ValueError):
    pass


class DuplicidadeNegocio(ValueError):
    pass


def conectar():
    if not os.environ.get("MYSQL_USER") or not os.environ.get("MYSQL_DATABASE"):
        raise ValueError("Configure MYSQL_USER, MYSQL_PASSWORD e MYSQL_DATABASE antes de usar o banco.")
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"], password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ["MYSQL_DATABASE"], charset="utf8mb4", autocommit=False,
        cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
        read_timeout=15, write_timeout=15,
    )


def inicializar():
    with conectar() as conn:
        with conn.cursor() as cur:
            for comando in Path(__file__).with_name("schema.sql").read_text(encoding="utf-8").split(";"):
                if comando.strip():
                    cur.execute(comando)
        conn.commit()


def chave_negocio(dados):
    def normalizar(valor):
        return " ".join(unicodedata.normalize("NFKC", valor).casefold().split())
    texto = json.dumps([normalizar(dados["fornecedor"]), normalizar(dados["numero_fatura"])])
    return sha256(texto.encode()).hexdigest()


def consultar_duplicidades(dados):
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, fornecedor, numero_fatura, moeda, total FROM faturas WHERE chave_negocio=%s", (chave_negocio(dados),))
            return cur.fetchall()


def salvar_fatura(nome, conteudo, extracao, entrada, formato, ordem,
                  aceitar_avisos=False, aceitar_duplicidade=False, confirmar_tipo=False):
    dados, erros, avisos = validar_fatura(entrada, formato, ordem)
    if erros:
        raise ValueError("\n".join(erros))
    if not confirmar_tipo:
        raise ValueError("Confirme que o documento é uma fatura.")
    if avisos and not aceitar_avisos:
        raise ValueError("Revise os avisos e confirme ciência antes de salvar.")
    digest = sha256(conteudo).hexdigest()
    if digest != extracao["sha256"]:
        raise ValueError("O documento mudou desde a extração. Processe-o novamente.")
    if len(conteudo) > 10 * 1024 * 1024:
        raise ValueError("Arquivo excede 10 MB.")
    chave = chave_negocio(dados)
    revisao = {
        "entrada_revisada": entrada, "normalizados_aprovados": dados,
        "correcoes": {c: {"antes": extracao["valores"].get(c), "depois": entrada.get(c)}
                      for c in CAMPOS if (extracao["valores"].get(c) or "") != (entrada.get(c) or "")},
        "formato_monetario": formato, "ordem_datas": ordem, "avisos": avisos,
        "avisos_aceitos": aceitar_avisos, "duplicidade_aceita": aceitar_duplicidade,
        "tipo_confirmado": confirmar_tipo,
    }
    with conectar() as conn:
        bloqueio = False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT GET_LOCK(%s, 5) AS obtido", (chave,))
                bloqueio = cur.fetchone()["obtido"] == 1
                if not bloqueio:
                    raise ValueError("Outra confirmação está em andamento. Tente novamente.")
                cur.execute("SELECT id FROM documentos WHERE sha256=%s", (digest,))
                if cur.fetchone():
                    raise ArquivoRepetido("Este mesmo arquivo já foi confirmado.")
                cur.execute("SELECT id FROM faturas WHERE chave_negocio=%s", (chave,))
                duplicadas = cur.fetchall()
                if duplicadas and not aceitar_duplicidade:
                    raise DuplicidadeNegocio("Já existe fatura com o mesmo fornecedor e número. Consulte e confirme se deseja manter ambas.")
                revisao["duplicatas_encontradas"] = [r["id"] for r in duplicadas]
                cur.execute("INSERT INTO documentos (sha256,nome_original,conteudo,extracao) VALUES (%s,%s,%s,%s)",
                            (digest, Path(nome).name[:255], conteudo, json.dumps(extracao, ensure_ascii=False)))
                documento_id = cur.lastrowid
                colunas = ",".join(CAMPOS) 
                marcadores = ",".join(["%s"] * (len(CAMPOS) + 3))
                cur.execute(f"INSERT INTO faturas (documento_id,{colunas},chave_negocio,revisao) VALUES ({marcadores})",
                            (documento_id, *(dados[c] for c in CAMPOS), chave,
                             json.dumps(revisao, ensure_ascii=False, default=str)))
                identificador = cur.lastrowid
            conn.commit()
            return identificador
        except pymysql.IntegrityError as exc:
            conn.rollback()
            if exc.args[0] == 1062:
                raise ArquivoRepetido("Este arquivo já foi confirmado por outra operação.") from exc
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            if bloqueio:
                with conn.cursor() as cur:
                    cur.execute("SELECT RELEASE_LOCK(%s)", (chave,))


def listar_faturas():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, fornecedor, numero_fatura, data_emissao, data_vencimento, moeda, total FROM faturas ORDER BY id DESC LIMIT 200")
            return cur.fetchall()


def obter_documento(fatura_id):
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT d.nome_original,d.conteudo,d.extracao,f.revisao FROM documentos d JOIN faturas f ON f.documento_id=d.id WHERE f.id=%s", (fatura_id,))
            return cur.fetchone()


if __name__ == "__main__":
    inicializar()
    print("Tabelas prontas no banco configurado.")
