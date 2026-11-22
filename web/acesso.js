'use strict';

const form = document.querySelector('#auth-form');
const statusBox = document.querySelector('#auth-status');
const errorBox = document.querySelector('#auth-error');
const password = document.querySelector('#senha');
const toggle = document.querySelector('#toggle-senha');
const submit = form.querySelector('[type="submit"]');
const mode = form.dataset.modo;
const passwordFlow = mode === 'invite' || mode === 'recovery';
const query = new URLSearchParams(location.search);
const fragment = new URLSearchParams(location.hash.slice(1));
let linkData = passwordFlow && fragment.has('token_hash') ? { token_hash: fragment.get('token_hash') } : {};
if (mode === 'recovery' && query.has('code')) linkData = { codigo: query.get('code') };

if (location.search || location.hash) history.replaceState(null, '', location.pathname);

function message(box, content, focus = true) {
  box.textContent = content;
  box.hidden = !content;
  if (content && focus) box.focus();
}

if (query.get('senha') === 'definida' && mode === 'entrar') {
  message(statusBox, 'Senha salva. Entre para abrir seu espaço.', false);
}
if (passwordFlow && (query.has('error_code') || fragment.has('error_code') || fragment.has('access_token'))) {
  message(errorBox, 'Este link não pode ser usado. Solicite um novo para continuar.', false);
}

if (toggle) {
  toggle.hidden = false;
  toggle.addEventListener('click', () => {
    const show = password.type === 'password';
    password.type = show ? 'text' : 'password';
    toggle.textContent = show ? 'Ocultar' : 'Mostrar';
    toggle.setAttribute('aria-label', show ? 'Ocultar senha' : 'Mostrar senha');
  });
  toggle.setAttribute('aria-label', 'Mostrar senha');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submit.disabled) return;

  const fields = Object.fromEntries(new FormData(form));
  const values = passwordFlow ? { ...fields, tipo: mode, ...linkData } : fields;
  message(errorBox, '');
  message(statusBox, mode === 'entrar' ? 'Entrando…' : mode === 'recuperar' ? 'Enviando…' : 'Salvando senha…', false);
  submit.disabled = true;
  form.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Inview': 'local' },
      body: JSON.stringify(values),
    });
    const result = await response.json();
    if (result.verificado) linkData = {};
    if (!response.ok) throw new Error(result.erro);
    if (result.destino) {
      form.reset();
      location.replace(result.destino);
    } else {
      message(statusBox, result.mensagem);
    }
  } catch (error) {
    message(statusBox, '');
    message(errorBox, error instanceof Error && !(error instanceof TypeError || error instanceof SyntaxError)
      ? error.message : 'Não foi possível concluir. Confira a conexão e tente novamente.');
  } finally {
    form.removeAttribute('aria-busy');
    submit.disabled = false;
  }
});
