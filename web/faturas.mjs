const engine = new URL('./pdf-engine/', import.meta.url);
const maxPaginas = 5;
const limiteFatura = 10 * 1024 * 1024;

const rotuloTotal = /\b(?:valor (?:total |integral )?(?:da(?: sua)?|desta|dessa) fatura|(?:valor )?total (?:da(?: sua)?|desta|dessa) fatura|total a pagar)(?: (?:nesta|na) fatura)?\b/g;
const rotuloVencimento = /\b(?:(?:data (?:de|do) )?vencimento(?: (?:da(?: sua)?|desta|dessa) fatura)?(?: em)?|vence em|pague ate)\b/g;
const outrosValores = /\b(?:minim[oa]|parcel(?:a|as|ado|amento)|limite|proxima fatura|melhor dia)\b/;
const meses = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const bancos = [
  'Banco do Brasil', 'Caixa Econômica Federal', 'Caixa', 'Itaú', 'Bradesco', 'Santander',
  'Nubank', 'Banco Inter', 'C6 Bank', 'Banco PAN', 'Banco BV', 'Banco Safra', 'Banco Original',
  'Banco Daycoval', 'Banco BMG', 'Banco do Nordeste', 'Banco da Amazônia', 'Sicredi', 'Sicoob',
  'Banrisul', 'Banestes', 'BRB', 'Banpará', 'Cresol', 'Unicred', 'Ailos', 'BTG Pactual',
  'Neon', 'PicPay', 'PagBank', 'Mercado Pago', 'Credicard', 'Porto Bank', 'Next', 'Will Bank',
];

function normalizar(texto) {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function lerTotal(texto) {
  const valor = texto.match(/^(?:\(r\s*\$\)\s*:?\s*|r\s*\$\s*)?((?:\d{1,3}(?:\.\d{3})+|\d{1,12}),\d{2})(?![\d,.])/u)?.[1];
  const decimal = valor?.replaceAll('.', '').replace(',', '.') ?? '';
  return decimal.length <= 15 && /[1-9]/.test(decimal) ? decimal : '';
}

function lerData(texto) {
  const numerica = texto.match(/^(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})(?!\d)/u);
  const extensa = texto.match(/^(\d{1,2}) de ([a-z]+) de (\d{4})(?!\d)/u);
  if (!numerica && !extensa) return '';
  const [, dia, mesLido, ano] = numerica ?? extensa;
  const mes = numerica ? Number(mesLido) : meses.indexOf(mesLido) + 1;
  if (!mes || mes > 12) return '';
  const iso = `${ano.length === 2 ? '20' + ano : ano}-${String(mes).padStart(2, '0')}-${dia.padStart(2, '0')}`;
  const data = new Date(iso + 'T12:00:00Z');
  return !Number.isNaN(data.getTime()) && data.toISOString().startsWith(iso) ? iso : '';
}

function sugerir(linhas, rotulo, ler) {
  const candidatos = new Set();
  for (const [i, linha] of linhas.entries()) {
    for (const [j, celula] of linha.entries()) {
      const texto = normalizar(celula.texto);
      for (const marca of texto.matchAll(rotulo)) {
        const antes = texto.slice(0, marca.index).trim();
        const depois = texto.slice(marca.index + marca[0].length).replace(/^\s*\(r\s*\$\)/u, '').replace(/^[\s:–—|]+/, '');
        if (outrosValores.test(antes) || (depois && outrosValores.test(depois) && !ler(depois))) continue;
        let valor = ler(depois);
        if (!depois) {
          const aoLado = linha[j + 1];
          const abaixo = linhas[i + 1]?.find(c => c.y - celula.y <= celula.altura * 3.5
            && Math.abs(c.x - celula.x) <= Math.max(celula.altura * 2, 12));
          valor = (aoLado && ler(normalizar(aoLado.texto))) || (abaixo && ler(normalizar(abaixo.texto)));
        }
        if (valor) candidatos.add(valor);
      }
    }
  }
  return candidatos.size === 1 ? candidatos.values().next().value : '';
}

export function sugerirFatura(paginas) {
  const primeirosCampos = (paginas[0] ?? []).slice(0, 12).flat().map(celula => celula.texto);
  const emissor = primeirosCampos.map(texto => texto.match(/^(?:banco emissor|emissor|instituição financeira)\s*:\s*([\p{L}][\p{L} .&-]{1,48})$/iu)?.[1]).find(Boolean);
  const cabecalho = primeirosCampos.map(normalizar);
  const marcas = bancos.filter(nome => cabecalho.some(texto => new RegExp(`\\b${normalizar(nome)}\\b`).test(texto)));
  const distintos = marcas.filter(nome => !marcas.some(outro => outro !== nome && outro.includes(nome)));
  const banco = emissor || (distintos.length === 1 ? distintos[0] : '');
  const linhas = paginas.flat();
  return {
    descricao: banco ? `Fatura · ${banco}` : '',
    valor: sugerir(linhas, rotuloTotal, lerTotal),
    data: sugerir(linhas, rotuloVencimento, lerData),
  };
}

