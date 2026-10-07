(function(){
'use strict';
var D=document,W=window;
var DATA=(function(){try{return JSON.parse(D.getElementById('pdata').textContent)}catch(e){return {plans:[],prov:{}}}})();
var P=DATA.plans,PV=DATA.prov;
var RM=W.matchMedia&&W.matchMedia('(prefers-reduced-motion: reduce)').matches;
function $(s,c){return (c||D).querySelector(s)}
function $$(s,c){return Array.prototype.slice.call((c||D).querySelectorAll(s))}
function kr(n){return Math.round(n).toLocaleString('da-DK')+' kr.'}
function gbTxt(g){return g===null?'Fri data':g+' GB'}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
var bg=$('.burger');
if(bg)bg.addEventListener('click',function(){var o=D.body.classList.toggle('nav-open');bg.setAttribute('aria-expanded',o)});
$$('.nav button.dd').forEach(function(b){b.addEventListener('click',function(){var li=b.parentNode,o=!li.classList.contains('open');$$('.nav li.open').forEach(function(x){if(x!==li)x.classList.remove('open')});li.classList.toggle('open',o);b.setAttribute('aria-expanded',o)})});
D.addEventListener('keydown',function(e){if(e.key==='Escape'){$$('.nav li.open').forEach(function(x){x.classList.remove('open')});D.body.classList.remove('nav-open')}});
$$('.cmp').forEach(function(c){
var t=$('table.plans',c);if(!t)return;
$$('th[data-sort]',t).forEach(function(th){
th.setAttribute('tabindex','0');th.setAttribute('role','button');
function go(){
var k=th.getAttribute('data-sort'),asc=th.classList.contains('asc')||th.classList.contains('desc')?!th.classList.contains('asc'):k==='price';
$$('th',t).forEach(function(x){x.classList.remove('asc','desc')});
th.classList.add(asc?'asc':'desc');$$('th',t).forEach(function(x){x.removeAttribute('aria-sort')});th.setAttribute('aria-sort',asc?'ascending':'descending');
var tb=t.tBodies[0],rows=$$('tr',tb);
rows.sort(function(a,b){var x=+a.dataset[k],y=+b.dataset[k];return asc?x-y:y-x});
rows.forEach(function(r,i){tb.appendChild(r);r.classList.toggle('extra',i>=+(c.dataset.limit||99))});
}
th.addEventListener('click',go);th.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}});
});
var m=$('.cmp-more',c);
if(m)m.addEventListener('click',function(){var col=c.classList.toggle('collapsed');m.textContent=col?m.dataset.more:'Vis færre'});
});
$$('[data-ends]').forEach(function(el){
var e=new Date(el.getAttribute('data-ends')+'T23:59:59'),d=Math.ceil((e-new Date())/864e5);
if(d<0){el.textContent='Kampagnen er udløbet – tjek ny pris';}
else if(d<=31){el.textContent=d===0?'Udløber i dag':'Udløber om '+d+(d===1?' dag':' dage');}
});
function onSeen(els,fn){
if(!('IntersectionObserver' in W)||RM){els.forEach(fn);return}
var io=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){fn(x.target);io.unobserve(x.target)}})},{rootMargin:'0px 0px -8% 0px'});
els.forEach(function(e){io.observe(e)});
}
onSeen($$('.rv'),function(e){e.classList.add('in')});
onSeen($$('.bar em[data-w]'),function(e){e.style.width=e.dataset.w+'%'});
function countUp(el,to,suffix){
if(RM){el.textContent=to.toLocaleString('da-DK')+(suffix||'');return}
var s=performance.now(),from=0,dur=900;
(function f(n){var p=Math.min(1,(n-s)/dur),v=from+(to-from)*(1-Math.pow(1-p,3));el.textContent=Math.round(v).toLocaleString('da-DK')+(suffix||'');if(p<1)requestAnimationFrame(f)})(s);
}
onSeen($$('[data-cu]'),function(e){countUp(e,+e.dataset.cu,e.dataset.suf||'')});
var tl=$$('.toc a');
if(tl.length&&'IntersectionObserver' in W){
var map={};tl.forEach(function(a){map[a.getAttribute('href').slice(1)]=a});
var io2=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){tl.forEach(function(a){a.classList.remove('on')});var a=map[x.target.id];if(a){a.classList.add('on');}}})},{rootMargin:'-20% 0px -70% 0px'});
$$('.content h2[id]').forEach(function(h){io2.observe(h)});
}
var hb=$('.hero-bubble');
if(hb&&!RM){var tips=JSON.parse(hb.dataset.tips||'[]'),ti=0;if(tips.length>1)setInterval(function(){hb.style.opacity=0;setTimeout(function(){ti=(ti+1)%tips.length;hb.innerHTML=tips[ti];hb.style.opacity=1},350)},4800)}
function fill(r){var p=(r.value-r.min)/(r.max-r.min)*100;r.style.setProperty('--p',p+'%')}
function rec(o){
var need=o.gb||0,res=P.filter(function(p){
if(o.prio==='net'&&PV[p.p].net<8.6)return false;
if(p.name.indexOf('Børn')===0&&!o.kids)return false;
if(o.fri&&p.talk!=='fri')return false;
if(o.g5&&!p.g5)return false;
if(o.kids===false&&p.tags.indexOf('boern')>-1&&p.name.indexOf('Børn')===0)return false;
var g=p.gb===null?1e6:p.gb;return g>=need;
});
res.sort(function(a,b){
if(o.prio==='eu')return ((b.eu||0)-(a.eu||0))||(a.price-b.price);
return a.price-b.price;
});
var seen={},out=[];
res.forEach(function(p){if(!seen[p.p]&&out.length<(o.n||3)){seen[p.p]=1;out.push(p)}});
return out;
}
function recHTML(list,why){
if(!list.length)return '<p>Ingen abonnementer matcher – prøv at justere.</p>';
return '<div class="recs">'+list.map(function(p,i){var v=PV[p.p];return '<div class="rec"><img src="/img/logos/'+v.logo+'.webp" alt="'+esc(v.name)+'" width="84" height="22" loading="lazy"><div><strong>'+(i===0?'<span class="badge">Bedste match</span> ':'')+esc(v.name)+' · '+esc(p.name)+'</strong><small>'+gbTxt(p.gb)+' · EU '+(p.eu?p.eu+' GB':'–')+' · '+(p.talk==='fri'?'Fri tale':p.talk+' tale')+(p.g5?' · 5G':'')+' · <b>'+kr(p.price)+'/md.</b>'+(p.intro_txt?' ('+esc(p.intro_txt)+')':'')+'</small></div><a class="btn btn-go" href="/go/'+p.p+'/" rel="sponsored nofollow noopener" target="_blank">Se tilbud</a></div>'}).join('')+'</div>'+(why?'<p style="margin-top:10px;font-size:.82rem">'+why+'</p>':'');
}
function toolData(el){
var acts=[['video','Video og streaming (Netflix, YouTube)','t/dag',0,6,0.5,.5,1],['social','Sociale medier med video (TikTok, Reels)','t/dag',0,6,0.5,.5,.7],['music','Musik og podcasts','t/dag',0,8,1,.5,.072],['calls','Videoopkald','t/uge',0,15,1,1,1.0/7*7*1],['web','Web, mails og kort','t/dag',0,6,1,.5,.06]];
el.innerHTML='<div class="tool-h"><div class="ic">'+IC.data+'</div><div><p class="tool-t">Databeregner: Hvor meget data bruger du?</p><p>Træk i skyderne – vi regner dit månedlige forbrug ud og finder de billigste abonnementer, der passer.</p></div></div><div class="row">'+acts.map(function(a){return '<div><label for="db-'+a[0]+'">'+a[1]+'</label><div class="rng"><input type="range" id="db-'+a[0]+'" min="'+a[3]+'" max="'+a[4]+'" step="'+a[6]+'" value="'+a[5]+'"><output>'+a[5]+' '+a[2]+'</output></div></div>'}).join('')+'</div><div class="result" aria-live="polite"><p style="margin:0">Dit estimerede forbrug</p><div class="big"><span class="v">0</span> GB/md.</div><p class="ex"></p><div class="rr"></div></div>';
var rs=$$('input',el);
function calc(){
var v={};rs.forEach(function(r,i){v[acts[i][0]]=+r.value;r.nextElementSibling.textContent=(+r.value).toLocaleString('da-DK')+' '+acts[i][2];fill(r)});
var gb=v.video*1*30+v.social*.7*30+v.music*.072*30+v.calls*2*4.3+v.web*.06*30;
gb=Math.round(gb*1.15);
$('.v',el).textContent=gb.toLocaleString('da-DK');
$('.ex',el).textContent='Inkl. 15 % buffer. Danskernes gennemsnit er 26,9 GB/md. (Telestatistik, 2. halvår 2024). '+(gb>250?'Du bør vælge fri data eller 1000 GB.':'Vi anbefaler mindst '+gb+' GB.');
$('.rr',el).innerHTML=recHTML(rec({gb:gb>250?1000:gb,fri:true}),'Billigste abonnementer med fri tale og mindst '+(gb>250?'1000':gb)+' GB. Beregnet med Netflix \'Høj SD\' (1 GB/t), sociale medier ca. 0,7 GB/t (skøn), Spotify normal (72 MB/t) og Zoom 720p (ca. 2 GB/t).');
}
rs.forEach(function(r){r.addEventListener('input',calc)});calc();
}
function toolSave(el){
el.innerHTML='<div class="tool-h"><div class="ic">'+IC.save+'</div><div><p class="tool-t">Sparberegner: Hvor meget kan du spare?</p><p>Indtast hvad du betaler i dag, og hvor meget data du har brug for.</p></div></div><div class="row"><div><label for="sb-p">Din pris i dag (kr./md.)</label><div class="rng"><input type="range" id="sb-p" min="49" max="449" step="5" value="199"><output>199 kr.</output></div></div><div><label for="sb-g">Data du har brug for</label><select id="sb-g"><option value="10">Op til 10 GB</option><option value="30" selected>Ca. 30 GB</option><option value="60">Ca. 60 GB</option><option value="100">Ca. 100 GB</option><option value="200">200 GB+</option><option value="1000">Fri data / 1000 GB</option></select></div></div><div class="result" aria-live="polite"><p style="margin:0">Du kan spare op til</p><div class="big"><span class="v">0</span> kr./år</div><p class="ex"></p><div class="rr"></div></div>';
var r=$('#sb-p',el),s=$('#sb-g',el);
function calc(){
fill(r);r.nextElementSibling.textContent=r.value+' kr.';
var l=rec({gb:+s.value,fri:true}),best=l[0],sv=best?Math.max(0,(+r.value-best.price)*12):0;
var v=$('.v',el);v.textContent=sv.toLocaleString('da-DK');
$('.ex',el).textContent=best?(sv>0?'Skifter du til '+PV[best.p].name+' ('+best.name+') til '+kr(best.price)+'/md., sparer du '+kr(sv/12)+' om måneden – helt uden binding, og nummeret flyttes gratis.':'Du betaler allerede en god pris. Tjek alligevel om du får 5G og nok EU-data.'):'';
$('.rr',el).innerHTML=recHTML(l,'Sammenlignet med normalpriser – introtilbud kan gøre første år endnu billigere.');
}
r.addEventListener('input',calc);s.addEventListener('change',calc);calc();
}
function toolRoam(el){
el.innerHTML='<div class="tool-h"><div class="ic">'+IC.globe+'</div><div><p class="tool-t">EU-databeregner (fair use)</p><p>Hvor meget data har du ret til i EU på et abonnement med fri eller meget data? Beregnet efter EU-reglerne for 2026.</p></div></div><div class="row"><div><label for="ro-p">Månedspris inkl. moms</label><div class="rng"><input type="range" id="ro-p" min="49" max="399" step="5" value="149"><output>149 kr.</output></div></div><div><label for="ro-k">Eurokurs</label><input type="number" id="ro-k" value="7.46" step="0.01" min="7" max="8"></div></div><div class="result" aria-live="polite"><p style="margin:0">Lovens minimum for EU-data</p><div class="big"><span class="v">0</span> GB/md.</div><p class="ex"></p></div>';
var r=$('#ro-p',el),k=$('#ro-k',el);
function calc(){
fill(r);r.nextElementSibling.textContent=r.value+' kr.';
var ex=(+r.value)/1.25,gb=2*(ex/(1.30*(+k.value||7.46)));
$('.v',el).textContent=gb.toLocaleString('da-DK',{maximumFractionDigits:1});
$('.ex',el).textContent='Formel: 2 × (pris ekskl. moms ÷ engrosloft 1,30 €/GB). '+kr(+r.value)+' inkl. moms = '+kr(ex)+' ekskl. moms. Mange selskaber giver mere end minimum – se EU-data i tabellerne.';
}
r.addEventListener('input',calc);k.addEventListener('input',calc);calc();
}
var QS=[
{q:'Hvor meget bruger du mobildata?',o:[['Lidt','Beskeder, mails, kort',10],['Normalt','Sociale medier og musik',35],['Meget','Video og streaming',90],['Rigtig meget','Hotspot, streamer alt',1000]],k:'gb'},
{q:'Hvor meget taler du i telefon?',o:[['Under 5 timer/md.','Kort og sjældent',0],['Mere end 5 timer','Eller ved ikke',1]],k:'fri'},
{q:'Hvad er vigtigst for dig?',o:[['Lavest pris','Mest for pengene','pris'],['Bedst dækning','Stabilt net overalt','net'],['5G','Højeste hastighed','5g'],['Data i udlandet','Rejser meget i EU','eu']],k:'prio'}
];
function quiz(el,closeBtn){
var st=0,a={};
function draw(){
if(st>=QS.length){
var o={gb:a.gb,fri:!!a.fri,g5:a.prio==='5g',prio:a.prio};
el.innerHTML=head()+'<div class="qz-prog"><i style="width:100%"></i></div><p class="qz-q">Dine 3 bedste matches</p>'+recHTML(rec(o),'Baseret på '+(a.gb>=1000?'fri data/1000 GB':a.gb+' GB+')+(a.fri?', fri tale':'')+'. Priser tjekket '+DATA.checked+'.').replace('class="recs"','class="recs" style="margin-top:0"')+'<p style="margin-top:14px"><button class="btn btn-ghost btn-sm" type="button" data-r>↺ Start forfra</button></p>';
$('[data-r]',el).onclick=function(){st=0;a={};draw()};bindX();return;
}
var q=QS[st];
el.innerHTML=head()+'<div class="qz-prog"><i style="width:'+(st/QS.length*100)+'%"></i></div><p class="qz-q">'+(st+1)+'/'+QS.length+' · '+q.q+'</p><div class="qz-opts">'+q.o.map(function(x,i){return '<button type="button" data-i="'+i+'"><span>'+x[0]+'</span><small>'+x[1]+'</small></button>'}).join('')+'</div>';
$$('[data-i]',el).forEach(function(b){b.onclick=function(){a[q.k]=q.o[+b.dataset.i][2];st++;draw()}});bindX();
}
function head(){return '<div class="qz-top">'+SIMO_SM+'<div><p class="tool-t"'+(closeBtn?' id="qz-title"':'')+'>Find dit abonnement på 30 sek.</p><p style="margin:0;font-size:.88rem;color:#5A6A80">Simo matcher dig med '+P.length+' abonnementer</p></div>'+(closeBtn?'<button class="qz-x" type="button" aria-label="Luk">×</button>':'')+'</div>'}
function bindX(){var x=$('.qz-x',el);if(x)x.onclick=function(){var d=el.closest('dialog');if(d)d.close()}}
draw();
}
var SIMO_SM=(function(){var s=$('#simo-tpl');return s?s.innerHTML:''})();
function toolFilter(el){
var nets={};Object.keys(PV).forEach(function(k){nets[PV[k].netk]=PV[k].netn});
el.innerHTML='<div class="tool-h"><div class="ic">'+IC.filter+'</div><div><p class="tool-t">Sammenlign alle '+P.length+' abonnementer</p><p>Filtrér på pris, data, net og 5G. Klik på kolonnerne for at sortere.</p></div></div><div class="filters"><div><label for="f-max">Maks. pris/md.</label><div class="rng"><input type="range" id="f-max" min="19" max="399" step="10" value="399"><output>399 kr.</output></div></div><div><label for="f-gb">Min. data</label><select id="f-gb"><option value="0">Alle</option><option value="10">10 GB+</option><option value="30">30 GB+</option><option value="50">50 GB+</option><option value="100">100 GB+</option><option value="200">200 GB+</option><option value="999">Fri data / 1000 GB</option></select></div><div><label for="f-net">Mobilnet</label><select id="f-net"><option value="">Alle net</option>'+Object.keys(nets).map(function(k){return '<option value="'+k+'">'+nets[k]+'</option>'}).join('')+'</select></div><div><label class="tgl"><input type="checkbox" id="f-fri" checked> Fri tale</label><label class="tgl" style="padding-top:0"><input type="checkbox" id="f-5g"> Kun 5G</label></div></div><p class="count" aria-live="polite"></p>';
var tbl=el.nextElementSibling&&el.nextElementSibling.classList.contains('cmp')?el.nextElementSibling:null;
if(!tbl)return;
var rows=$$('tbody tr',tbl),mx=$('#f-max',el);
tbl.classList.remove('collapsed');var mb=$('.cmp-more',tbl);if(mb)mb.style.display='none';
function run(){
fill(mx);mx.nextElementSibling.textContent=mx.value+' kr.';
var n=0,g=+$('#f-gb',el).value,nt=$('#f-net',el).value,fr=$('#f-fri',el).checked,g5=$('#f-5g',el).checked;
rows.forEach(function(r){var d=r.dataset,ok=+d.price<=+mx.value&&(+d.gb>=g||(g===999&&+d.gb>=1000))&&(!nt||d.net===nt)&&(!fr||d.fri==='1')&&(!g5||d.g5==='1');r.style.display=ok?'':'none';if(ok)n++});
$('.count',el).textContent=n+' abonnementer matcher dine filtre';
}
$$('input,select',el).forEach(function(i){i.addEventListener('input',run);i.addEventListener('change',run)});run();
}
var IC={
data:'<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
save:'<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
globe:'<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>',
filter:'<svg viewBox="0 0 24 24" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 3H2l8 9.5V19l4 2v-8.5z"/></svg>'
};
$$('[data-tool]').forEach(function(el){
var t=el.dataset.tool;
try{
if(t==='databeregner')toolData(el);else if(t==='sparberegner')toolSave(el);else if(t==='roaming')toolRoam(el);
else if(t==='quiz'){var w=D.createElement('div');w.className='qz';el.appendChild(w);quiz(w,false)}
else if(t==='filter')toolFilter(el);
}catch(e){}
});
var dlg=$('#quiz-dlg');
function openQuiz(){if(!dlg)return;var b=$('.qz',dlg);quiz(b,true);if(dlg.showModal)dlg.showModal();else dlg.setAttribute('open','')}
$$('[data-quiz]').forEach(function(b){b.addEventListener('click',function(e){e.preventDefault();D.body.classList.remove('nav-open');openQuiz()})});
if(dlg)dlg.addEventListener('click',function(e){if(e.target===dlg)dlg.close()});
var hp=$('.helper');
if(hp){var sh=false,over=0;
W.addEventListener('scroll',function(){var s=W.scrollY>520&&!over;if(s!==sh){sh=s;hp.classList.toggle('show',s)}},{passive:true});
if('IntersectionObserver' in W&&W.innerWidth<720){var vis=new Set();var io3=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting)vis.add(x.target);else vis.delete(x.target)});over=vis.size;var s=W.scrollY>520&&!over;sh=s;hp.classList.toggle('show',s)});$$('.cmp,.tool,.qpicks,.top3,.ctabox,.pcard').forEach(function(e){io3.observe(e)})}}
})();