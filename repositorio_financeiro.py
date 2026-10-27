"""Demonstração em JSON local ou MySQL explícito; não faz fallback silencioso."""
import json
import os
from pathlib import Path
from threading import RLock
from contextlib import contextmanager

from banco import conectar
from financeiro import demonstracao, vazio

LOCK = RLock()
TABELAS = {'contas': ('fin_contas', 'saldo_inicial'),
           'lancamentos': ('fin_lancamentos', 'valor'),
           'recorrencias': ('fin_recorrencias', 'valor'),
           'documentos': ('fin_documentos', None)}


class Repositorio:
    def __init__(self, modo='demo', caminho=None):
        if modo not in {'demo', 'local', 'mysql'}:
            raise ValueError('INVIEW_MODO deve ser demo, local ou mysql.')
        self.modo = modo
        self.caminho = Path(caminho or Path(__file__).parent / 'data' / f'dashboard-{modo}.json')

    def inicializar_mysql(self):
        with conectar() as conn:
            with conn.cursor() as cur:
                for sql in Path(__file__).with_name('financeiro.sql').read_text(encoding='utf-8').split(';'):
                    if sql.strip():
                        cur.execute(sql)
            conn.commit()
        with self.transacao() as estado:
            if not estado['contas']:
                estado.update(vazio())

    @contextmanager
    def transacao(self, gravar=True):
        if self.modo in {'demo', 'local'}:
            with LOCK:
                estado = json.loads(self.caminho.read_text(encoding='utf-8')) if self.caminho.exists() else (demonstracao() if self.modo == 'demo' else vazio())
                yield estado
                if gravar:
                    self.caminho.parent.mkdir(parents=True, exist_ok=True)
                    temporario = self.caminho.with_suffix('.tmp')
                    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding='utf-8')
                    temporario.replace(self.caminho)
        else:
            with conectar() as conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute('SELECT id FROM fin_workspace WHERE id=1 FOR UPDATE')
                        estado = {}
                        for colecao, (tabela, campo) in TABELAS.items():
                            cur.execute(f'SELECT * FROM {tabela}')
                            estado[colecao] = []
                            for linha in cur.fetchall():
                                item = json.loads(linha['dados'])
                                if campo:
                                    item[campo] = str(linha['valor'])
                                estado[colecao].append(item)
                        yield estado
                        if gravar:
                            for colecao, (tabela, campo) in TABELAS.items():
                                for item in estado[colecao]:
                                    dados = dict(item)
                                    valor = dados.pop(campo) if campo else '0.00'
                                    cur.execute(f'INSERT INTO {tabela} (id,valor,dados) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE valor=%s,dados=%s',
                                                (item['id'], valor, json.dumps(dados, ensure_ascii=False), valor, json.dumps(dados, ensure_ascii=False)))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
