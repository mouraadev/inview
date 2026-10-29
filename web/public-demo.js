'use strict';
(() => {
  const key = 'inview.public.movements.v1';
  const message = 'Demonstração com dados fictícios. Novas entradas e saídas ficam salvas apenas neste navegador, sem sincronização. Limpar os dados do navegador apaga seus lançamentos.';
  function read() {
    try {
      const items = JSON.parse(localStorage.getItem(key) || '[]');
      if (!Array.isArray(items)) throw Error();
      return items;
    } catch { throw Error('Não foi possível ler os lançamentos deste navegador. Verifique se o armazenamento está disponível.'); }
  }
  window.inviewPublicRequest = async (url, options, send) => {
    if (url.startsWith('/api/dashboard?')) {
      return send('/api/demo/dashboard' + url.slice('/api/dashboard'.length), {
        method:'POST', body:JSON.stringify({lancamentos:read()})
      });
    }
    if (url === '/api/lancamentos' && options.method === 'POST') {
      const result = await send('/api/demo/lancamentos', {
        method:'POST', body:JSON.stringify({lancamentos:read(),novo:JSON.parse(options.body)})
      });
      try { localStorage.setItem(key, JSON.stringify(result.lancamentos)); }
      catch { throw Error('Não foi possível salvar neste navegador. Libere espaço ou habilite o armazenamento e tente novamente.'); }
      return result;
    }
    return send(url, options);
  };
  function updatePublicView() {
    document.querySelector('#storage-label').textContent = 'Lançamentos · neste navegador';
    const note = document.querySelector('#demo-note');
    note.hidden = false;
    note.textContent = message;
    document.querySelectorAll('[data-action],[data-edit],[data-remove],[data-toggle],[data-settle],[data-restore]').forEach(button => {
      const enabled = button.dataset.action === 'novo';
      button.disabled = !enabled;
      button.title = enabled ? 'Cadastrar entrada ou saída, prevista ou realizada' : 'Disponível ao executar o projeto localmente';
    });
  }
  updatePublicView();
  new MutationObserver(updatePublicView).observe(document.querySelector('#page-content'), {childList:true});
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) {
      if (typeof refresh === 'function') refresh();
    }
  });
})();
