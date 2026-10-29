'use strict';
(() => {
  const key = 'inview.public.state.v2';
  const legacyKey = 'inview.public.movements.v1';
  const message = 'Demonstração com dados fictícios. Lançamentos, pagamentos e recorrências ficam salvos apenas neste navegador, sem sincronização. Limpar os dados do navegador apaga essas alterações.';
  function read() {
    try {
      const saved = localStorage.getItem(key);
      if (saved) {
        const estado = JSON.parse(saved);
        if (!estado || !Array.isArray(estado.lancamentos)) throw Error();
        return {estado};
      }
      const items = JSON.parse(localStorage.getItem(legacyKey) || '[]');
      if (!Array.isArray(items)) throw Error();
      return {lancamentos:items};
    } catch { throw Error('Não foi possível ler os dados deste navegador. Verifique o armazenamento.'); }
  }
  function save(estado) {
    try { localStorage.setItem(key, JSON.stringify(estado)); }
    catch { throw Error('Não foi possível salvar neste navegador. Libere espaço ou habilite o armazenamento e tente novamente.'); }
  }
  let queue = Promise.resolve();
  window.inviewPublicRequest = (url, options, send) => {
    const task = queue.then(async () => {
      if (url.startsWith('/api/dashboard?')) {
        const result = await send('/api/demo/dashboard' + url.slice('/api/dashboard'.length), {method:'POST',body:JSON.stringify(read())});
        save(result.estado_navegador);
        return result;
      }
      let action;
      const parts = url.split('/').map(decodeURIComponent);
      const values = options.body && !(options.body instanceof FormData) ? JSON.parse(options.body) : {};
      if (url === '/api/realizar') action = {acao:'realizar',id:values.id};
      else if (parts[2] === 'recorrencias' && parts[4] === 'alternar') action = {acao:'alternar',id:parts[3]};
      else if (['lancamentos','recorrencias'].includes(parts[2])) {
        if (parts[4] === 'lixeira') action = {acao:'lixeira',id:parts[3]};
        else if (options.method === 'PUT') action = {acao:'editar',id:parts[3]};
        else if (options.method === 'POST' && !parts[3]) action = {acao:'criar'};
        if (action) action.colecao = parts[2];
      }
      if (action) {
        const result = await send('/api/demo/acao', {method:'POST',body:JSON.stringify({...read(),...action,dados:values})});
        save(result.estado);
        return result.item;
      }
      return send(url, options);
    });
    queue = task.catch(() => {});
    return task;
  };
  function updatePublicView() {
    document.querySelector('#storage-label').textContent = 'Dados · neste navegador';
    const note = document.querySelector('#demo-note');
    note.hidden = false;
    note.textContent = message;
    document.querySelectorAll('[data-action],[data-edit],[data-remove],[data-toggle],[data-settle],[data-restore]').forEach(button => {
      const enabled = ['novo','recorrencia','espaco','lixeira'].includes(button.dataset.action)
        || button.hasAttribute('data-toggle') || button.hasAttribute('data-settle')
        || (['lancamentos','recorrencias'].includes(button.dataset.kind) &&
            ['data-edit','data-remove','data-restore'].some(a => button.hasAttribute(a)));
      button.disabled = !enabled;
      button.title = enabled ? '' : 'Disponível ao executar o projeto localmente';
    });
  }
  document.addEventListener('click', event => {
    if (event.target.closest('[data-action="espaco"]')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openDialog('Seus dados neste navegador', '<p class="form-help">Suas alterações ficam neste navegador. Não há sincronização entre aparelhos. A lixeira permite restaurar lançamentos e recorrências excluídos.</p><button class="button" data-action="lixeira">Abrir lixeira</button>');
    }
  }, true);
  updatePublicView();
  new MutationObserver(updatePublicView).observe(document.querySelector('#page-content'), {childList:true});
  window.addEventListener('storage', event => {
    if ([key,legacyKey,null].includes(event.key) && typeof refresh === 'function') refresh();
  });
})();