export function linhasDoPdf(itens) {
  const linhas = [];
  const ordenados = itens.filter(item => item.texto.trim()).sort((a, b) => a.y - b.y || a.x - b.x);
  for (const item of ordenados) {
    let linha = linhas.at(-1);
    if (!linha || Math.abs(linha.y - item.y) > Math.max(item.altura * 0.45, 2)) {
      linha = {y: item.y, itens: []};
      linhas.push(linha);
    }
    linha.itens.push(item);
  }
  return linhas.map(({itens}) => {
    const celulas = [];
    for (const item of itens.sort((a, b) => a.x - b.x)) {
      const anterior = celulas.at(-1);
      if (anterior && item.x - anterior.fim < Math.max(item.altura * 1.5, 6)) {
        anterior.texto += ' ' + item.texto;
        anterior.fim = Math.max(anterior.fim, item.x + item.largura);
      } else {
        celulas.push({texto: item.texto, x: item.x, y: item.y, altura: item.altura, fim: item.x + item.largura});
      }
    }
    return celulas;
  });
}

function linhasDoOcr(tsv) {
  return linhasDoPdf(tsv.split('\n').slice(1).flatMap(linha => {
    const [nivel, , , , , , esquerda, topo, largura, altura, , texto] = linha.split('\t');
    return nivel === '5' && texto ? [{texto, x: +esquerda, y: +topo + +altura / 2, altura: +altura, largura: +largura}] : [];
  }));
}

export async function analisarFatura(arquivo, progresso, signal) {
  if (!arquivo?.size || arquivo.size > limiteFatura) throw new Error('Selecione um PDF de até 10 MB.');
  const bytes = new Uint8Array(await arquivo.arrayBuffer());
  if (!new TextDecoder().decode(bytes.subarray(0, 1024)).includes('%PDF-')) {
    throw new Error('Este arquivo não parece ser um PDF. Selecione outro arquivo.');
  }
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  const arquivo_sha256 = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  signal.throwIfAborted();
  const url = caminho => new URL(caminho, engine).href;
  const pdfjs = await import(url('pdfjs/pdf.min.mjs'));
  signal.throwIfAborted();
  pdfjs.GlobalWorkerOptions.workerSrc = url('pdfjs/pdf.worker.min.mjs');
  const tarefa = pdfjs.getDocument({data: bytes, cMapUrl: url('pdfjs/cmaps/'), cMapPacked: true,
    standardFontDataUrl: url('pdfjs/standard_fonts/'), wasmUrl: url('pdfjs/wasm/'), iccUrl: url('pdfjs/iccs/'),
    enableXfa: false, maxImageSize: 16_000_000});
  let ocr;
  try {
    const pdf = await tarefa.promise;
    const quantidade = Math.min(pdf.numPages, maxPaginas);
    const paginas = [];
    for (let n = 1; n <= quantidade; n++) {
      signal.throwIfAborted();
      progresso(`Lendo página ${n} de ${quantidade}…`);
      const pagina = await pdf.getPage(n);
      try {
        const viewport = pagina.getViewport({scale: 1});
        const conteudo = await pagina.getTextContent();
        paginas.push(linhasDoPdf(conteudo.items.flatMap(item => {
          if (!item.str) return [];
          const [x, y] = viewport.convertToViewportPoint(item.transform[4], item.transform[5]);
          return [{texto: item.str, x, y, altura: item.height, largura: item.width}];
        })));
      } finally {
        pagina.cleanup();
      }
    }
    let campos = sugerirFatura(paginas);
    for (let n = 1; n <= quantidade && (!campos.valor || !campos.data); n++) {
      if (n > 1 && paginas[n - 1].length) continue;
      signal.throwIfAborted();
      progresso(`Reconhecendo texto na página ${n}…`);
      try {
        if (!ocr) {
          const {default: {createWorker}} = await import(url('ocr/tesseract.esm.min.js'));
          ocr = await new Promise((resolve, reject) => {
            createWorker('por', 1, {workerPath: url('ocr/worker.min.js'),
              corePath: url('ocr/core/'), langPath: url('ocr/idiomas/'), workerBlobURL: false,
              errorHandler: reject}).then(resolve, reject);
          });
        }
        signal.throwIfAborted();
        const pagina = await pdf.getPage(n);
        const canvas = document.createElement('canvas');
        try {
          const base = pagina.getViewport({scale: 1});
          const escala = Math.min(2.6, Math.sqrt(3_000_000 / (base.width * base.height)));
          const viewport = pagina.getViewport({scale: escala});
          canvas.width = Math.max(1, Math.ceil(viewport.width));
          canvas.height = Math.max(1, Math.ceil(viewport.height));
          await pagina.render({canvas, viewport, annotationMode: 0}).promise;
          signal.throwIfAborted();
          const resultado = await ocr.recognize(canvas, {}, {tsv: true});
          const lido = sugerirFatura([linhasDoOcr(resultado.data.tsv ?? '')]);
          campos = {descricao: campos.descricao || (n === 1 ? lido.descricao : ''),
            valor: campos.valor || lido.valor, data: campos.data || lido.data};
        } finally {
          canvas.width = canvas.height = 0;
          pagina.cleanup();
        }
      } catch {
        signal.throwIfAborted();
        // Os campos revisáveis continuam disponíveis se o OCR falhar neste aparelho.
        break;
      }
    }
    signal.throwIfAborted();
    return {campos, arquivo_sha256};
  } catch (falha) {
    signal.throwIfAborted();
    if (falha.name === 'PasswordException') throw new Error('Selecione uma versão do PDF sem senha.');
    if (falha.name === 'InvalidPDFException') throw new Error('Não foi possível abrir este PDF. Selecione outro arquivo.');
    throw falha;
  } finally {
    try {
      await ocr?.terminate();
    } finally {
      await tarefa.destroy();
    }
  }
}
