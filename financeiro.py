from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

CATEGORIAS = ['Salário', 'Renda extra', 'Moradia', 'Alimentação', 'Transporte',
              'Assinaturas', 'Saúde', 'Lazer', 'Compras', 'Outros']


def hoje():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def dinheiro(valor):
    if not isinstance(valor, str):
        raise ValueError('Informe o valor como texto decimal.')
    import re
    if not re.fullmatch(r'-?[0-9]{1,12}(?:\.[0-9]{1,2})?', valor):
        raise ValueError('Valor inválido. Use até duas casas decimais.')
    return Decimal(valor).quantize(Decimal('0.01'))


def mes_data(mes, dia=1):
    inicio = date.fromisoformat(mes + '-01')
    return inicio.replace(day=min(dia, monthrange(inicio.year, inicio.month)[1]))


def meses_entre(inicio, fim):
    atual = inicio.replace(day=1)
    while atual <= fim:
        yield atual.strftime('%Y-%m')
        atual = (atual.replace(day=28) + timedelta(days=4)).replace(day=1)


def vazio():
    return {'contas': [{'id': 'principal', 'nome': 'Conta principal', 'moeda': 'BRL',
                       'saldo_inicial': '0.00', 'data_inicial': hoje().replace(day=1).isoformat()}],
            'lancamentos': [], 'recorrencias': [], 'documentos': []}


def demonstracao():
    agora = hoje()
    mes = agora.strftime('%Y-%m')
    inicio = agora.replace(day=1)
    estado = vazio()
    estado['contas'] = [
        {'id': 'principal', 'nome': 'Conta do dia a dia', 'moeda': 'BRL', 'saldo_inicial': '5240.00', 'data_inicial': inicio.isoformat()},
        {'id': 'reserva', 'nome': 'Reserva pessoal', 'moeda': 'BRL', 'saldo_inicial': '8200.00', 'data_inicial': inicio.isoformat()},
    ]
    regras = [('salario', 'Salário', 'entrada', '8500.00', 5, 'Salário'),
              ('aluguel', 'Aluguel', 'saida', '2200.00', 10, 'Moradia'),
              ('internet', 'Internet', 'saida', '119.90', 15, 'Moradia'),
              ('spotify', 'Spotify Premium', 'saida', '21.90', 28, 'Assinaturas'),
              ('icloud', 'iCloud+', 'saida', '14.90', 29, 'Assinaturas'),
              ('freela', 'Projeto freelance', 'entrada', '1800.00', 30, 'Renda extra')]
    for ident, nome, tipo, valor, dia, categoria in regras:
        regra = dict(id=ident, descricao=nome, tipo=tipo, valor=valor, dia=dia,
                     categoria=categoria, conta_id='principal', inicio=inicio.isoformat(), ativa=True)
        estado['recorrencias'].append(regra)
        prevista = mes_data(mes, dia)
        if prevista <= agora:
            estado['lancamentos'].append(dict(id=uuid4().hex, descricao=nome, tipo=tipo, valor=valor,
                categoria=categoria, conta_id='principal', data=prevista.isoformat(), status='realizado',
                ocorrencia=f'{ident}:{prevista.isoformat()}', origem='demo'))
    for dia, nome, valor, categoria in [(3, 'Mercado da semana', '286.40', 'Alimentação'),
            (7, 'Café e companhia', '38.50', 'Alimentação'), (12, 'Uber', '27.90', 'Transporte'),
            (18, 'Farmácia', '86.30', 'Saúde'), (21, 'Jantar de sexta', '142.00', 'Lazer'),
            (24, 'Mercado da semana', '324.65', 'Alimentação'), (26, 'Livraria', '79.90', 'Compras')]:
        if dia <= agora.day:
            estado['lancamentos'].append(dict(id=uuid4().hex, descricao=nome, tipo='saida', valor=valor,
                categoria=categoria, conta_id='principal', data=mes_data(mes, dia).isoformat(),
                status='realizado', origem='demo'))
    return estado


