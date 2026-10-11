(function(){
"use strict";
const root=document.getElementById('bc-__SID__');
if(!root) return;
function showErr(e){try{let b=root.querySelector('.bc-err'); if(!b){b=document.createElement('div'); b.className='bc-err'; root.insertBefore(b,root.children[1]);}
  b.textContent='⚠ NoteBug error: '+((e&&(e.message||e.reason))||String(e));}catch(_){}}
window.addEventListener('error',ev=>showErr(ev.error||ev.message));
window.addEventListener('unhandledrejection',ev=>showErr(ev.reason));
try{
const D=__DATA__;
const S=D.steps, V=D.vals, OUT=Array.from(D.out||'');
const $=s=>root.querySelector(s), $$=s=>Array.from(root.querySelectorAll(s));
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const short=(s,n)=>{s=String(s);return s.length>n?s.slice(0,n-1)+'…':s};

/*__I18N__*/
const ACH_ICON={first_run:'🚀',first_bp:'🎯',bp5:'📍',into:'🤿',deep3:'🌊',back:'⏪',con1:'🧪',con10:'🔬',bug:'🐛',finish:'🏁',power:'⚡',combo20:'🔥'};

// ---------- persistent settings ----------
const KEY='notebug:v1';
let store={ach:[]};
try{Object.assign(store,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(store))}catch(e){}};
const O=D.opts||{};
let lang=O.lang||store.lang||'ja'; if(!I18N[lang]) lang='en';
let pet=O.pet||store.pet||'🐈';
let power=O.power!=null?!!O.power:!!store.power;
let sound=O.sound!=null?!!O.sound:!!store.sound;
const ACHV=O.achievements!==false;
const THEMES=['night','light','darcula','contrast'];
let theme=O.theme||store.theme||'night'; if(!THEMES.includes(theme)) theme='night';
const clampFs=v=>Math.min(28,Math.max(9,Math.round(+v||13)));
let fs=clampFs(O.font_size||store.fs||13);
const COLORS=(O.colors&&typeof O.colors==='object')?O.colors:{};
const t=(k,v)=>{let s=(I18N[lang][k]!=null?I18N[lang][k]:I18N.en[k]); if(s==null) return k; if(v) for(const x in v) s=String(s).split('{'+x+'}').join(v[x]); return s;};

// ---------- elements ----------
const codeEl=$('.bc-code'), varsEl=$('.bc-vars'), stackEl=$('.bc-stack'), outEl=$('.bc-out'),
  logEl=$('.bc-log'), logWrap=$('.bc-logwrap'), inEl=$('.bc-in'), statusEl=$('.bc-status'), tl=$('.bc-tl'),
  petEl=$('.bc-pet'), petE=$('.bc-pet-e'), bubble=$('.bc-bubble'), wrap=$('.bc-codewrap'),
  comboEl=$('.bc-combo'), bannerEl=$('.bc-banner'), cv=$('.bc-fx'), ctx=cv.getContext('2d');

// ---------- syntax highlight ----------
const KW=new Set('False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case'.split(' '));
const BI=new Set('print range len int str float list dict set tuple input sum min max abs sorted enumerate zip map filter open type isinstance round bool reversed any all super breakpoint chr ord divmod pow'.split(' '));
function el(tag,cls,txt){const e=document.createElement(tag); if(cls) e.className=cls; if(txt!=null) e.textContent=txt; return e;}
function hl(line){
  const re=/(#.*$)|([rbfuRBFU]{0,2}"(?:[^"\\]|\\.)*"?|[rbfuRBFU]{0,2}'(?:[^'\\]|\\.)*'?)|(\b\d[\d_]*(?:\.\d+)?\b)|([A-Za-z_\u00c0-\uffff][\w\u00c0-\uffff]*)|([\s\S])/g;
  const f=document.createDocumentFragment(); let m, prev='';
  const put=(cls,txt)=>f.appendChild(cls?el('span',cls,txt):document.createTextNode(txt));
  while((m=re.exec(line))){
    if(m[1]){put('k-com',m[1]);prev='';}
    else if(m[2]){put('k-str',m[2]);prev='';}
    else if(m[3]){put('k-num',m[3]);prev='';}
    else if(m[4]){const w=m[4];
      put(prev==='def'||prev==='class'?'k-fn':KW.has(w)?'k-kw':w==='self'?'k-self':BI.has(w)?'k-bi':null,w); prev=w;}
    else {put(null,m[5]); if(/\S/.test(m[5])) prev='';}
  }
  if(!line) put(null,' ');
  return f;
}

// ---------- code view ----------
const lines=D.code.split('\n');
const bps=new Set(D.bps||[]);
const rows=lines.map((L,i)=>{
  const row=el('div','bc-row'), gut=el('span','bc-gut'), src=el('span','bc-src');
  gut.title='breakpoint'; gut.append(el('span','bc-dot'),el('span','bc-num',String(i+1)));
  src.appendChild(hl(L)); row.append(gut,src,el('span','bc-hint'));
  row.firstChild.addEventListener('click',()=>toggleBp(i+1));
  codeEl.appendChild(row); return row;
});
function toggleBp(ln){
  const s=lines[ln-1].trim();
  if(!s||s.startsWith('#')){const r=rows[ln-1];r.classList.remove('bc-dead');void r.offsetWidth;r.classList.add('bc-dead');say(t('notExec'));return;}
  if(bps.has(ln)) bps.delete(ln); else {bps.add(ln); tone(880,.06,'sine',.04);}
  if(bps.size>=5) achieve('bp5');
  rows.forEach((r,i)=>r.classList.toggle('bc-bp',bps.has(i+1)));
}
rows.forEach((r,i)=>r.classList.toggle('bc-bp',bps.has(i+1)));

// ---------- state ----------
let cur=-1, prev=-1, lvl=0;
const expanded=new Set();
const conHist={}; const cmdHist=[]; let hIdx=0; let conCount=0;
tl.max=Math.max(0,S.length-1);

function frameOf(st){return st.s[Math.min(lvl,st.s.length-1)];}
function fnName(f){return f.fn==='<module>'?'<module>':f.fn+'()';}

function render(){
  const st=cur>=0?S[cur]:null;
  rows.forEach(r=>{r.classList.remove('bc-cur','bc-ret','bc-exc','bc-callsite');r.lastChild.textContent='';});
  if(st){
    if(st.e!=='end'){
      const top=st.s.length-1;
      const row=rows[st.ln-1];
      if(row){row.classList.add(st.e==='r'?'bc-ret':st.e==='x'?'bc-exc':'bc-cur'); if(lvl===top) scrollTo(row);}
      if(lvl<top){const f=st.s[lvl]; const r=rows[f.ln-1]; if(r){r.classList.add('bc-callsite'); scrollTo(r);}}
    } else if(st.eln){const r=rows[st.eln-1]; if(r){r.classList.add('bc-exc'); scrollTo(r);}}
    hints(st);
  }
  renderStack(st); renderVars(st);
  renderOut(st);
  const ow=outEl.parentNode; ow.scrollTop=ow.scrollHeight;
  if(!st) statusEl.textContent=t('waiting');
  else if(st.e==='end') statusEl.textContent=t('stepFmt',{i:cur+1,n:S.length})+' · '+t('finished');
  else statusEl.textContent=t('stepFmt',{i:cur+1,n:S.length})+' · '+t('lineFmt',{ln:st.ln});
  tl.value=Math.max(cur,0);
  const atEnd=st&&st.e==='end';
  btn('back').disabled=cur<=0; btn('restart').disabled=cur<0;
  ['run','over','into','out'].forEach(a=>btn(a).disabled=!!atEnd||!!D.syntax||!S.length);
  btn('out').disabled=btn('out').disabled||!st||st.d<=1;
  const f=st&&frameOf(st); $('.bc-conwhere').textContent=f?t('conWhere',{fn:fnName(f)}):'';
  $('.bc-frname').textContent=f?fnName(f):'';
}
const btn=a=>root.querySelector(`[data-a="${a}"]`);
const FIGS=(D.figs||[]).slice().sort((a,b)=>a.o-b.o||a.si-b.si);
function figImg(png){ const im=el('img','bc-fig'); im.src='data:image/png;base64,'+png; im.alt='figure'; im.title='click to enlarge';
  im.addEventListener('load',()=>{ const w=im.closest('.bc-scroll'); if(w) w.scrollTop=w.scrollHeight; });
  im.addEventListener('click',()=>{ const big=$('.bc-lightbox img'); big.src=im.src; $('.bc-lightbox').classList.add('bc-open'); }); return im; }
function renderOut(st){
  outEl.textContent='';
  if(!st) return;
  let pos=0;
  for(const f of FIGS){ if(f.si>cur) continue;
    if(f.o>pos){ outEl.appendChild(document.createTextNode(OUT.slice(pos,f.o).join(''))); pos=f.o; }
    outEl.appendChild(figImg(f.png)); }
  if(st.o>pos) outEl.appendChild(document.createTextNode(OUT.slice(pos,st.o).join('')));
  if(st.e==='end'&&st.ex) outEl.appendChild(el('span','bc-tb',st.ex));
}
function scrollTo(row){const top=row.offsetTop, h=codeEl.clientHeight; if(top<codeEl.scrollTop+20||top>codeEl.scrollTop+h-50) codeEl.scrollTop=top-h/3;}

function hintVal(n){ return n.sh ? (n.t==='ndarray'&&n.r.length<=28 ? n.r : n.t+' '+n.sh) : short(n.r,28); }
function hints(st){
  const f=frameOf(st); if(!f.ln&&st.e!=='end') return;
  const d=Math.min(lvl,st.s.length-1)+1;
  const vm=new Map(); f.v.forEach(([n,id,k])=>{if(!k) vm.set(n,id)});
  const seen=new Set(); if(f.ln) seen.add(f.ln);
  for(let j=cur;j>=0;j--){const s=S[j]; if(s.e==='end') continue; if(s.d<d) break; if(s.d===d&&s.s[d-1].fn===f.fn) seen.add(s.s[d-1].ln);}
  seen.forEach(ln=>{
    const src=(lines[ln-1]||'').replace(/#.*$/,'').replace(/(["'])(?:\\.|(?!\1).)*\1/g,'');
    const names=[...new Set(src.match(/[A-Za-z_\u00c0-\uffff][\w\u00c0-\uffff]*/g)||[])].filter(n=>vm.has(n));
    if(names.length&&rows[ln-1]) rows[ln-1].lastChild.textContent='  '+short(names.map(n=>n+' = '+hintVal(V[vm.get(n)])).join(', '),90);
  });
}

function renderStack(st){
  stackEl.textContent='';
  if(!st) return;
  const L=st.s.length, sel=Math.min(lvl,L-1);
  for(let i=L-1;i>=0;i--){const f=st.s[i], d=el('div','bc-fr'+(i===sel?' bc-sel':''));
    d.dataset.l=i; d.append(el('span',null,fnName(f)),el('small',null,f.ln?t('lineFmt',{ln:f.ln}):'')); stackEl.appendChild(d);}
}
stackEl.addEventListener('click',e=>{const el=e.target.closest('.bc-fr'); if(!el) return; lvl=+el.dataset.l; render();});

function vnode(parent,label,id,path,cls,depth){
  const n=V[id], has=(n.k&&n.k.length)||n.tbl, open=expanded.has(path);
  const ty=n.t+(n.sh?' '+n.sh:(n.n!=null&&n.t!=='str'?`[${n.n}]`:''));
  const r=el('div','bc-var'+(cls?' '+cls:'')); r.style.paddingLeft=(depth*14)+'px'; r.dataset.p=path; if(n.o) r.dataset.o=n.o;
  r.append(el('span','bc-car',has?(open?'▾':'▸'):''),el('span','bc-name',label),el('span','bc-ty',ty));
  if(n.o){const o=el('span','bc-oid','#'+n.o); o.title=t('sameObj'); r.appendChild(o);}
  r.appendChild(el('span','bc-val',n.r)); parent.appendChild(r);
  if(has&&open&&n.tbl) parent.appendChild(tableOf(n.tbl,depth+1));
  else if(has&&open) n.k.forEach(([l,cid])=>vnode(parent,l,cid,path+'/'+l,'',depth+1));
}
function tableOf(tb,depth){
  const wrapT=el('div','bc-tblw'); wrapT.style.marginLeft=(depth*14+14)+'px';
  const tbl=el('table','bc-tbl'), hr=el('tr');
  hr.appendChild(el('th',null,'')); tb.c.forEach(c=>hr.appendChild(el('th',null,c))); if(tb.m>tb.c.length) hr.appendChild(el('th',null,'…'));
  tbl.appendChild(hr);
  tb.v.forEach((row,i)=>{ const tr=el('tr'); tr.appendChild(el('th',null,tb.i[i])); row.forEach(x=>tr.appendChild(el('td',null,x)));
    if(tb.m>tb.c.length) tr.appendChild(el('td',null,'…')); tbl.appendChild(tr); });
  wrapT.appendChild(tbl);
  if(tb.n>tb.v.length) wrapT.appendChild(el('div','bc-tblmore',t('moreRows',{a:tb.v.length,n:tb.n})));
  return wrapT;
}
function renderVars(st){
  varsEl.textContent='';
  if(!st){varsEl.appendChild(el('div','bc-empty',t('notStartedVars')));return;}
  const f=frameOf(st), L=Math.min(lvl,st.s.length-1);
  let pm=null;
  if(prev>=0&&prev!==cur){const ps=S[prev]; const pf=ps.s[L]; if(pf&&pf.fn===f.fn) pm=new Map(pf.v.map(x=>[x[0],x[1]]));}
  if(L===st.s.length-1){
    if(st.e==='r'&&st.rv!=null) vnode(varsEl,'↩ '+t('retLabel'),st.rv,'@ret','bc-special',0);
    if(st.e==='x'||(st.e==='end'&&st.ex)){const r=el('div','bc-var bc-special bc-x');
      r.append(el('span','bc-car',''),el('span','bc-name','⚡ '+t('excLabel')),el('span','bc-val',st.e==='x'?st.ex:st.ex.split('\n').pop())); varsEl.appendChild(r);}
  }
  const vs=f.v.slice().sort((a,b)=>(a[2]?1:0)-(b[2]?1:0));
  vs.forEach(([name,id,k])=>{
    let c=k?'bc-dim':'';
    if(pm&&!k){ if(!pm.has(name)) c+=' bc-new'; else if(pm.get(name)!==id) c+=' bc-chg'; }
    vnode(varsEl,name,id,L+':'+f.fn+':'+name,c.trim(),0);
  });
  if(!varsEl.childNodes.length) varsEl.appendChild(el('div','bc-empty',t('noVars')));
}
varsEl.addEventListener('click',e=>{const r=e.target.closest('.bc-var'); if(!r||!r.querySelector('.bc-car').textContent) return;
  const p=r.dataset.p; expanded.has(p)?expanded.delete(p):expanded.add(p); renderVars(cur>=0?S[cur]:null);});
varsEl.addEventListener('mouseover',e=>{const r=e.target.closest('.bc-var'); $$('.bc-var.bc-same').forEach(x=>x.classList.remove('bc-same'));
  if(r&&r.dataset.o) $$(`.bc-var[data-o="${r.dataset.o}"]`).forEach(x=>x.classList.add('bc-same'));});
varsEl.addEventListener('mouseleave',()=>$$('.bc-var.bc-same').forEach(x=>x.classList.remove('bc-same')));

// ---------- navigation ----------
function go(i,why){
  if(i<0||i>=S.length) return;
  prev=cur; cur=i; lvl=S[i].s.length-1;
  render(); react(why);
}
const isBp=s=>s.e==='l'&&bps.has(s.ln);
function run(){ for(let i=cur+1;i<S.length;i++) if(isBp(S[i])) return go(i,'bp'); go(S.length-1,bps.size?'end':'nobp'); }
function into(){ go(cur<0?0:cur+1,'step'); }
function over(){ if(cur<0) return go(0,'step'); const d0=S[cur].d;
  for(let i=cur+1;i<S.length;i++){const s=S[i]; if(s.e==='end'||s.d<=d0) return go(i,'step'); if(isBp(s)) return go(i,'bp');} }
function out(){ if(cur<0) return; const d0=S[cur].d;
  for(let i=cur+1;i<S.length;i++){const s=S[i]; if(s.e==='end'||s.d<d0) return go(i,'step'); if(isBp(s)) return go(i,'bp');} }
function back(){ if(cur>0) go(cur-1,'back'); }
function restart(){ prev=-1; cur=-1; lvl=0; render(); say(bps.size?t('readyBp',{n:bps.size}):t('ready')); }
const ACT={run,over,into,out,back,restart};
$$('.bc-btn[data-a]').forEach(b=>b.addEventListener('click',()=>ACT[b.dataset.a]()));
tl.addEventListener('input',()=>go(+tl.value,'jump'));
root.addEventListener('keydown',e=>{
  if(e.target.matches('input,select,textarea')) return;
  const k=e.key; let f=null;
  if(k==='F9') f=run; else if(k==='F8'&&e.shiftKey) f=out; else if(k==='F8') f=over; else if(k==='F7') f=into;
  else if(k==='ArrowRight') f=into; else if(k==='ArrowDown') f=over; else if(k==='ArrowUp') f=out; else if(k==='ArrowLeft') f=back;
  if(f){e.preventDefault(); if(!btn(f.name).disabled) f();}
});

// ---------- reactions: pet, achievements ----------
function react(why){
  const st=S[cur], ps=prev>=0?S[prev]:null;
  achieve('first_run');
  let msg=null, kind='step';
  if(st.e==='end'){ if(st.ex){msg=t('endErr');kind='exc';achieve('bug');} else {msg=why==='nobp'?t('noBpEnd'):t('end');kind='end';achieve('finish');} }
  else if(st.e==='x'){msg=t('exc',{ex:short(st.ex,70)});kind='exc';achieve('bug');}
  else if(why==='bp'){msg=t('hit',{ln:st.ln});kind='bp';achieve('first_bp');}
  else if(st.e==='r'){msg=t('ret',{fn:st.s[st.s.length-1].fn,val:short(V[st.rv].r,30)});}
  else if(ps&&st.d>ps.d){msg=t('enter',{fn:st.s[st.s.length-1].fn});achieve('into');if(st.d>=4)achieve('deep3');}
  else if(why==='back'){msg=t('backMsg');achieve('back');}
  else if(ps&&why!=='jump') msg=changeMsg(ps,st);
  if(!msg&&ps&&why!=='jump'&&FIGS.some(f=>f.si>prev&&f.si<=cur)) msg=t('figMsg');
  if(msg) say(msg);
  if(why!=='jump') fx(kind);
}
function changeMsg(ps,st){
  const a=ps.s[ps.s.length-1], b=st.s[st.s.length-1]; if(a.fn!==b.fn||ps.d!==st.d) return null;
  const pm=new Map(a.v.map(x=>[x[0],x[1]]));
  for(const [n,id,k] of b.v){ if(k) continue; if(!pm.has(n)) return t('newvar',{name:n,val:short(V[id].r,30)}); if(pm.get(n)!==id) return t('changed',{name:n,val:short(V[id].r,30)}); }
  return null;
}
let sayT=null;
function say(msg){
  bubble.textContent=msg;
  const lane=petEl.parentNode; bubble.classList.toggle('bc-right',petEl.offsetLeft>lane.clientWidth/2);
  petEl.classList.remove('bc-talk'); void petEl.offsetWidth; petEl.classList.add('bc-talk');
  clearTimeout(sayT); sayT=setTimeout(()=>petEl.classList.remove('bc-talk'),3800);
}
let tipI=Math.floor(Math.random()*7);
petEl.addEventListener('click',()=>{const tips=t('tips'); say(tips[tipI++%tips.length]); tone(660,.08,'sine',.05); tone(990,.08,'sine',.04,.08);});

const ACH_KEYS=Object.keys(ACH_ICON);
function drawTrophy(){const b=$('.bc-trophy'); b.hidden=!ACHV; b.lastChild.textContent=store.ach.filter(k=>ACH_ICON[k]).length+'/'+ACH_KEYS.length; b.title=t('achList',{a:store.ach.length,b:ACH_KEYS.length});}
function achieve(k){ if(!ACHV||store.ach.includes(k)) return; store.ach.push(k); save(); drawTrophy(); toast(ACH_ICON[k]+' '+t('achGot'),t('ach')[k]); }
const tq=[]; let tqOn=0;
function toast(title,body){tq.push([title,body]); pump();}
function pump(){ while(tqOn<2&&tq.length){ const [title,body]=tq.shift(); tqOn++;
  const box=el('div','bc-toast'); box.append(el('b',null,title),document.createTextNode(body));
  $('.bc-toasts').appendChild(box); setTimeout(()=>{box.remove(); tqOn--; pump();},2600);} }
$('.bc-trophy').addEventListener('click',()=>{const got=ACH_KEYS.filter(k=>store.ach.includes(k));
  toast('🏆 '+t('achList',{a:got.length,b:ACH_KEYS.length}),got.map(k=>ACH_ICON[k]+' '+t('ach')[k]).join('  ')||'—');});

// ---------- power mode ----------
let parts=[], animOn=false, combo=0, lastT=0;
const COLS=['#ffc94a','#ff6b7a','#52e0a4','#7cb8ff','#b99bff'];
function burst(x,y,n,big){
  for(let i=0;i<n;i++) parts.push({x,y,vx:(Math.random()-.5)*(big?10:5),vy:(Math.random()-.8)*(big?9:4),life:1,c:COLS[i%COLS.length],r:1.5+Math.random()*(big?3.5:2)});
  if(!animOn){animOn=true; cv.width=wrap.clientWidth; cv.height=wrap.clientHeight; requestAnimationFrame(tick);}
}
function tick(){
  ctx.clearRect(0,0,cv.width,cv.height);
  parts.forEach(p=>{p.x+=p.vx;p.y+=p.vy;p.vy+=.25;p.life-=.025; ctx.globalAlpha=Math.max(p.life,0); ctx.fillStyle=p.c; ctx.fillRect(p.x,p.y,p.r*2,p.r*2);});
  parts=parts.filter(p=>p.life>0); ctx.globalAlpha=1;
  if(parts.length) requestAnimationFrame(tick); else {animOn=false; ctx.clearRect(0,0,cv.width,cv.height);}
}
function banner(txt,col){bannerEl.textContent=txt; bannerEl.style.color=col; bannerEl.style.textShadow=`0 0 18px ${col}`;
  bannerEl.classList.remove('bc-pop'); void bannerEl.offsetWidth; bannerEl.classList.add('bc-pop');}
function fx(kind){
  sfx(kind);
  if(!power) return;
  const st=S[cur]; const ln=st.e==='end'?st.eln:st.ln; const row=ln&&rows[ln-1];
  let x=wrap.clientWidth/2, y=wrap.clientHeight/2;
  if(row){ y=row.offsetTop-codeEl.scrollTop+10; x=Math.min(row.children[0].offsetWidth+row.children[1].offsetWidth, wrap.clientWidth-30); }
  const big=kind!=='step';
  burst(x,y,big?60:14,big);
  wrap.classList.remove('bc-shake'); void wrap.offsetWidth; wrap.classList.add('bc-shake');
  const now=performance.now(); combo=(now-lastT<1800)?combo+1:1; lastT=now;
  if(combo>=3){comboEl.textContent=combo+'× COMBO'; comboEl.classList.remove('bc-pop'); void comboEl.offsetWidth; comboEl.classList.add('bc-pop');}
  if(combo===20) achieve('combo20');
  if(kind==='bp') banner('BREAK!','var(--coral)');
  else if(kind==='exc') banner('BUG!','var(--coral)');
  else if(kind==='end') banner('FINISH!','var(--mint)');
}

// ---------- sound ----------
let ac=null;
function tone(f,d,type,vol,delay){
  if(!sound) return; delay=delay||0;
  try{ ac=ac||new (window.AudioContext||window.webkitAudioContext)();
    const o=ac.createOscillator(), g=ac.createGain(), t0=ac.currentTime+delay;
    o.type=type||'square'; o.frequency.value=f; g.gain.setValueAtTime(vol||.05,t0); g.gain.exponentialRampToValueAtTime(.0001,t0+d);
    o.connect(g); g.connect(ac.destination); o.start(t0); o.stop(t0+d+.02);}catch(e){}
}
function sfx(kind){
  if(kind==='bp') [523,659,784].forEach((f,i)=>tone(f,.12,'square',.045,i*.07));
  else if(kind==='exc') {tone(160,.35,'sawtooth',.05); tone(110,.4,'sawtooth',.04,.12);}
  else if(kind==='end') [523,659,784,1047].forEach((f,i)=>tone(f,.14,'triangle',.06,i*.09));
  else if(cur>=0) tone(330+Math.min(S[cur].d,8)*80+(power?combo*12:0),.05,'triangle',.04);
}

// ---------- console ----------
function log(text,cls){const d=document.createElement('div'); d.className='c-'+cls; d.textContent=text; logEl.appendChild(d); logWrap.scrollTop=logWrap.scrollHeight; return d;}
const colab=()=>!!(D.colab&&window.google&&google.colab&&google.colab.kernel&&google.colab.kernel.invokeFunction);
const promptEl=$('.bc-prompt'), goB=$('.bc-go');
const OPENER=/:\s*(#.*)?$/;
function autosize(){
  inEl.style.height='auto'; inEl.style.height=inEl.scrollHeight+'px';
  const n=inEl.value.split('\n').length; promptEl.textContent='>>>'+'\n...'.repeat(n-1);
}
function needMore(src){
  const lines=src.split('\n'), last=lines[lines.length-1];
  if(OPENER.test(last)||/\\$/.test(last)) return true;
  const bare=src.replace(/(["'])(?:\\.|(?!\1).)*\1/g,'').replace(/#.*$/gm,'');
  let depth=0; for(const c of bare){ if('([{'.includes(c)) depth++; else if(')]}'.includes(c)) depth--; }
  if(depth>0) return true;
  if(((src.match(/"{3}/g)||[]).length%2)||((src.match(/'{3}/g)||[]).length%2)) return true;
  return lines.length>1&&last.trim()!=='';      // inside a block: an empty line finishes it
}
function insertText(text){ inEl.setRangeText(text,inEl.selectionStart,inEl.selectionEnd,'end'); autosize(); }
function lineBefore(){ const v=inEl.value, a=inEl.selectionStart; return v.slice(v.lastIndexOf('\n',a-1)+1,a); }
function newline(){
  const line=lineBefore(); let ind=(line.match(/^[ \t]*/)||[''])[0];
  if(OPENER.test(line)) ind+='    ';
  else if(/^\s*(return|pass|break|continue|raise)\b/.test(line)) ind=ind.slice(0,Math.max(0,ind.length-4));
  insertText('\n'+ind);
}
let draft='';
function setInput(v){ inEl.value=v; inEl.setSelectionRange(v.length,v.length); autosize(); }
async function submit(){
  const src=inEl.value.replace(/\s+$/,''); if(!src.trim()) return;
  cmdHist.push(src); hIdx=cmdHist.length; draft=''; setInput('');
  log(src.split('\n').map((l,i)=>(i?'... ':'>>> ')+l).join('\n'),'cmd');
  if(cur<0){log(t('conNotStarted'),'err');return;}
  if(!colab()){log(t('conNoColab'),'err');return;}
  const st=S[cur], L=Math.min(lvl,st.s.length-1), key=cur+':'+L, prior=conHist[key]||[];
  const busy=log(t('conBusy'),'info'); inEl.disabled=true; goB.disabled=true;
  try{
    const r=await google.colab.kernel.invokeFunction('notebug.eval',[D.sid,st.e==='end'?-1:cur,L,prior,src],{});
    busy.remove();
    const res=(r&&r.data&&r.data['application/json'])||{ok:false,err:'no response'};
    if(res.out) log(res.out.replace(/\n$/,''),'out');
    (res.imgs||[]).forEach(p=>{ const d=el('div','c-img'); d.appendChild(figImg(p)); logEl.appendChild(d); logWrap.scrollTop=logWrap.scrollHeight; });
    if(res.ok){ if(res.val!=null) log(res.val,'val'); conHist[key]=prior.concat([src]); conCount++; achieve('con1'); if(conCount>=10) achieve('con10'); tone(990,.06,'sine',.04);}
    else {log(res.err,'err'); tone(200,.12,'sawtooth',.04);}
  }catch(e){busy.remove(); log(String(e),'err');}
  inEl.disabled=false; goB.disabled=false; inEl.focus();
}
inEl.addEventListener('keydown',e=>{
  e.stopPropagation();
  if(e.isComposing||e.keyCode===229) return;          // Korean / Japanese IME is converting
  const v=inEl.value, a=inEl.selectionStart, b=inEl.selectionEnd;
  if(e.key==='Enter'){
    e.preventDefault();
    if(e.ctrlKey||e.metaKey) submit();
    else if(e.shiftKey||b<v.length||needMore(v)) newline();
    else submit();
  } else if(e.key==='Tab'){
    e.preventDefault();
    if(e.shiftKey){ const ls=v.lastIndexOf('\n',a-1)+1, m=v.slice(ls).match(/^ {1,4}/);
      if(m){ inEl.setRangeText('',ls,ls+m[0].length,'preserve'); inEl.setSelectionRange(Math.max(ls,a-m[0].length),Math.max(ls,a-m[0].length)); } }
    else insertText('    ');
  } else if(e.key==='Backspace'&&a===b){
    const line=lineBefore(); if(line.length&&/^ +$/.test(line)&&line.length%4===0){ e.preventDefault(); inEl.setRangeText('',a-4,a,'end'); autosize(); }
  } else if(e.key==='ArrowUp'&&cmdHist.length&&v.lastIndexOf('\n',a-1)<0){
    e.preventDefault(); if(hIdx===cmdHist.length) draft=v; hIdx=Math.max(0,hIdx-1); setInput(cmdHist[hIdx]);
  } else if(e.key==='ArrowDown'&&v.indexOf('\n',b)<0&&hIdx<cmdHist.length){
    e.preventDefault(); hIdx++; setInput(hIdx<cmdHist.length?cmdHist[hIdx]:draft);
  } else if(e.key==='Escape'){ setInput(''); }
});
inEl.addEventListener('input',autosize);
goB.addEventListener('click',()=>submit());

// ---------- options ----------
const petSel=$('.bc-petsel'), langSel=$('.bc-langsel'), powB=$('.bc-powerb'), sndB=$('.bc-soundb'),
  setB=$('.bc-setb'), setP=$('.bc-set'), themeSel=$('.bc-themesel');
function openSet(on){ setP.classList.toggle('bc-open',on); setB.setAttribute('aria-expanded',on); setB.setAttribute('aria-pressed',on); }
setB.addEventListener('click',e=>{e.stopPropagation(); openSet(!setP.classList.contains('bc-open'));});
document.addEventListener('mousedown',e=>{ if(!setP.contains(e.target)&&e.target!==setB) openSet(false); });
root.addEventListener('keydown',e=>{ if(e.key==='Escape') openSet(false); });
themeSel.addEventListener('change',()=>{theme=themeSel.value; store.theme=theme; save(); applyOpts();});
function setFs(v){ fs=clampFs(v); store.fs=fs; save(); applyOpts(); }
$('.bc-fsm').addEventListener('click',()=>setFs(fs-1));
$('.bc-fsp').addEventListener('click',()=>setFs(fs+1));
$('.bc-fsv').addEventListener('click',()=>setFs(13));
function applyOpts(){
  petE.textContent=pet; petSel.value=pet; langSel.value=lang;
  root.dataset.theme=theme; themeSel.value=theme; root.style.setProperty('--s',fs+'px'); $('.bc-fsv').textContent=fs+'px';
  for(const k in COLORS) if(/^[a-z][a-z0-9-]*$/.test(k)) root.style.setProperty('--'+k,String(COLORS[k]));
  const tn=t('themes'); Array.from(themeSel.options).forEach(o=>o.textContent=tn[o.value]||o.value);
  setB.title=t('settings'); $('.bc-fsv').title=t('fsReset');
  powB.setAttribute('aria-pressed',power); sndB.setAttribute('aria-pressed',sound); sndB.textContent=sound?'🔊':'🔈';
  powB.title=t('power'); sndB.title=t('sound'); petSel.title=t('pet');
  root.classList.toggle('bc-power-on',power);
  $$('[data-t]').forEach(el=>el.textContent=t(el.dataset.t));
  $$('.bc-btn[data-a]').forEach(b=>b.title=t(b.dataset.a));
  inEl.placeholder=t('conPh'); autosize();
  drawTrophy(); render();
}
petSel.addEventListener('change',()=>{pet=petSel.value; store.pet=pet; save(); applyOpts(); say('♪');});
langSel.addEventListener('change',()=>{lang=langSel.value; store.lang=lang; save(); applyOpts();});
powB.addEventListener('click',()=>{power=!power; store.power=power; save(); applyOpts(); if(power){achieve('power'); banner('POWER MODE','var(--amber)'); burst(wrap.clientWidth/2,wrap.clientHeight/2,50,true);}});
sndB.addEventListener('click',()=>{sound=!sound; store.sound=sound; save(); applyOpts(); tone(660,.08,'sine',.05);});

$('.bc-lightbox').addEventListener('click',()=>$('.bc-lightbox').classList.remove('bc-open'));

// ---------- start ----------
applyOpts();
log(t('conHello'),'info');
if(D.syntax){ const r=rows[D.syntax.ln-1]; if(r){r.classList.add('bc-exc'); scrollTo(r);} log(D.syntax.msg,'err'); say(t('syntax',{ln:D.syntax.ln,msg:D.syntax.msg})); }
else { setTimeout(()=>say(bps.size?t('readyBp',{n:bps.size}):t('ready')),400); if(D.hard) toast('⚠️',t('trunc',{n:D.max})); else if(D.trunc) toast('ℹ️',t('truncSoft',{n:D.max})); }
}catch(e){showErr(e);}
})();
