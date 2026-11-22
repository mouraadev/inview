'use strict';
const paths = {
  grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  wallet:'M20 8V5a2 2 0 0 0-2-2H5a3 3 0 0 0 0 6h16v11H5a3 3 0 0 1-3-3V6 M21 12h-6v5h6 M17 14.5h.1',
  calendar:'M8 2v4 M16 2v4 M3 10h18 M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2 M7 14h2 M13 14h2 M7 17h2',
  arrows:'M4 7h15 M15 3l4 4-4 4 M20 17H5 M9 13l-4 4 4 4',
  file:'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  scan:'M8 3H3v5 M16 3h5v5 M3 16v5h5 M21 16v5h-5 M7 8h10 M7 12h10 M7 16h6',
  'arrow-right':'M4 12h16 M14 6l6 6-6 6',
  shield:'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',
  home:'M3 10l9-7 9 7 M5 9v12h14V9 M9 21v-8h6v8',
  eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12 M15 12a3 3 0 1 0-6 0 3 3 0 0 0 6 0',
  hidden:'M3 3l18 18 M9 5c1-.3 2-.5 3-.5 6 0 10 7.5 10 7.5a19 19 0 0 1-4 4 M6 6a22 22 0 0 0-4 6s4 7 10 7c2 0 3-.5 4-1',
  plus:'M12 5v14 M5 12h14',left:'M15 5l-7 7 7 7',right:'M9 5l7 7-7 7',
  chevrons:'M9 8l3-3 3 3 M9 16l3 3 3-3',close:'M6 6l12 12 M6 18L18 6',
  lock:'M6 10h12v11H6z M8 10V7a4 4 0 0 1 8 0v3',
  trend:'M3 17l6-6 4 3 8-10 M15 4h6v6',
  down:'M7 7l10 10 M7 17h10V7',up:'M7 17L17 7 M7 7h10v10',
  repeat:'M3 10V6h15l3 3 M21 14v4H6l-3-3 M3 6l3-3 M21 18l-3 3',
  info:'M12 8h.01 M12 11v6 M22 12a10 10 0 1 0-20 0 10 10 0 0 0 20 0',
  music:'M9 17V5l11-2v12 M9 8l11-2 M9 17c0 4-7 4-7 1s7-5 7-1 M20 15c0 4-7 4-7 1s7-5 7-1',
  cloud:'M7 18a5 5 0 1 1 .8-9.9A6 6 0 0 1 19 8a5 5 0 0 1 0 10z',
  bag:'M5 7h14l2 14H3z M8 8V6a4 4 0 0 1 8 0v2',
  coffee:'M4 8h12v7a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z M16 8h2a3 3 0 0 1 0 6h-2 M7 2v3 M12 2v3',
  check:'M5 12l4 4L19 6',download:'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
};
const icon = (name) => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`;
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const privatePage = location.pathname === '/app';
if (privatePage) {
  document.querySelectorAll('[data-view="documentos"], [data-action="importar"]').forEach(button => button.remove());
  $('#mode-badge').textContent = 'Meu espaço';
  $('#demo-note').hidden = true;
  window.addEventListener('pageshow', event => {
    if (event.persisted) location.reload();
  });
}
function mountIcons(){document.querySelectorAll('[data-icon]').forEach(el => {el.innerHTML=icon(el.dataset.icon);});}
mountIcons();
let data, view='visao', hidden=false, refreshId=0;
let month=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit'}).format(new Date());
let account='todas', currency='BRL';
const labels={visao:'Visão geral',lancamentos:'Lançamentos',planejamento:'Planejamento',contas:'Minhas contas',documentos:'Documentos'};
const titles={visao:'Seu próximo mês começa aqui.',lancamentos:'Cada movimento conta.',planejamento:'Planeje hoje. Respire amanhã.',contas:'Suas contas. Uma só visão.',documentos:'Menos digitação. Mais controle.'};
const subtitles={visao:'Entradas, saídas e planos. Uma visão completa do que vem pela frente.',lancamentos:'Acompanhe o que entrou, saiu e ainda está por vir.',planejamento:'Salário, aluguel e assinaturas. Seu mês já começa organizado.',contas:'Saldos separados por conta. Uma visão mais completa.',documentos:'Importe, confira e transforme suas faturas em saídas previstas.'};
const palette=['#c2f970','#7dbb8c','#78b7c7','#b3a2df','#dfb67b','#dc8e7b','#93a76a','#9da8b2'];
const money=(value, code=currency)=>hidden?'••••••':new Intl.NumberFormat('pt-BR',{style:'currency',currency:code}).format(Number(value));
const dateLabel=(value)=>new Date(value+'T12:00:00').toLocaleDateString('pt-BR',{day:'2-digit',month:'short'}).replace('.','');
const monthLabel=(value)=>new Date(value+'-01T12:00:00').toLocaleDateString('pt-BR',{month:'long',year:'numeric'}).replace(' de ',' ');
const sum=(list,type)=>list.filter(x=>!type||x.tipo===type).reduce((a,x)=>a+Number(x.valor),0);
function badge(t){return t.status==='realizado'?'<span class="status-chip">Realizado</span>':t.data<data.hoje?'<span class="status-chip late">Em atraso</span>':'<span class="status-chip pending">Previsto</span>';}
function itemIcon(t){let i=t.tipo==='entrada'?'up':t.categoria==='Moradia'?'home':t.descricao.toLowerCase().includes('spotify')?'music':t.descricao.toLowerCase().includes('icloud')?'cloud':t.categoria==='Alimentação'?'coffee':'bag';return `<span class="item-icon ${t.tipo==='entrada'?'income':i}">${icon(i)}</span>`;}
function notify(text){$('#toast').textContent=text;$('#toast').classList.add('show');clearTimeout(notify.timer);notify.timer=setTimeout(()=>$('#toast').classList.remove('show'),3200);}
async function api(url, options={}){return window.inviewPublicRequest?window.inviewPublicRequest(url,options,requestApi):requestApi(url,options);}
async function requestApi(url, options={}) {
  const response = await fetch(url, {...options, headers: {
    'X-Inview': 'local',
    ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
    ...options.headers,
  }});
  if (privatePage && response.status === 401) {
    data = null;
    $('#page-content').replaceChildren();
    closeDialog();
    location.replace('/');
  }
  let result;
  try {
    result = await response.json();
  } catch {
    throw Error('Não foi possível ler a resposta do servidor.');
  }
  if (!response.ok) throw Error(result.erro || 'Não foi possível concluir.');
  return result;
}

async function refresh() {
  const id = ++refreshId;
  try {
    const result = await api(`/api/dashboard?mes=${encodeURIComponent(month)}&conta=${encodeURIComponent(account)}&moeda=${currency}`);
    if (id !== refreshId) return;
    data = result;
    $('#month').value = month;
    $('#month-name').textContent = monthLabel(month);
    $('#mode-badge').textContent = data.modo === 'demo' ? 'Demonstração' : 'Meu espaço';
    const storage = {
      demo: 'Dados locais · demonstração', local: 'Dados pessoais · neste computador',
      mysql: 'Conectado ao MySQL', online: 'Dados sincronizados',
    };
    $('#storage-label').textContent = storage[data.modo];
    $('#demo-note').hidden = data.modo !== 'demo';
    const options = data.todas_contas.filter(c => c.moeda === currency);
    if (account !== 'todas' && !options.some(c => c.id === account)) {
      account = 'todas';
      return refresh();
    }
    $('#account').innerHTML = '<option value="todas">Todas as contas</option>' + options.map(c =>
      `<option value="${esc(c.id)}">${esc(c.nome)}</option>`).join('');
    $('#account').value = account;
    render();
  } catch (error) {
    if (id !== refreshId) return;
    $('#page-content').innerHTML = `<div class="notice" role="alert">${esc(error.message)}</div>`;
  }
}
function changeView(next){view=next;document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);b.setAttribute('aria-current',b.dataset.view===view?'page':'false');});$('#breadcrumb').textContent=labels[view];$('#page-title').textContent=titles[view];$('#page-subtitle').textContent=subtitles[view];history.replaceState(null,'','#'+view);render();window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
function chart(){if(hidden)return '<div class="chart-hidden">Valores ocultos</div>';const series=data.serie;const values=series.map(x=>Number(x.valor));const pad=Math.max(100,(Math.max(...values)-Math.min(...values))*.12);let min=Math.min(...values)-pad,max=Math.max(...values)+pad;if(min===max){min-=100;max+=100;}if(max-min<100){min-=100;max+=100;}const W=640,H=190,L=48,R=12,T=14,B=27;const x=i=>L+i*(W-L-R)/(series.length-1);const y=v=>T+(max-v)*(H-T-B)/(max-min);const point=(r,i)=>`${x(i).toFixed(2)},${y(Number(r.valor)).toFixed(2)}`;const split=series.findIndex(r=>r.previsto);const solid=split<0?series:series.slice(0,split);const start=split<=0?0:split-1;const projected=split<0?[]:series.slice(start);const lines=[0,.33,.66,1].map(p=>{const value=max-(max-min)*p;const yy=y(value);return `<line x1="${L}" x2="${W-R}" y1="${yy}" y2="${yy}" stroke="#2b322b" stroke-dasharray="3 5"/><text x="${L-10}" y="${yy+3}" text-anchor="end" fill="#9fa99c" font-size="8">${new Intl.NumberFormat('pt-BR',{notation:'compact',maximumFractionDigits:1}).format(value)}</text>`;}).join('');const area=`M${x(0)},${H-B} L${series.map(point).join(' L')} L${x(series.length-1)},${H-B} Z`;const ticks=[0,5,10,15,20,25,series.length-1].filter((v,i,a)=>v<series.length&&a.indexOf(v)===i).map(i=>`<text x="${x(i)}" y="${H-5}" text-anchor="middle" fill="#9fa99c" font-size="8">${String(i+1).padStart(2,'0')}</text>`).join('');return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Evolução diária do saldo; linha tracejada indica projeção"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b5ec67" stop-opacity=".55"/><stop offset="1" stop-color="#b5ec67" stop-opacity=".1"/></linearGradient></defs>${lines}<path d="${area}" fill="url(#area)"/>${solid.length?`<polyline points="${solid.map(point).join(' ')}" fill="none" stroke="#b5ec67" stroke-width="2.3" stroke-linejoin="round"/>`:''}${projected.length?`<polyline points="${projected.map((r,i)=>point(r,i+start)).join(' ')}" fill="none" stroke="#78a36a" stroke-width="2.3" stroke-dasharray="5 5" stroke-linejoin="round"/>`:''}${split>0?`<line x1="${x(start)}" x2="${x(start)}" y1="${T}" y2="${H-B}" stroke="#56664d" stroke-dasharray="3 4"/><circle cx="${x(start)}" cy="${y(values[start])}" r="4" fill="#b5ec67" stroke="#171c16" stroke-width="2"/><text x="${x(start)}" y="${T-5}" text-anchor="middle" fill="#c3d5b2" font-size="8">Hoje</text>`:''}${ticks}${series.map((r,i)=>`<circle cx="${x(i)}" cy="${y(Number(r.valor))}" r="8" fill="transparent"><title>${dateLabel(r.data)} · ${money(r.valor)} · ${r.previsto?'Projetado':'Realizado'}</title></circle>`).join('')}</svg>`;}
function hero(){const diff=Number(data.saldo_final)-Number(data.saldo_atual);const past=month<data.hoje.slice(0,7);return `<div class="hero-grid"><section class="balance-card"><div class="card-eyebrow">${icon('trend')}${past?'SALDO NO FIM DO MÊS':'SALDO PROJETADO NO FIM DO MÊS'}</div><div class="balance-amount">${money(data.saldo_final)}</div><span class="projected-pill">${icon(diff>=0?'up':'down')}${money(Math.abs(diff))} ${diff>=0?'acima':'abaixo'} do saldo atual</span><div class="balance-divider"></div><div class="balance-bottom"><div>Saldo disponível hoje<strong>${money(data.saldo_atual)}</strong></div><span>${data.contas.length} ${data.contas.length===1?'conta':'contas'} ${account==='todas'?(data.contas.length===1?'cadastrada':'cadastradas'):'selecionada'}</span></div><div class="balance-footer">${icon('shield')} ${past?'Histórico de movimentos realizados':'Projeção baseada nos seus lançamentos'}</div></section><section class="card chart-card"><div class="card-heading"><div><h2>Seu saldo ao longo do mês</h2><p>O que aconteceu e o que está por vir.</p></div><div class="legend"><span><i></i>Realizado</span><span><i class="dashed"></i>Projetado</span></div></div><div class="chart-area">${chart()}</div><div class="chart-foot">${icon('info')}Previsões não alteram seu saldo disponível.</div></section></div>`;}
function metrics(){return `<div class="metric-grid"><section class="card metric"><div class="metric-label"><span class="metric-icon">${icon('down')}</span>Entradas do mês</div><div class="metric-value">${money(data.entradas)}</div><p>Recebidas · ${money(data.entradas_previstas)} ainda previstas</p></section><section class="card metric out"><div class="metric-label"><span class="metric-icon">${icon('up')}</span>Saídas do mês</div><div class="metric-value">${money(data.saidas)}</div><p>Pagas · ${money(data.saidas_previstas)} ainda previstas</p></section><section class="card metric plan"><div class="metric-label"><span class="metric-icon">${icon('repeat')}</span>Compromissos recorrentes</div><div class="metric-value">${money(sum(data.recorrencias.filter(r=>r.ativa),'saida'))}</div><p>${data.recorrencias.filter(r=>r.ativa).length} recorrências ativas · saídas mensais</p></section></div>`;}
function empty(text){return `<div class="empty"><div>${icon('calendar')}<p>${esc(text)}</p></div></div>`;}
function recurringList(all=false){const rules=all?data.recorrencias:data.recorrencias.slice(0,4);return rules.length?rules.map(r=>`<div class="movement">${itemIcon(r)}<div class="movement-info"><strong>${esc(r.descricao)}</strong><small>Todo dia ${r.dia} · ${esc(r.categoria)}</small></div><div class="movement-amount ${r.tipo==='entrada'?'positive':''}">${r.tipo==='entrada'?'+ ':''}${money(r.valor)}<small>por mês</small></div>${manage('recorrencias',r)}<button class="switch ${r.ativa?'on':''}" role="switch" aria-checked="${r.ativa}" aria-label="${r.ativa?'Pausar':'Ativar'} ${esc(r.descricao)}" data-toggle="${esc(r.id)}"></button></div>`).join(''):empty('Adicione salário, aluguel ou assinaturas para começar a planejar.');}
function upcoming(all=false){let list=data.proximos;if(!all)list=list.filter(t=>t.data>=data.hoje).slice(0,4);return list.length?list.map(t=>`<div class="movement">${itemIcon(t)}<div class="movement-info"><strong>${esc(t.descricao)}</strong><small>${dateLabel(t.data)} · ${esc(t.categoria)}</small></div><div class="movement-amount ${t.tipo==='entrada'?'positive':''}">${t.tipo==='entrada'?'+':'−'} ${money(t.valor)}<small>${t.data<data.hoje?'Em atraso':t.data===data.hoje?'Hoje':'Previsto'}</small></div><button class="settle-button" data-settle="${esc(t.id)}">${t.tipo==='entrada'?'Receber':'Pagar'}</button></div>`).join(''):empty('Nenhum compromisso pendente neste período. Tudo em perspectiva.');}
function donut(){if(!data.categorias.length)return empty('Os gastos realizados aparecerão aqui, separados por categoria.');const total=sum(data.categorias);let acc=0;const segments=data.categorias.map((c,i)=>{let start=acc;acc+=Number(c.valor)/total*100;return `${palette[i%palette.length]} ${start}% ${acc}%`;}).join(',');return `<div class="donut-layout"><div class="donut" style="background:conic-gradient(${hidden?'#e3ece5 0% 100%':segments})" role="img" aria-label="Gastos realizados por categoria"><div class="donut-center"><small>Total do mês</small><strong>${money(total)}</strong></div></div><div class="category-list">${data.categorias.slice(0,6).map((c,i)=>`<div class="category-row"><i style="background:${palette[i]}"></i><span>${esc(c.categoria)}</span><strong>${money(c.valor)}</strong><small>${hidden?'••':Math.round(Number(c.valor)/total*100)+'%'}</small></div>`).join('')}</div></div>`;}
function table(all=false){let rows=all?data.lancamentos:data.lancamentos.filter(t=>t.status==='realizado').slice(0,5);return `<section class="card table-card"><div class="card-heading"><div><span class="card-overline">ATIVIDADE DA CONTA</span><h2>${all?'Seus lançamentos':'Últimos movimentos'}</h2></div>${all?'<input class="search" id="search" placeholder="Buscar lançamento…" aria-label="Buscar lançamento">':'<button class="text-button" data-view="lancamentos">Ver todos '+icon('arrow-right')+'</button>'}</div>${rows.length?`<div class="table-scroll"><table><thead><tr><th>DESCRIÇÃO</th><th>CATEGORIA</th><th>DATA</th><th>STATUS</th><th>VALOR</th><th></th></tr></thead><tbody>${rows.map(t=>`<tr data-search="${esc(t.descricao.toLowerCase())}"><td><span class="table-name">${itemIcon(t)}${esc(t.descricao)}</span></td><td><small>${esc(t.categoria)}</small></td><td><small>${dateLabel(t.data)}</small></td><td>${badge(t)}</td><td class="${t.tipo==='entrada'?'positive':''}">${t.tipo==='entrada'?'+':'−'} ${money(t.valor)}</td><td>${manage('lancamentos',t)}${t.status==='previsto'?`<button class="settle-button" data-settle="${esc(t.id)}">${t.tipo==='entrada'?'Receber':'Pagar'}</button>`:'<span class="quiet">'+icon('check')+'</span>'}</td></tr>`).join('')}</tbody></table></div>`:empty('Nenhum lançamento neste mês. Adicione um movimento para começar.')}</section>`;}
function render(){if(!data)return;let html='';const warning=data.atrasados?`<div class="notice">${data.atrasados} ${data.atrasados===1?'compromisso vencido não realizado':'compromissos vencidos não realizados'}. A projeção não presume pagamento de pendências passadas.</div>`:'';if(view==='visao'){html=hero()+metrics()+warning+`<div class="content-grid"><section class="card section-card"><div class="card-heading"><div><span class="card-overline">DE OLHO NO AMANHÃ</span><h2>Próximos compromissos</h2></div><button class="text-button" data-view="planejamento">Ver planejamento ${icon('arrow-right')}</button></div><div class="upcoming-list">${upcoming()}</div></section><section class="card section-card"><div class="card-heading"><div><span class="card-overline">SEU MÊS, ORGANIZADO</span><h2>No piloto automático.</h2></div><button class="icon-button" data-action="recorrencia" aria-label="Adicionar recorrência">${icon('plus')}</button></div><div class="upcoming-list">${recurringList()}</div><div class="recurring-banner"><div>Menos surpresas no fim do mês.<strong>Suas recorrências já estão na projeção.</strong></div>${icon('repeat')}</div></section></div><div class="content-grid"><section class="card section-card"><div class="card-heading"><div><span class="card-overline">DISTRIBUIÇÃO DOS GASTOS</span><h2>Para onde foi seu dinheiro</h2></div><span class="quiet">Realizado</span></div>${donut()}</section><section class="card section-card"><div class="card-heading"><div><span class="card-overline">SEU PONTO DE PARTIDA</span><h2>Suas contas</h2></div><button class="text-button" data-view="contas">Gerenciar ${icon('arrow-right')}</button></div><div class="upcoming-list">${data.contas.map(c=>`<div class="movement"><span class="item-icon">${icon('wallet')}</span><div class="movement-info"><strong>${esc(c.nome)}</strong><small>Saldo realizado · ${c.moeda}</small></div><div class="movement-amount">${money(c.saldo,c.moeda)}</div></div>`).join('')||empty('Nenhuma conta nesta moeda.')}</div><div class="info-panel">${icon('shield')}<div>Clareza em cada número.<p>Entradas e saídas previstas só afetam o saldo disponível quando você confirma a realização.</p></div></div></section></div>`+table();}
else if(view==='lancamentos'){html=metrics()+warning+table(true)+pending();}
else if(view==='planejamento'){html=hero()+warning+`<div class="section-actions"><button class="button primary" data-action="recorrencia">${icon('plus')}Nova recorrência</button><button class="button" data-action="novo">${icon('calendar')}Adicionar previsão</button></div><div class="content-grid"><section class="card section-card"><div class="card-heading"><h2>Recorrências mensais</h2><span class="quiet">${data.recorrencias.length} cadastradas</span></div>${recurringList(true)}<p class="pause-note">Pausar retira as ocorrências não realizadas da projeção. O histórico realizado permanece. Dias 29–31 usam o último dia em meses mais curtos.</p></section><section class="card section-card"><div class="card-heading"><h2>Agenda do mês</h2><span class="quiet">Previstos e pendentes</span></div>${upcoming(true)}</section></div>`+pending();}
else if(view==='contas'){html=`<div class="section-actions"><button class="button primary" data-action="conta">${icon('plus')}Adicionar conta</button></div><div class="account-grid">${data.contas.map(c=>`<section class="card account-card"><span class="item-icon">${icon('wallet')}</span><h3>${esc(c.nome)}</h3><p>Conta pessoal · ${c.moeda}</p><div class="metric-value">${money(c.saldo,c.moeda)}</div><p>Saldo realizado hoje</p><div class="balance-divider"></div><p>Saldo inicial de ${money(c.saldo_inicial,c.moeda)} em ${dateLabel(c.data_inicial)}</p>${manage('contas',c)}</section>`).join('')||empty('Nenhuma conta nesta moeda.')}</div><div class="info-panel">${icon('info')}<div>Uma moeda por conta.<p>Os saldos de moedas diferentes nunca são somados. Use o filtro de moeda para alternar sua visão.</p></div></div>`;}
else{html=`<section class="card section-card"><div class="card-heading"><div><h2>Importar uma fatura</h2><p>O PDF é o ponto de partida. A confirmação é sua.</p></div><span class="status-chip">${data.pdf_ia ? 'PDF ou digitalização' : 'PDF com texto'}</span></div><div class="upload-zone"><span>${icon('scan')}</span><h2>Seus documentos também fazem parte.</h2><p>Extraímos os dados para você conferir e criar um lançamento previsto.</p><button class="button primary" data-action="importar">${icon('plus')}Selecionar PDF</button><p class="quiet">Até 10 MB · o lançamento é criado como previsto</p></div></section><section class="card section-card" style="margin-top:20px"><div class="card-heading"><h2>Documentos importados</h2><span class="quiet">${data.documentos.length} documentos</span></div>${data.documentos.length?data.documentos.map(d=>`<div class="document-row"><span class="item-icon">${icon('file')}</span><div><strong>${esc(d.descricao)}</strong><p>${esc(d.nome)} · ${dateLabel(d.criado_em)}</p></div><a href="/api/documentos/${esc(d.id)}">${icon('download')} PDF</a></div>`).join(''):empty('Os PDFs confirmados ficam aqui, vinculados aos seus lançamentos.')}</section>`;}
$('#page-content').innerHTML=html;}