def validar_lancamento(entrada, estado, recorrencia=False):
    if not isinstance(entrada, dict):
        raise ValueError('Informe os campos do lançamento.')
    descricao = str(entrada.get('descricao', '')).strip()
    if not descricao or len(descricao) > 150:
        raise ValueError('Descrição obrigatória, com até 150 caracteres.')
    if entrada.get('tipo') not in {'entrada', 'saida'}:
        raise ValueError('Escolha entrada ou saída.')
    valor = dinheiro(entrada.get('valor', ''))
    if valor <= 0:
        raise ValueError('O valor deve ser maior que zero.')
    conta = next((c for c in estado['contas'] if c['id'] == entrada.get('conta_id')), None)
    if not conta or conta.get('excluido'):
        raise ValueError('Selecione uma conta válida.')
    if entrada.get('categoria') not in CATEGORIAS:
        raise ValueError('Selecione uma categoria válida.')
    r = {k: entrada[k] for k in ('tipo', 'conta_id', 'categoria')}
    r.update(id=uuid4().hex, descricao=descricao, valor=str(valor))
    if recorrencia:
        try:
            dia = int(entrada.get('dia', 0))
        except (TypeError, ValueError):
            raise ValueError('Dia inválido.')
        if not 1 <= dia <= 31:
            raise ValueError('O dia deve estar entre 1 e 31.')
        inicio = date.fromisoformat(entrada.get('inicio', ''))
        if inicio < date.fromisoformat(conta['data_inicial']):
            raise ValueError('A recorrência não pode iniciar antes do saldo inicial da conta.')
        r.update(dia=dia, inicio=inicio.isoformat(), ativa=True)
    else:
        data = date.fromisoformat(entrada.get('data', ''))
        status = entrada.get('status')
        if status not in {'previsto', 'realizado'}:
            raise ValueError('Escolha previsto ou realizado.')
        if data < date.fromisoformat(conta['data_inicial']):
            raise ValueError('O lançamento é anterior ao saldo inicial desta conta.')
        if status == 'realizado' and data > hoje():
            raise ValueError('Uma movimentação futura deve ficar como prevista.')
        r.update(data=data.isoformat(), status=status, origem='manual')
    return r


def ocorrencias(estado, fim):
    realizadas = {t.get('ocorrencia') for t in estado['lancamentos']}
    resultado = []
    for r in estado['recorrencias']:
        if not r['ativa'] or r.get('excluido'):
            continue
        for mes in meses_entre(date.fromisoformat(r['inicio']), fim):
            data = mes_data(mes, r['dia'])
            chave = f"{r['id']}:{data.isoformat()}"
            if data < date.fromisoformat(r['inicio']) or data > fim or chave in realizadas or any(k and k.rsplit('-', 1)[0] == chave.rsplit('-', 1)[0] for k in realizadas):
                continue
            resultado.append(dict(r, id=chave, ocorrencia=chave, data=data.isoformat(), status='previsto', origem='recorrencia'))
    return resultado


def realizar(estado, identificador):
    item = next((t for t in estado['lancamentos'] if t['id'] == identificador), None)
    if item:
        if item.get('excluido'):
            raise ValueError('Restaure o lançamento antes de confirmar.')
        if item['status'] != 'previsto':
            raise ValueError('Este lançamento já foi realizado.')
        item['data_prevista'] = item['data']
        item.update(status='realizado', data=hoje().isoformat())
        return item
    if any(t.get('ocorrencia') == identificador for t in estado['lancamentos']):
        raise ValueError('Esta ocorrência já foi realizada.')
    limite = hoje() + timedelta(days=760)
    item = next((t for t in ocorrencias(estado, limite) if t['id'] == identificador), None)
    if not item:
        raise ValueError('Lançamento não encontrado ou recorrência pausada.')
    item = dict(item, id=uuid4().hex, data_prevista=item['data'], data=hoje().isoformat(), status='realizado')
    estado['lancamentos'].append(item)
    return item


