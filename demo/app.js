const $ = selector => document.querySelector(selector);
const format = value => Number(value || 0).toLocaleString();
let previousLiveNodes = new Set();
let previousMtimes = {};
let lastGraphSignature = '';
let lastUsageTokens = 0;

function setLoading(loading) {
  document.body.classList.toggle('loading', loading);
  $('#analyze-button').disabled = loading;
  $('#sample-button').disabled = loading;
  $('#analyze-button span').textContent = loading ? 'Tracing intent…' : 'Analyze next change';
}

function showError(message = '') {
  $('#error').textContent = message;
  $('#error').classList.toggle('visible', Boolean(message));
}

function render(data) {
  showError();
  const memory = data.memory || {}, packet = data.change_packet || {}, cost = data.token_cost || {};
  const capability = packet.capability || {}, reads = new Set(packet.recommended_reads || []);
  $('#request').value = data.request || $('#request').value;
  $('#confidence').textContent = `${Math.round((memory.confidence || 0) * 100)}%`;
  $('#decision').textContent = memory.decision_excerpt || 'No prior architectural decision matched this request.';
  $('#citations').replaceChildren(...(memory.citations || []).map(citation => {
    const el=document.createElement('span'); el.className='citation'; el.textContent=`${citation.type}:${citation.id.slice(0,18)}…`; return el;
  }));
  const exists=capability.status==='likely_exists';
  $('#capability-badge').textContent=exists?'Already exists':'Change needed';
  $('#evidence').replaceChildren(...(capability.evidence || []).slice(0,3).map(item => {
    const el=document.createElement('div'); el.className='evidence-item';
    const name=document.createElement('b'); name.textContent=item.module;
    const terms=document.createElement('span'); terms.textContent=item.matched_symbols.join(' + ');
    el.append(name,terms); return el;
  }));
  $('#target-list').replaceChildren(...(packet.likely_change_targets || []).map((item,index) => {
    const el=document.createElement('div'); el.className='target-item';
    const rank=document.createElement('span'); rank.className='target-rank'; rank.textContent=String(index+1).padStart(2,'0');
    const info=document.createElement('div'), name=document.createElement('b'), terms=document.createElement('small');
    name.textContent=item.module; terms.textContent=item.matched_terms.join(' · '); info.append(name,terms);
    const flag=document.createElement('span'); flag.className='read-flag'; flag.textContent=reads.has(item.module)?'read first':'ranked';
    el.append(rank,info,flag); return el;
  }));
  $('#expansion-policy').textContent=packet.expansion_policy || '';
  $('#hero-saving').textContent=`${Number(cost.difference_percent || 0).toFixed(1)}%`;
  $('#hero-token-caption').textContent=`${format(cost.difference)} tokens never entered the context window`;
  $('#full-tokens').textContent=format(cost.full_repository); $('#focused-tokens').textContent=format(cost.focused_total);
  $('#packet-tokens').textContent=format(cost.focused_change_packet); $('#source-tokens').textContent=format(cost.recommended_source); $('#saved-tokens').textContent=format(cost.difference);
  $('#live-saved').textContent=`${Number(cost.difference_percent || 0).toFixed(1)}%`;
  requestAnimationFrame(() => {
    $('#full-bar').style.width='100%';
    $('#focused-bar').style.width=`${Math.max(2,(cost.focused_total/Math.max(cost.full_repository,1))*100)}%`;
  });
  drawGraph(data.graph || {modules:[],dependencies:[]},packet);
}

function graphPositions(nodes, centerY=205) {
  const positions=new Map();
  nodes.forEach((node,index) => {
    const angle=(Math.PI*2*index/Math.max(nodes.length,1))-Math.PI/2;
    const radius=nodes.length<=1?0:Math.min(165,80+nodes.length*8);
    positions.set(node,{x:380+Math.cos(angle)*radius,y:centerY+Math.sin(angle)*radius});
  });
  return positions;
}

function addEdges(layer, links, positions, className) {
  const ns='http://www.w3.org/2000/svg'; layer.replaceChildren();
  links.forEach(link => {
    if(!positions.has(link.source)||!positions.has(link.target))return;
    const a=positions.get(link.source),b=positions.get(link.target),dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1,pad=30;
    const line=document.createElementNS(ns,'line'); line.setAttribute('class',className(link));
    line.setAttribute('x1',a.x+dx/length*pad);line.setAttribute('y1',a.y+dy/length*pad);line.setAttribute('x2',b.x-dx/length*pad);line.setAttribute('y2',b.y-dy/length*pad);layer.appendChild(line);
  });
}