function field(name, label, type='text', value='', extra='') {
  return `<label class="field ${extra.includes('data-full') ? 'full' : ''}">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
}

function select(name, label, options, value, extra='') {
  const choices = options.map(option => {
    const [val, text] = Array.isArray(option) ? option : [option, option];
    return `<option value="${esc(val)}" ${val === value ? 'selected' : ''}>${esc(text)}</option>`;
  }).join('');
  return `<label class="field">${label}<span class="field-select"><select name="${name}" ${extra}>${choices}</select></span></label>`;
}

function accounts(value) {
  const options = data.todas_contas.map(c => [c.id, c.nome + ' · ' + c.moeda]);
  if (!options.length) options.push(['', 'Nenhuma conta disponível']);
  return select('conta_id', 'Conta', options, value ?? data.contas[0]?.id, 'required');
}

function moneyField(name, label, value, {required=false, doc=false, negative=false, positive=false}={}) {
  return `<div class="field money-field">
    <label class="money-label" for="valor-${name}">${label}<span class="money-currency" data-money-currency hidden></span></label>
    <div class="money-control">
      <input id="valor-${name}" name="${name}" type="text" value="${esc(value)}" inputmode="numeric" placeholder="0,00"
        data-money ${doc ? 'data-document-money readonly' : ''} ${negative ? 'data-negative' : ''} ${positive ? 'data-positive' : ''}
        aria-describedby="money-${name}${doc ? ' instrucao-valores-fatura' : ' instrucao-' + name}" ${required ? 'required' : ''}>
      ${negative ? '<button type="button" class="money-sign" aria-label="Saldo negativo" aria-pressed="false">±</button>' : ''}
    </div>
    ${doc ? '' : `<small class="money-hint" id="instrucao-${name}">Os dois últimos dígitos são os centavos.</small>`}
    <span class="field-error" id="money-${name}" hidden></span>
  </div>`;
}

function watchMoney(form) {
  const inputs = Array.from(form.querySelectorAll('[data-money]'));

  const validators = inputs.map(input => {
    const field = input.closest('.money-field');
    const error = field.querySelector('.field-error');
    const sign = field.querySelector('.money-sign');
    const isDocument = input.hasAttribute('data-document-money');
    const options = {
      negativo: Boolean(sign),
      positivo: input.hasAttribute('data-positive'),
      limite: isDocument ? 16 : 12,
    };
    const source = input.value;
    let format = isDocument ? form.elements.formato.value : 'pt-BR';
    let changed = false;
    let pending;

    function validate(show = false, formatValue = false) {
      let message = '';
      try {
        if (format && formatValue) {
          const canonical = valores.normalizar(input.value, format, {...options, positivo:false});
          input.value = valores.formatar(canonical, format);
        }
        if (format) valores.normalizar(input.value, format, options);
      } catch (failure) {
        message = failure.message;
      }
      input.setCustomValidity(message);
      if (show && message) input.setAttribute('aria-invalid', 'true');
      else input.removeAttribute('aria-invalid');
      error.textContent = message;
      error.hidden = !(show && message);
      sign?.setAttribute('aria-pressed', String(input.value.startsWith('-')));
    }

    function hasMask() {
      if (!input.value || input.value === '-') return true;
      try {
        const canonical = valores.normalizar(input.value, format, {...options, positivo:false, limite:Infinity});
        return input.value === valores.formatar(canonical, format);
      } catch {
        return false;
      }
    }

    function write(result, show = input.hasAttribute('aria-invalid')) {
      input.value = result.texto;
      input.setSelectionRange(result.cursor, result.cursor);
      changed = true;
      validate(show);
    }

    input.addEventListener('beforeinput', event => {
      pending = undefined;
      if (!format || event.isComposing) return;
      const {selectionStart:inicio, selectionEnd:fim} = input;
      const whole = inicio === 0 && fim === input.value.length;
      if (!whole && !hasMask()) return;
      const deletion = {deleteContentBackward:'tras', deleteContentForward:'frente', deleteByCut:'selecao'};
      const apagar = deletion[event.inputType];
      const tecla = event.inputType === 'insertText' ? event.data : '';
      if (!tecla && !apagar) return;
      if (tecla && !/^\d+$/.test(tecla) && !(options.negativo && /^[-−]$/.test(tecla))) {
        if (event.cancelable) event.preventDefault();
        return;
      }
      const result = valores.editarCentavos(input.value, {inicio, fim, formato:format, tecla, apagar, negativo:options.negativo});
      if (event.cancelable) {
        event.preventDefault();
        write(result);
      } else {
        pending = result;
      }
    });
    input.addEventListener('paste', event => {
      const pasted = event.clipboardData?.getData('text');
      if (!format || !pasted) return;
      const {selectionStart:inicio, selectionEnd:fim} = input;
      if (inicio !== 0 || fim !== input.value.length) {
        if (/^\d+$/.test(pasted) && hasMask()) {
          event.preventDefault();
          write(valores.editarCentavos(input.value, {inicio, fim, formato:format, tecla:pasted, negativo:options.negativo}));
        }
        return;
      }
      event.preventDefault();
      let text = pasted.trim();
      try {
        text = valores.formatar(valores.normalizar(text, format, {...options, positivo:false}), format);
      } catch {
        // Deixa o valor colado visível para correção.
      }
      write({texto:text, cursor:text.length}, true);
    });
    input.addEventListener('input', event => {
      if (event.isComposing) return;
      changed = true;
      if (pending) {
        write(pending);
        pending = undefined;
      } else {
        validate(input.hasAttribute('aria-invalid'), true);
      }
    });
    input.addEventListener('blur', () => validate(true));
    input.addEventListener('invalid', () => validate(true));

    sign?.addEventListener('click', () => {
      input.focus();
      const text = valores.alternarSinal(input.value);
      write({texto:text, cursor:text.length});
    });

    if (isDocument) {
      form.elements.formato.addEventListener('change', () => {
        const selected = form.elements.formato.value;
        input.readOnly = !selected;
        if (!selected) return;
        if (!changed) {
          input.value = source;
        } else if (format && format !== selected) {
          try {
            const canonical = valores.normalizar(input.value, format, {...options, positivo:false});
            input.value = valores.formatar(canonical, selected);
          } catch {
            // Preserva o texto para correção no formato escolhido.
          }
        }
        format = selected;
        input.placeholder = format === 'en-US' ? '0.00' : '0,00';
        validate(true, true);
      });
    }
    validate();
    return () => validate(true);
  });
  return () => validators.forEach(validate => validate());
}

function actions(label) {
  return `<div class="form-error" role="alert" tabindex="-1"></div>
    <div class="form-actions"><button type="button" class="button" data-close>Cancelar</button>
    <button type="submit" class="button primary"><span>${label}</span>${icon('arrow-right')}</button></div>`;
}

function openDialog(title, body, wide=false) {
  $('#dialog-title').textContent = title;
  const dialog = $('#editor');
  dialog.classList.toggle('wide', wide);
  const content = $('#dialog-body');
  content.innerHTML = body;
  const intended = content.querySelector('[autofocus]') || content.querySelector('[data-close]');
  intended?.setAttribute('autofocus', '');
  if (!dialog.open) dialog.showModal();
  else (intended || $('#close-dialog')).focus();
  dialog.scrollTop = 0;
}

function closeDialog() {
  $('#editor').close();
}

function bindForm(form, {send, success, busy='Salvando…', prepare, after}) {
  const button = form.querySelector('[type="submit"]');
  const label = button.querySelector('span');
  const original = label.textContent;
  const error = form.querySelector('.form-error');
  form.addEventListener('input', () => {
    error.classList.remove('show');
    error.textContent = '';
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    prepare?.();
    if (!form.reportValidity()) return;
    button.disabled = true;
    label.textContent = busy;
    form.setAttribute('aria-busy', 'true');
    error.classList.remove('show');
    try {
      const result = await send(Object.fromEntries(new FormData(form)));
      const active = form.isConnected && $('#editor').open;
      if (after) {
        if (active) after(result);
      } else {
        if (active) closeDialog();
        await refresh();
        if (active && document.activeElement === document.body) $('#conteudo').focus({preventScroll:true});
        notify(success);
      }
    } catch (failure) {
      if (form.isConnected && $('#editor').open) {
        error.textContent = failure.message;
        error.classList.add('show');
        error.focus();
      } else {
        notify(failure.message);
      }
    } finally {
      form.removeAttribute('aria-busy');
      button.disabled = false;
      label.textContent = original;
    }
  });
}

function registerAccountDate(form, dateInput) {
  const update = () => {
    const selected = data.todas_contas.find(c => c.id === form.elements.conta_id.value);
    dateInput.min = selected?.data_inicial ?? '';
    const currencyLabel = form.querySelector('[data-money-currency]');
    if (currencyLabel && !form.elements.formato) {
      currencyLabel.textContent = selected?.moeda ?? '';
      currencyLabel.hidden = !selected;
    }
  };
  form.elements.conta_id.addEventListener('change', update);
  update();
  return update;
}

function newMovement(recurring=false, item=null) {
  if (!data.todas_contas.length) {
    newAccount();
    return;
  }
  const title = recurring ? (item ? 'Editar recorrência' : 'Nova recorrência') : (item ? 'Editar lançamento' : 'Novo lançamento');
  const action = item ? 'Salvar alterações' : recurring ? 'Criar recorrência' : 'Salvar lançamento';
  const help = recurring
    ? (item ? 'As ocorrências previstas serão atualizadas. O histórico confirmado será preservado.' : 'A recorrência entra no planejamento todos os meses.')
    : 'Movimentos previstos entram na projeção. Movimentos realizados entram no saldo.';
  const period = recurring
    ? field('dia', 'Dia do mês', 'number', item?.dia ?? 5, 'required min="1" max="31" step="1" inputmode="numeric"') +
      field('inicio', 'Começar a partir de', 'date', item?.inicio ?? data.hoje, 'required')
    : field('data', 'Data', 'date', item?.data ?? data.hoje, 'required') +
      select('status', 'Situação', [['previsto','Previsto'],['realizado','Realizado']], item?.status ?? 'previsto');
  openDialog(title, `<form id="movement-form"><div class="form-grid">
    ${field('descricao', 'Descrição', 'text', item?.descricao ?? '', 'required maxlength="150" placeholder="Ex.: Aluguel" autofocus data-full')}
    ${select('tipo','Tipo',[['saida','Saída'],['entrada','Entrada']],item?.tipo ?? 'saida')}
    ${moneyField('valor', 'Valor', valores.formatar(item?.valor), {required:true, positive:true})}
    ${accounts(item?.conta_id)}
    ${select('categoria','Categoria',data.categorias_disponiveis,item?.categoria ?? 'Outros')}
    ${period}</div><p class="form-help">${help}</p>${actions(action)}</form>`);
  const form = $('#movement-form');
  const dateInput = form.elements[recurring ? 'inicio' : 'data'];
  registerAccountDate(form, dateInput);
  if (!recurring) {
    const update = () => { dateInput.max = form.elements.status.value === 'realizado' ? data.hoje : ''; };
    form.elements.status.addEventListener('change', update);
    update();
  }
  bindForm(form, {
    prepare: watchMoney(form),
    send: payload => {
      payload.valor = valores.normalizar(payload.valor, 'pt-BR', {positivo:true});
      const route = recurring ? '/api/recorrencias' : '/api/lancamentos';
      return api(route + (item ? '/' + encodeURIComponent(item.id) : ''), {
        method: item ? 'PUT' : 'POST', body: JSON.stringify(payload),
      });
    },
    success: item ? 'Alterações salvas.' : recurring ? 'Recorrência criada. Projeção atualizada.' : 'Lançamento salvo.',
  });
}

function newAccount(item=null) {
  openDialog(item ? 'Editar conta' : 'Nova conta', `<form id="account-form"><div class="form-grid">
    ${field('nome', 'Nome da conta', 'text', item?.nome ?? '', 'required maxlength="80" placeholder="Ex.: Conta principal" autofocus data-full')}
    ${select('moeda', 'Moeda', ['BRL','USD','EUR'], item?.moeda ?? currency, item ? 'disabled' : '')}
    ${moneyField('saldo_inicial', 'Saldo inicial', valores.formatar(item?.saldo_inicial), {negative:true, required:Boolean(item)})}
    ${field('data_inicial', 'Data do saldo inicial', 'date', item?.data_inicial ?? data.hoje, `required max="${esc(data.hoje)}" data-full`)}
    </div><p class="form-help">${item ? 'A moeda é definida ao criar a conta.' : 'Se deixar o saldo em branco, a conta começa com zero.'}</p>
    ${actions(item ? 'Salvar alterações' : 'Adicionar conta')}</form>`);
  const form = $('#account-form');
  const badge = form.querySelector('[data-money-currency]');
  const update = () => { badge.textContent = form.elements.moeda.value; };
  badge.hidden = false;
  form.elements.moeda.addEventListener('change', update);
  update();
  bindForm(form, {
    prepare: watchMoney(form),
    send: payload => {
      payload.saldo_inicial = valores.normalizar(payload.saldo_inicial, 'pt-BR', {negativo:true}) || '0.00';
      if (item) payload.moeda = item.moeda;
      return api('/api/contas' + (item ? '/' + encodeURIComponent(item.id) : ''), {
        method: item ? 'PUT' : 'POST', body: JSON.stringify(payload),
      });
    },
    success: item ? 'Conta atualizada.' : 'Conta adicionada.',
  });
}

function settle(id) {
  const item = [...data.lancamentos, ...data.proximos, ...data.pendencias].find(t => t.id === id);
  if (!item) return;
  const receipt = item.tipo === 'entrada';
  openDialog(receipt ? 'Confirmar recebimento' : 'Confirmar pagamento', `<form id="settle-form">
    <div class="movement">${itemIcon(item)}<div class="movement-info"><strong>${esc(item.descricao)}</strong>
    <small>Previsto para ${dateLabel(item.data)}</small></div><div class="movement-amount">${money(item.valor)}</div></div>
    <p class="form-help">O lançamento será realizado hoje (${dateLabel(data.hoje)}) e substituirá a previsão.</p>
    ${actions(receipt ? 'Confirmar recebimento' : 'Confirmar pagamento')}</form>`);
  bindForm($('#settle-form'), {
    send: () => api('/api/realizar', {method:'POST', body:JSON.stringify({id})}),
    success: 'Movimento realizado. Saldo atualizado.',
  });
}

function importPDF() {
  const methods = data.pdf_ia
    ? select('metodo', 'Método de extração', [['texto','Texto do PDF'], ['ia','IA local']], 'texto') : '';
  openDialog('Importar fatura', `<form id="upload-form"><label class="field full">Arquivo PDF
    <input type="file" name="arquivo" accept="application/pdf,.pdf" aria-describedby="pdf-info" required autofocus></label>
    ${methods}
    <p class="form-help" id="pdf-info">Escolha um PDF de até 10 MB. ${data.pdf_ia ? 'A IA local lê até cinco páginas, inclusive digitalizadas.' : 'Você poderá revisar os dados extraídos.'}</p>
    ${actions('Extrair dados')}</form>`);
  const form = $('#upload-form');
  form.elements.arquivo.addEventListener('change', event => {
    const input = event.currentTarget;
    input.setCustomValidity(input.files[0]?.size > 10 * 1024 * 1024 ? 'Selecione um PDF de até 10 MB.' : '');
    input.reportValidity();
  });
  bindForm(form, {
    busy: 'Lendo PDF…',
    send: async ({arquivo, metodo}) => {
      const body = new FormData();
      body.append('arquivo', arquivo);
      if (metodo) body.append('metodo', metodo);
      return {arquivo, extraction:await api('/api/pdf/analisar', {method:'POST', body})};
    },
    after: ({arquivo, extraction}) => reviewPDF(arquivo, extraction),
  });
}

function reviewPDF(arquivo, extraction) {
  const labels = {fornecedor:'Fornecedor', numero_fatura:'Número da fatura', data_emissao:'Emissão',
    data_vencimento:'Vencimento', moeda:'Moeda', total:'Total', subtotal:'Subtotal', desconto:'Desconto',
    tributos:'Tributos adicionais', identificador_fiscal:'Identificador fiscal', pedido_compra:'Pedido de compra'};
  const mandatory = ['fornecedor', 'numero_fatura', 'data_emissao', 'moeda', 'total'];
  const amounts = ['total', 'subtotal', 'desconto', 'tributos'];
  const evidence = Object.entries(extraction.candidatos).filter(([, list]) => list.length).map(([name,list]) =>
    `${labels[name]}: ${list.map(candidate => candidate.valor + ' (pág. ' + candidate.pagina + ')').join(' / ')}`);
  const fields = Object.entries(labels).map(([name,label]) => {
    const required = mandatory.includes(name);
    const fieldLabel = required ? label : label + ' (opcional)';
    const value = extraction.valores[name] ?? '';
    if (amounts.includes(name)) return moneyField(name, fieldLabel, value, {doc:true, required, positive:name === 'total'});
    if (name === 'moeda') {
      return select(name, label, [['','Escolha a moeda'], 'BRL', 'USD', 'EUR'], String(value).toUpperCase(), 'required');
    }
    const detail = name.startsWith('data_') ? 'placeholder="AAAA-MM-DD"' : 'maxlength="255"';
    return field(name, fieldLabel, 'text', value, `${detail} ${required ? 'required' : ''}`);
  }).join('');
  openDialog('Revisar fatura', `<form id="pdf-form">
    <div class="evidence" tabindex="0" aria-label="Dados encontrados no documento">${esc([arquivo.name, ...evidence, ...extraction.avisos].join('\n'))}</div>
    <div class="form-grid">
    ${select('formato','Formato dos valores',[['','Escolha o formato'],['pt-BR','1.250,90 (pt-BR)'],['en-US','1,250.90 (en-US)']],'','required autofocus')}
    ${select('ordem','Datas com barras',[['','Escolha a ordem'],['DMY','Dia / mês / ano'],['MDY','Mês / dia / ano']],'','required')}
    ${fields}${accounts()}${select('categoria','Categoria',data.categorias_disponiveis,'Outros')}
    ${select('tipo','Tipo de movimento',[['saida','Saída prevista'],['entrada','Entrada prevista']],'saida')}
    ${field('data_prevista','Data prevista para o movimento','date','','required')}</div>
    <p class="form-help" id="instrucao-valores-fatura">Escolha o formato para editar os valores. Os dois últimos dígitos são os centavos.</p>
    <p class="form-help">Escolha uma conta na moeda da fatura e confira o vencimento antes de informar a data prevista.</p>
    <label class="check-field"><input name="confirmado" type="checkbox" required>Conferi o documento e os campos acima.</label>
    <label class="check-field"><input name="aceitar_avisos" type="checkbox">Revisei eventuais diferenças entre subtotal, descontos, tributos e total.</label>
    <label class="check-field"><input name="aceitar_duplicidade" type="checkbox">Se houver mesmo fornecedor e número, conferi a possível duplicidade e desejo manter ambos.</label>
    ${actions('Criar lançamento previsto')}</form>`, true);
  const form = $('#pdf-form');
  const accountSelect = form.elements.conta_id;
  const updateDate = registerAccountDate(form, form.elements.data_prevista);
  function updateAccounts() {
    const list = data.todas_contas.filter(c => c.moeda === form.elements.moeda.value);
    const previous = accountSelect.value;
    if (!list.length) {
      accountSelect.replaceChildren(new Option(form.elements.moeda.value ? 'Nenhuma conta nessa moeda' : 'Escolha a moeda da fatura', ''));
    } else {
      accountSelect.replaceChildren(...list.map(c => new Option(c.nome + ' · ' + c.moeda, c.id)));
      if (list.some(c => c.id === previous)) accountSelect.value = previous;
    }
    updateDate();
  }
  form.elements.moeda.addEventListener('change', updateAccounts);
  updateAccounts();
  bindForm(form, {
    prepare: watchMoney(form),
    send: values => {
      const campos = Object.fromEntries(Object.keys(labels).map(name => [name, values[name]]));
      const payload = {...values, campos, confirmado:!!values.confirmado, aceitar_avisos:!!values.aceitar_avisos,
        aceitar_duplicidade:!!values.aceitar_duplicidade};
      if (extraction.analise_ia) payload.analise_ia = extraction.analise_ia;
      const body = new FormData();
      body.append('arquivo', arquivo);
      body.append('revisao', JSON.stringify(payload));
      return api('/api/pdf/confirmar', {method:'POST', body});
    },
    success: 'Fatura conferida. Lançamento previsto criado.',
  });
}

document.addEventListener('click',async e=>{const b=e.target.closest('button,a.brand');if(!b)return;if(b.classList.contains('brand')){e.preventDefault();changeView('visao');return;}if(b.dataset.view){changeView(b.dataset.view);return;}if(b.hasAttribute('data-close'))closeDialog();if(b.dataset.action){if(!data){notify('Aguarde o carregamento dos dados.');return;}({novo:()=>newMovement(),recorrencia:()=>newMovement(true),conta:()=>newAccount(),espaco:workspace, lixeira:trash,importar:importPDF})[b.dataset.action]?.();}if(b.dataset.toggle){b.disabled=true;try{await api(`/api/recorrencias/${encodeURIComponent(b.dataset.toggle)}/alternar`,{method:'POST',body:'{}'});await refresh();notify('Recorrência atualizada. Projeção recalculada.');}catch(err){notify(err.message);}finally{b.disabled=false;}}if(b.dataset.settle)settle(b.dataset.settle);if(b.dataset.edit){const k=b.dataset.kind;const list=k==='contas'?data.todas_contas:k==='recorrencias'?data.recorrencias:[...data.lancamentos,...data.pendencias];const item=list.find(i=>i.id===b.dataset.edit);if(item){if(k==='contas')newAccount(item);else newMovement(k==='recorrencias',item);}}if(b.dataset.remove)removeItem(b.dataset.kind,b.dataset.remove);if(b.dataset.restore)restoreItem(b);});
$('#close-dialog').addEventListener('click',closeDialog);
$('#editor').addEventListener('click',e=>{if(e.target===$('#editor')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDialog();}});
$('#privacy').addEventListener('click',()=>{hidden=!hidden;$('#privacy').setAttribute('aria-pressed',String(hidden));$('#privacy').setAttribute('aria-label',hidden?'Mostrar valores':'Ocultar valores');$('#privacy').innerHTML=icon(hidden?'hidden':'eye');render();});
function stepMonth(step){const d=new Date(month+'-01T12:00:00');d.setMonth(d.getMonth()+step);month=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;refresh();}
$('#prev-month').onclick=()=>stepMonth(-1);$('#next-month').onclick=()=>stepMonth(1);
$('#month').onchange=e=>{if(e.target.value){month=e.target.value;refresh();}};
$('#today').onclick=()=>{if(!data)return;month=data.hoje.slice(0,7);refresh();};
$('#account').onchange=e=>{account=e.target.value;refresh();};
$('#currency').onchange=e=>{currency=e.target.value;account='todas';refresh();};
document.addEventListener('input',e=>{if(e.target.id==='search'){const query=e.target.value.toLowerCase();document.querySelectorAll('[data-search]').forEach(row=>row.hidden=!row.dataset.search.includes(query));}});
const initialView = location.hash.slice(1);
if (Object.hasOwn(labels, initialView) && (!privatePage || initialView !== 'documentos')) {
  view = initialView;
  $('#breadcrumb').textContent = labels[view];
  $('#page-title').textContent = titles[view];
  $('#page-subtitle').textContent = subtitles[view];
}
document.querySelectorAll('.nav-item').forEach(button => {
  const current = button.dataset.view === view;
  button.classList.toggle('active', current);
  button.setAttribute('aria-current', current ? 'page' : 'false');
});
refresh();

function manage(kind,item){return `<span class="manage-actions"><button class="text-button" data-kind="${kind}" data-edit="${esc(item.id)}" aria-label="Editar ${esc(item.descricao||item.nome)}">Editar</button><button class="text-button" data-kind="${kind}" data-remove="${esc(item.id)}" aria-label="Excluir ${esc(item.descricao||item.nome)}">Excluir</button></span>`;}
function pending(){const items=data.pendencias.filter(t=>!data.proximos.some(p=>p.id===t.id));return items.length?`<section class="card section-card" style="margin-top:20px"><h2>Pendências de outros meses</h2>${items.map(t=>`<div class="movement"><div class="movement-info"><strong>${esc(t.descricao)}</strong><small>${esc(t.data)}</small></div><span>${money(t.valor)}</span>${manage('lancamentos',t)}<button class="settle-button" data-settle="${esc(t.id)}">Confirmar</button></div>`).join('')}</section>`:'';}
function removeItem(kind, id) {
  openDialog('Mover para a lixeira?', `<form id="remove-form"><p class="form-help">Você poderá restaurar o registro pela lixeira.</p>${actions('Mover para a lixeira')}</form>`);
  bindForm($('#remove-form'), {
    send: () => api(`/api/${kind}/${encodeURIComponent(id)}/lixeira`, {method:'POST', body:'{}'}),
    success: 'Registro movido para a lixeira.',
  });
}
async function restoreItem(button) {
  const {kind, restore:id} = button.dataset;
  button.disabled = true;
  button.textContent = 'Restaurando…';
  try {
    await api(`/api/${kind}/${encodeURIComponent(id)}/lixeira`, {
      method:'POST', body:JSON.stringify({restaurar:true}),
    });
    await refresh();
    if (button.isConnected && $('#editor').open) trash();
    notify('Registro restaurado.');
  } catch (error) {
    notify(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Restaurar';
  }
}
function trash(){openDialog('Lixeira',`<p class="form-help">Restaure uma conta antes dos movimentos vinculados a ela.</p>${data.lixeira.length?data.lixeira.map(i=>`<div class="movement"><div class="movement-info"><strong>${esc(i.descricao||i.nome)}</strong><small>${esc(i.colecao)}</small></div><button class="button" data-kind="${i.colecao}" data-restore="${esc(i.id)}">Restaurar</button></div>`).join(''):empty('Sua lixeira está vazia.')}`);}
function workspace() {
  const actions = '<a class="button" href="/api/backup">Baixar cópia dos dados</a><button class="button" data-action="lixeira">Lixeira</button>';
  if (data.modo === 'online') {
    openDialog('Meu espaço', `<p class="form-help">${esc(data.perfil.email)}</p><div class="section-actions">${actions}
      <button class="button" id="sign-out">Sair da conta</button></div>`);
    $('#sign-out').onclick = async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        const result = await api('/api/auth/sair', {method: 'POST', body: '{}'});
        data = null;
        $('#page-content').replaceChildren();
        location.replace(result.destino);
      } catch (error) {
        notify(error.message);
        button.disabled = false;
      }
    };
    return;
  }
  const modos = data.modo === 'mysql' ? '' : '<button class="button" id="use-demo">Demonstração</button><button class="button primary" id="use-local">Meus dados</button>';
  openDialog('Seu espaço financeiro', `<p class="form-help">A demonstração e seus dados pessoais são separados. Seus dados pessoais começam com uma conta vazia e ficam salvos neste computador.</p><div class="section-actions">${modos}${actions}</div>`);
  for (const mode of ['demo', 'local']) {
    const button = $('#use-' + mode);
    if (button) button.onclick = async () => {
      button.disabled = true;
      try {
        await api('/api/espaco', {method: 'POST', body: JSON.stringify({modo: mode})});
        account = 'todas';
        closeDialog();
        await refresh();
        notify(mode === 'local' ? 'Seu espaço pessoal está pronto.' : 'Demonstração aberta.');
      } catch (error) {
        notify(error.message);
      } finally {
        button.disabled = false;
      }
    };
  }
}