def resumo(estado, mes, conta_id='todas', moeda='BRL'):
    atual = hoje()
    inicio = mes_data(mes)
    fim = mes_data(mes, 31)
    if abs((inicio.year - atual.year) * 12 + inicio.month - atual.month) > 24:
        raise ValueError('Escolha um mês até 24 meses antes ou depois de hoje.')
    contas = [c for c in estado['contas'] if not c.get('excluido') and c['moeda'] == moeda and (conta_id == 'todas' or c['id'] == conta_id)]
    ids = {c['id'] for c in contas}
    todos = [t for t in estado['lancamentos'] if t['conta_id'] in ids and not t.get('excluido')]
    planos = [t for t in todos if t['status'] == 'previsto'] + [t for t in ocorrencias(estado, max(fim, atual)) if t['conta_id'] in ids]
    efetivos = [t for t in todos if t['status'] == 'realizado']
    def soma(itens, tipo=None):
        return sum((dinheiro(t['valor']) * (1 if t['tipo'] == 'entrada' else -1)
                    for t in itens if tipo is None or t['tipo'] == tipo), Decimal('0'))
    def saldo(data):
        return sum((dinheiro(c['saldo_inicial']) for c in contas if c['data_inicial'] <= data.isoformat()), Decimal('0')) + soma(t for t in efetivos if t['data'] <= data.isoformat())
    periodo = [t for t in efetivos if inicio.isoformat() <= t['data'] <= fim.isoformat()]
    futuros = [t for t in planos if atual.isoformat() <= t['data'] <= fim.isoformat()]
    futuros_periodo = [t for t in futuros if t['data'] >= inicio.isoformat()]
    atrasados = [t for t in planos if t['data'] < atual.isoformat()]
    serie = []
    for dia in range(1, fim.day + 1):
        data = inicio.replace(day=dia)
        valor = saldo(min(data, atual))
        if data > atual:
            valor += soma(t for t in futuros if t['data'] <= data.isoformat())
        serie.append({'dia': dia, 'data': data.isoformat(), 'valor': str(valor), 'previsto': data > atual})
    categorias = []
    for categoria in CATEGORIAS:
        valor = -soma((t for t in periodo if t['categoria'] == categoria), 'saida')
        if valor:
            categorias.append({'categoria': categoria, 'valor': str(valor)})
    categorias.sort(key=lambda c: dinheiro(c['valor']), reverse=True)
    proximos = sorted([t for t in planos if inicio.isoformat() <= t['data'] <= fim.isoformat()], key=lambda t: t['data'])
    return {'hoje': atual.isoformat(), 'mes': mes, 'moeda': moeda, 'conta_id': conta_id,
            'saldo_atual': str(saldo(atual)),
            'saldo_final': str(saldo(fim) if fim < atual else saldo(atual) + soma(futuros)),
            'entradas': str(soma(periodo, 'entrada')), 'saidas': str(-soma(periodo, 'saida')),
            'entradas_previstas': str(soma(futuros_periodo, 'entrada')), 'saidas_previstas': str(-soma(futuros_periodo, 'saida')),
            'serie': serie, 'categorias': categorias, 'atrasados': len(atrasados),
            'lancamentos': sorted(periodo + proximos, key=lambda t: t['data'], reverse=True),
            'proximos': proximos,
            'pendencias': sorted(atrasados, key=lambda t: t['data']),
            'recorrencias': [r for r in estado['recorrencias'] if r['conta_id'] in ids and not r.get('excluido')],
            'contas': [dict(c, saldo=str(dinheiro(c['saldo_inicial']) + soma(t for t in efetivos if t['conta_id'] == c['id'] and t['data'] <= atual.isoformat()))) for c in contas]}
