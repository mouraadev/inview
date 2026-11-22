'use strict';

const valores = (() => {
  const formatos = {'pt-BR': {milhar: '.', decimal: ','}, 'en-US': {milhar: ',', decimal: '.'}};

  function partes(texto, formato) {
    const {milhar, decimal} = formatos[formato];
    const limpo = texto.trim().replace(/^−/, '-');
    const sinal = /^[+-]/.test(limpo) ? limpo[0] : '';
    const [antes, depois, sobra] = limpo.slice(sinal.length).split(decimal);
    const inteira = antes.replaceAll(milhar, '');
    const grupos = antes.split(milhar);
    if (sobra !== undefined || !/^\d*$/.test(inteira) || !/^\d{0,2}$/.test(depois ?? '') ||
        (grupos.length > 1 && (!/^\d{1,3}$/.test(grupos[0]) || grupos.slice(1).some(g => !/^\d{3}$/.test(g))))) {
      throw new Error('Confira os separadores e use até duas casas decimais.');
    }
    return {sinal, inteira, depois};
  }

  function exibir({sinal, inteira, depois}, formato) {
    const {milhar, decimal} = formatos[formato];
    const grupo = inteira.replace(/\B(?=(\d{3})+(?!\d))/g, milhar);
    return sinal + grupo + (depois === undefined ? '' : decimal + depois);
  }

  function normalizar(texto, formato, {negativo = false, positivo = false, limite = 12} = {}) {
    if (!texto.trim()) return '';
    const {sinal, inteira, depois} = partes(texto, formato);
    if (!inteira && !depois) throw new Error('Informe um valor.');
    const digitos = inteira.replace(/^0+(?=\d)/, '') || '0';
    const centavos = (depois || '').padEnd(2, '0');
    if (digitos.length > limite) throw new Error(`Use até ${limite} dígitos antes dos centavos.`);
    if (sinal === '-' && !negativo) throw new Error('Informe um valor sem sinal negativo.');
    if (positivo && digitos === '0' && centavos === '00') throw new Error('Informe um valor maior que zero.');
    return (sinal === '-' ? '-' : '') + digitos + '.' + centavos;
  }

  function formatar(canonico, formato = 'pt-BR') {
    if (!canonico) return '';
    return exibir(partes(canonico, 'en-US'), formato);
  }

  function alternarSinal(texto) {
    return texto.startsWith('-') ? texto.slice(1) : '-' + texto;
  }

  function editarCentavos(texto, {inicio, fim, formato, tecla = '', apagar = '', negativo = false}) {
    if (negativo && /^[-−]$/.test(tecla)) {
      const valor = alternarSinal(inicio === 0 && fim === texto.length ? '' : texto);
      return {texto: valor, cursor: valor.length};
    }
    const digitos = trecho => trecho.replace(/\D/g, '');
    const atual = digitos(texto);
    const sinalAnterior = texto.startsWith('-') ? '-' : '';
    let antes = digitos(texto.slice(0, inicio)).length;
    let depois = digitos(texto.slice(0, fim)).length;
    let sinal = inicio > 0 || fim === 0 ? sinalAnterior : '';
    if (inicio === fim && apagar === 'tras') {
      if (sinal && inicio === 1) sinal = '';
      else antes = Math.max(0, antes - 1);
    } else if (inicio === fim && apagar === 'frente') {
      if (sinal && inicio === 0) sinal = '';
      else depois = Math.min(atual.length, depois + 1);
    }

    if (apagar && antes === depois && sinal === sinalAnterior) return {texto, cursor: inicio};
    const sufixo = atual.slice(depois);
    const novo = atual.slice(0, antes) + tecla + sufixo;
    if (!novo || (apagar && !/[1-9]/.test(novo))) return {texto: '', cursor: 0};
    const numero = novo.replace(/^0+(?=\d)/, '').padStart(3, '0');
    const valor = exibir({sinal, inteira: numero.slice(0, -2), depois: numero.slice(-2)}, formato);
    let cursor = valor.length;
    for (let restantes = sufixo.length; cursor > 0 && restantes > 0;) {
      if (/\d/.test(valor[--cursor])) restantes--;
    }
    return {texto: valor, cursor};
  }

  return {normalizar, formatar, editarCentavos, alternarSinal};
})();