function drawGraph(graph,packet) {
  const nodes=graph.modules||[],links=graph.dependencies||[],positions=graphPositions(nodes);
  const targets=new Set((packet.likely_change_targets||[]).map(item=>item.module)),reads=new Set(packet.recommended_reads||[]),hints=new Set((packet.neighbor_hints||[]).map(item=>item.module));
  addEdges($('#graph-edges'),links,positions,link=>`graph-edge ${(targets.has(link.source)||targets.has(link.target))?'hot':''}`);
  const ns='http://www.w3.org/2000/svg',layer=$('#graph-nodes');layer.replaceChildren();
  nodes.forEach(node=>{const p=positions.get(node),group=document.createElementNS(ns,'g');group.setAttribute('transform',`translate(${p.x} ${p.y})`);group.setAttribute('class',`graph-node ${reads.has(node)?'read':''} ${targets.has(node)?'target':''} ${hints.has(node)?'hint':''}`);const circle=document.createElementNS(ns,'circle');circle.setAttribute('r','27');const text=document.createElementNS(ns,'text');text.setAttribute('dy','43');text.textContent=node.split('/').pop().replace('.py','');group.append(circle,text);layer.appendChild(group);});
}

function appendActivity(message,className='') {
  const line=document.createElement('p');line.textContent=message;line.className=className;$('#live-console').appendChild(line);$('#live-console').scrollTop=$('#live-console').scrollHeight;
}

function drawLiveGraph(graph,touched=new Set()) {
  const nodes=graph.modules||[],links=graph.dependencies||[],positions=graphPositions(nodes,195);
  addEdges($('#live-edges'),links,positions,()=> 'live-edge');
  const ns='http://www.w3.org/2000/svg',layer=$('#live-nodes');layer.replaceChildren();
  nodes.forEach(node=>{const p=positions.get(node),group=document.createElementNS(ns,'g');group.setAttribute('transform',`translate(${p.x} ${p.y})`);group.setAttribute('class',`live-node ${(!previousLiveNodes.has(node)||touched.has(node))?'new':''}`);const circle=document.createElementNS(ns,'circle');circle.setAttribute('r','27');const text=document.createElementNS(ns,'text');text.setAttribute('dy','43');text.textContent=node.split('/').pop().replace('.py','');group.append(circle,text);layer.appendChild(group);});
  previousLiveNodes=new Set(nodes);$('#live-modules').textContent=format(nodes.length);$('#live-edges-count').textContent=format(links.length);
}

async function pollWorkspace() {
  try {
    const response=await fetch('/api/watch',{cache:'no-store'}),data=await response.json(),graph=data.graph||{modules:[],dependencies:[]};
    const signature=JSON.stringify({modules:graph.modules,dependencies:graph.dependencies});
    const mtimes=graph.module_mtimes||{},touched=new Set(Object.keys(mtimes).filter(module=>previousMtimes[module]&&previousMtimes[module]!==mtimes[module]));
    if(signature!==lastGraphSignature||touched.size){
      const oldCount=previousLiveNodes.size;drawLiveGraph(graph,touched);
      if(graph.modules.length>oldCount)appendActivity(`${graph.modules.length-oldCount} module${graph.modules.length-oldCount===1?'':'s'} added to the graph.`,'done-line');
      if(touched.size)appendActivity(`Touched only: ${[...touched].join(', ')}`,'done-line');
      lastGraphSignature=signature;previousMtimes=mtimes;
    }
    if(data.usage&&data.usage.total_tokens!==lastUsageTokens){lastUsageTokens=data.usage.total_tokens;$('#live-tokens').textContent=format(lastUsageTokens);appendActivity(`Enter usage updated · ${format(lastUsageTokens)} provider tokens`);}
  } catch(error) { $('#live-status').textContent='reconnecting'; }
}

async function loadSample() {setLoading(true);try{const response=await fetch('/api/sample');render(await response.json());}catch(error){showError(`Could not load the sample: ${error.message}`);}finally{setLoading(false);}}

async function analyze() {
  const request=$('#request').value.trim();if(!request){showError('Describe the repeated feature request first.');return;}
  setLoading(true);showError();
  try{const response=await fetch('/api/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request})});const data=await response.json();if(!response.ok)throw new Error(data.error||'Analysis failed');render(data);appendActivity(`Planner highlighted ${(data.change_packet?.recommended_reads||[]).join(', ')||'no existing files'} before Enter reads the repo.`,'done-line');}
  catch(error){showError(error.message);}finally{setLoading(false);}
}

async function copyCommand() {try{await navigator.clipboard.writeText($('#enter-command').textContent);$('#copy-command').textContent='Copied';setTimeout(()=>$('#copy-command').textContent='Copy Enter command',1400);}catch{appendActivity('Copy failed; select the command manually.','error-line');}}

$('#sample-button').addEventListener('click',loadSample);$('#analyze-button').addEventListener('click',analyze);$('#copy-command').addEventListener('click',copyCommand);
$('#request').addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key==='Enter')analyze();});
fetch('/api/status').then(response=>response.json()).then(status=>{$('#project-label').textContent=status.project;$('#enter-command').textContent=status.enter_command;drawLiveGraph(status.graph||{modules:[],dependencies:[]});previousMtimes=status.graph?.module_mtimes||{};lastGraphSignature=JSON.stringify({modules:status.graph?.modules||[],dependencies:status.graph?.dependencies||[]});}).catch(()=>{});
setInterval(pollWorkspace,750);pollWorkspace();loadSample();
