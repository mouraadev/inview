import base64
import json
import os
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_file
import pymysql

from extracao import extrair_documento
from validacao import validar_fatura
from financeiro import CATEGORIAS, hoje, resumo, validar_lancamento, realizar, dinheiro
from repositorio_financeiro import Repositorio
from gestao import editar, lixeira


def criar_app(repositorio=None):
    app = Flask(__name__, static_folder='web', static_url_path='/assets')
    app.config['MAX_CONTENT_LENGTH'] = 11 * 1024 * 1024
    repo = repositorio or Repositorio(os.environ.get('INVIEW_MODO', 'demo'))

    def current_repo():
        if repositorio or repo.modo == 'mysql':
            return repo
        return Repositorio(request.cookies.get('inview_espaco', repo.modo) if request.cookies.get('inview_espaco', repo.modo) in {'demo', 'local'} else repo.modo)

    @app.before_request
    def origem_local():
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            if request.headers.get('X-Inview') != 'local':
                return jsonify(erro='Requisição não autorizada.'), 403
            origem = request.headers.get('Origin')
            if origem and origem != request.host_url.rstrip('/'):
                return jsonify(erro='Origem não autorizada.'), 403
            if request.is_json and not isinstance(request.get_json(silent=True), dict):
                return jsonify(erro='Informe um objeto com os campos do formulário.'), 400

    @app.errorhandler(ValueError)
    def invalido(exc):
        return jsonify(erro=str(exc)), 400

    @app.errorhandler(pymysql.MySQLError)
    def erro_mysql(exc):
        return jsonify(erro='MySQL indisponível. Confira a conexão e execute dashboard.py --init-db.'), 503

    @app.errorhandler(413)
    def tamanho(exc):
        return jsonify(erro='O PDF deve ter até 10 MB.'), 413

    @app.get('/')
    def index():
        return app.send_static_file('index.html')

    @app.get('/api/dashboard')
    def dados():
        with current_repo().transacao() as estado:
            resultado = resumo(estado, request.args.get('mes', hoje().strftime('%Y-%m')),
                               request.args.get('conta', 'todas'), request.args.get('moeda', 'BRL'))
            resultado.update(modo=current_repo().modo, categorias_disponiveis=CATEGORIAS,
                             todas_contas=[c for c in estado['contas'] if not c.get('excluido')],
                             lixeira=[dict(i, colecao=k) for k in ('contas', 'lancamentos', 'recorrencias') for i in estado[k] if i.get('excluido')],
                             documentos=[{k: d[k] for k in ('id', 'nome', 'criado_em', 'descricao', 'lancamento_id')} for d in estado['documentos']])
        return jsonify(resultado)

    @app.post('/api/lancamentos')
    def adicionar():
        with current_repo().transacao() as estado:
            item = validar_lancamento(request.get_json(), estado)
            estado['lancamentos'].append(item)
        return jsonify(item), 201

    @app.post('/api/recorrencias')
    def recorrencia():
        with current_repo().transacao() as estado:
            item = validar_lancamento(request.get_json(), estado, recorrencia=True)
            estado['recorrencias'].append(item)
        return jsonify(item), 201

    @app.post('/api/recorrencias/<ident>/alternar')
    def alternar(ident):
        with current_repo().transacao() as estado:
            regra = next((r for r in estado['recorrencias'] if r['id'] == ident), None)
            if not regra or regra.get('excluido'):
                raise ValueError('Recorrência não encontrada.')
            regra['ativa'] = not regra['ativa']
        return jsonify(ok=True)

    @app.post('/api/realizar')
    def liquidar():
        with current_repo().transacao() as estado:
            item = realizar(estado, request.get_json().get('id'))
        return jsonify(item)

    @app.post('/api/contas')
    def conta():
        entrada = request.get_json()
        nome = str(entrada.get('nome', '')).strip()
        if not nome or len(nome) > 80 or entrada.get('moeda') not in {'BRL', 'USD', 'EUR'}:
            raise ValueError('Informe um nome e uma moeda válida.')
        inicio = date.fromisoformat(entrada.get('data_inicial', ''))
        if inicio > hoje():
            raise ValueError('A data do saldo inicial não pode ser futura.')
        item = dict(id=uuid4().hex, nome=nome, moeda=entrada['moeda'],
                    saldo_inicial=str(dinheiro(entrada.get('saldo_inicial', ''))), data_inicial=inicio.isoformat())
        with current_repo().transacao() as estado:
            estado['contas'].append(item)
        return jsonify(item), 201

    @app.post('/api/pdf/analisar')
    def analisar():
        arquivo = request.files.get('arquivo')
        if arquivo is None:
            raise ValueError('Selecione um PDF.')
        conteudo = arquivo.read()
        extracao = extrair_documento(conteudo)
        with current_repo().transacao(gravar=False) as estado:
            if any(d['id'] == extracao['sha256'] for d in estado['documentos']):
                raise ValueError('Este arquivo já foi importado. Consulte Documentos.')
        return jsonify(extracao)

    @app.post('/api/pdf/confirmar')
    def confirmar_pdf():
        arquivo = request.files.get('arquivo')
        if arquivo is None:
            raise ValueError('Selecione um PDF.')
        entrada = json.loads(request.form.get('revisao', '{}'))
        if not entrada.get('confirmado'):
            raise ValueError('Confirme a revisão do documento.')
        conteudo = arquivo.read()
        extracao = extrair_documento(conteudo)
        dados, erros, avisos = validar_fatura(entrada.get('campos', {}), entrada.get('formato', ''), entrada.get('ordem', ''))
        if erros:
            raise ValueError(' '.join(erros))
        if avisos and not entrada.get('aceitar_avisos'):
            raise ValueError(' '.join(avisos) + ' Confirme os avisos para continuar.')
        with current_repo().transacao() as estado:
            if any(d['id'] == extracao['sha256'] for d in estado['documentos']):
                raise ValueError('Este mesmo arquivo já foi importado.')
            repetido = any(d['revisao']['fornecedor'].casefold() == dados['fornecedor'].casefold()
                          and d['revisao']['numero_fatura'].casefold() == dados['numero_fatura'].casefold() for d in estado['documentos'])
            if repetido and not entrada.get('aceitar_duplicidade'):
                raise ValueError('Mesmo fornecedor e número já importados. Confira e aceite a possível duplicidade para continuar.')
            conta = next((c for c in estado['contas'] if c['id'] == entrada.get('conta_id')), None)
            if not conta or conta.get('excluido') or conta['moeda'] != dados['moeda']:
                raise ValueError('A moeda da fatura precisa ser igual à moeda da conta.')
            item = validar_lancamento(dict(descricao=dados['fornecedor'] + ' · ' + dados['numero_fatura'],
                tipo=entrada.get('tipo', 'saida'), conta_id=entrada.get('conta_id'), categoria=entrada.get('categoria'),
                valor=str(dados['total']), data=entrada.get('data_prevista', ''), status='previsto'), estado)
            item.update(origem='pdf', documento_id=extracao['sha256'])
            estado['lancamentos'].append(item)
            estado['documentos'].append(dict(id=extracao['sha256'], nome=Path(arquivo.filename).name,
                criado_em=hoje().isoformat(), descricao=item['descricao'], lancamento_id=item['id'],
                pdf=base64.b64encode(conteudo).decode(), extracao=extracao,
                revisao=json.loads(json.dumps(dados, default=str)), entrada_revisada=entrada,
                avisos=avisos))
        return jsonify(item), 201

    @app.get('/api/documentos/<ident>')
    def documento(ident):
        with current_repo().transacao(gravar=False) as estado:
            doc = next((d for d in estado['documentos'] if d['id'] == ident), None)
            if not doc:
                raise ValueError('Documento não encontrado.')
            return send_file(BytesIO(base64.b64decode(doc['pdf'])), mimetype='application/pdf',
                             as_attachment=True, download_name=doc['nome'])

    @app.post('/api/espaco')
    def espaco():
        modo = request.get_json().get('modo')
        if repo.modo == 'mysql' or modo not in {'demo', 'local'}:
            raise ValueError('Espaço inválido.')
        resposta = jsonify(ok=True)
        resposta.set_cookie('inview_espaco', modo, httponly=True, samesite='Strict', max_age=31536000)
        return resposta

    @app.put('/api/<colecao>/<ident>')
    def atualizar(colecao, ident):
        with current_repo().transacao() as estado:
            item = editar(estado, colecao, ident, request.get_json())
        return jsonify(item)

    @app.post('/api/<colecao>/<ident>/lixeira')
    def remover(colecao, ident):
        with current_repo().transacao() as estado:
            item = lixeira(estado, colecao, ident, request.get_json().get('restaurar') is True)
        return jsonify(item)

    @app.get('/api/backup')
    def backup():
        with current_repo().transacao(gravar=False) as estado:
            conteudo = json.dumps(estado, ensure_ascii=False, indent=2).encode('utf-8')
        return send_file(BytesIO(conteudo), mimetype='application/json', as_attachment=True,
                         download_name='inview-backup-' + hoje().isoformat() + '.json')

    return app


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--init-db', action='store_true')
    args = parser.parse_args()
    if args.init_db:
        Repositorio('mysql').inicializar_mysql()
        print('Estrutura financeira MySQL pronta.')
    else:
        criar_app().run(host='127.0.0.1', port=args.port, debug=False)
