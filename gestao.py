"""Edição e lixeira preservam vínculos e documentos originais."""
from datetime import date, timedelta
from financeiro import hoje, dinheiro, validar_lancamento, ocorrencias


def localizar(estado, colecao, ident):
    if colecao not in {'contas', 'lancamentos', 'recorrencias'}:
        raise ValueError('Cadastro inválido.')
    item = next((i for i in estado[colecao] if i['id'] == ident), None)
    if not item and colecao == 'lancamentos':
        item = next((i for i in ocorrencias(estado, hoje() + timedelta(days=760)) if i['id'] == ident), None)
        if item:
            estado[colecao].append(item)
    if not item:
        raise ValueError('Registro não encontrado.')
    return item


def editar(estado, colecao, ident, entrada):
    item = localizar(estado, colecao, ident)
    if item.get('excluido'):
        raise ValueError('Restaure o registro antes de editar.')
    if colecao == 'contas':
        nome = str(entrada.get('nome', '')).strip()
        if not nome or len(nome) > 80:
            raise ValueError('Informe um nome com até 80 caracteres.')
        inicio = date.fromisoformat(entrada.get('data_inicial', ''))
        if inicio > hoje():
            raise ValueError('O saldo inicial não pode ter data futura.')
        vinculados = [t for t in estado['lancamentos'] + estado['recorrencias'] if t['conta_id'] == ident]
        if any((t.get('data') or t.get('inicio')) < inicio.isoformat() for t in vinculados):
            raise ValueError('O saldo inicial não pode ficar depois de lançamentos ou recorrências existentes.')
        if entrada.get('moeda') != item['moeda']:
            raise ValueError('A moeda da conta não pode ser alterada. Crie outra conta.')
        item.update(nome=nome, saldo_inicial=str(dinheiro(entrada.get('saldo_inicial', ''))), data_inicial=inicio.isoformat())
    else:
        novo = validar_lancamento(entrada, estado, colecao == 'recorrencias')
        if item.get('documento_id'):
            conta = next(c for c in estado['contas'] if c['id'] == novo['conta_id'])
            doc = next(d for d in estado['documentos'] if d['id'] == item['documento_id'])
            if conta['moeda'] != doc['revisao']['moeda']:
                raise ValueError('Mantenha a moeda do documento original.')
        novo.pop('id')
        novo.pop('origem', None)
        novo.pop('ativa', None)
        item.update(novo)
    return item


def lixeira(estado, colecao, ident, restaurar=False):
    item = localizar(estado, colecao, ident)
    if colecao == 'contas' and not restaurar:
        if any(t['conta_id'] == ident and not t.get('excluido') for t in estado['lancamentos'] + estado['recorrencias']):
            raise ValueError('A conta tem movimentos ou recorrências. Remova-os antes de excluir a conta.')
    if restaurar and colecao != 'contas':
        conta = next(c for c in estado['contas'] if c['id'] == item['conta_id'])
        if conta.get('excluido'):
            raise ValueError('Restaure primeiro a conta vinculada.')
    item['excluido'] = not restaurar
    return item
