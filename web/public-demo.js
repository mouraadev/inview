'use strict';
// Carregado apenas na versão pública gerada por build_vercel.py.
(() => {
  const message = 'Demonstração pública com dados fictícios, somente para consulta. Para importar faturas e salvar alterações, execute o projeto localmente.';
  const selectors = '[data-action],[data-edit],[data-remove],[data-toggle],[data-settle],[data-restore]';
  function updatePublicView() {
    document.querySelector('#storage-label').textContent = 'Demo pública · somente consulta';
    const note = document.querySelector('#demo-note');
    note.hidden = false;
    note.textContent = message;
    document.querySelectorAll(selectors).forEach(button => {
      button.disabled = true;
      button.title = 'Disponível ao executar o projeto localmente';
    });
  }
  updatePublicView();
  new MutationObserver(updatePublicView).observe(document.querySelector('#page-content'), {childList:true});
})();
