"""Validação do estado financeiro enviado pelo navegador, sem persistência."""
from datetime import date
import re
from financeiro import dinheiro, validar_lancamento


def identificador(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_:\-]{1,160}', value):
        raise ValueError('Identificador inválido.')
    return value


def validar_estado(raw):
    if not isinstance(raw, dict):
        raise ValueError('Estado do navegador inválido.')
    state = {'contas': [], 'lancamentos': [], 'recorrencias': [], 'documentos': []}
    for name, limit in [('contas', 100), ('recorrencias', 200), ('lancamentos', 2000)]:
        rows = raw.get(name)
        if not isinstance(rows, list) or len(rows) > limit:
            raise ValueError(f'Lista de {name} inválida ou acima do limite.')
        ids = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Registro inválido.')
            ident = identificador(row.get('id'))
            if ident in ids:
                raise ValueError('Identificador repetido.')
            ids.add(ident)
            try:
                if name == 'contas':
                    nome = str(row.get('nome', '')).strip()
                    if not nome or len(nome) > 80 or row.get('moeda') not in {'BRL', 'USD', 'EUR'}:
                        raise ValueError('Conta inválida.')
                    item = dict(nome=nome, moeda=row['moeda'], saldo_inicial=str(dinheiro(row.get('saldo_inicial'))),
                                data_inicial=date.fromisoformat(row.get('data_inicial', '')).isoformat())
                else:
                    # Contas excluídas ainda podem possuir histórico na lixeira.
                    context = dict(state, contas=[dict(c, excluido=False) for c in state['contas']])
                    item = validar_lancamento(row, context, name == 'recorrencias')
                    if name == 'recorrencias':
                        item['ativa'] = row.get('ativa') is True
                    else:
                        if row.get('ocorrencia'):
                            item['ocorrencia'] = identificador(row['ocorrencia'])
                        if row.get('data_prevista'):
                            item['data_prevista'] = date.fromisoformat(row['data_prevista']).isoformat()
                        item['origem'] = row.get('origem') if row.get('origem') in {'manual', 'recorrencia', 'demo'} else 'manual'
            except (TypeError, KeyError):
                raise ValueError('Campos do registro inválidos.')
            item.update(id=ident, excluido=row.get('excluido') is True)
            state[name].append(item)
    return state
