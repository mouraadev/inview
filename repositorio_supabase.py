from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import g

from financeiro import vazio
from supabase_api import ErroSupabase


class ConflitoFinanceiro(Exception):
    """O espaço foi atualizado entre a leitura e a gravação."""


class RepositorioHospedado:
    rota = '/rest/v1/espacos_financeiros'

    def __init__(self, supabase):
        self.supabase = supabase

    @property
    def modo(self):
        return 'demo' if 'demo_estado' in g else 'online'

    @contextmanager
    def transacao(self, gravar=True):
        if self.modo == 'demo':
            yield g.demo_estado
            return

        usuario = g.usuario
        token = g.token
        filtro = {'usuario_id': f"eq.{usuario['id']}"}
        registros = self.supabase.requisitar('GET', self.rota, token=token,
                                            params={**filtro, 'select': 'estado,revisao'})
        registro = registros[0] if registros else None
        if registro is None:
            estado = vazio()
            criacao = datetime.fromisoformat(usuario['created_at']).astimezone(ZoneInfo('America/Sao_Paulo'))
            estado['contas'][0]['data_inicial'] = criacao.date().replace(day=1).isoformat()
        else:
            estado = registro['estado']
        yield estado
        if not gravar:
            return

        if registro is None:
            try:
                self.supabase.requisitar('POST', self.rota, token=token,
                                         dados={'usuario_id': usuario['id'], 'estado': estado})
            except ErroSupabase as exc:
                if exc.status == 409 and exc.codigo == '23505':
                    raise ConflitoFinanceiro() from None
                raise
        else:
            revisao = registro['revisao']
            atualizados = self.supabase.requisitar(
                'PATCH', self.rota, token=token, prefer='return=representation',
                params={**filtro, 'revisao': f'eq.{revisao}', 'select': 'revisao'},
                dados={'estado': estado, 'revisao': revisao + 1})
            if not atualizados:
                raise ConflitoFinanceiro()
