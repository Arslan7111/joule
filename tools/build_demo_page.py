# -*- coding: utf-8 -*-
"""
Assemble design/prototypes/demo/index.html.

The demo screen reuses candidate 05's design system verbatim: this script reads
the <style> block straight out of design/prototypes/05-fused/index.html and
wraps it around a single report screen plus a three-way footage switcher. Run
tools/build_demo.py first to (re)generate data.js, then run this.

Usage:  .venv/Scripts/python.exe tools/build_demo_page.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
core_css = (ROOT / "design" / "prototypes" / "05-fused" / "index.html").read_text(encoding="utf-8")
i = core_css.index("<style>") + 7
j = core_css.index("</style>")
CORE_CSS = core_css[i:j]

LOGO = '''<svg class="logo" viewBox="0 0 96 96" aria-hidden="true">
            <rect x="34" y="30" width="28" height="36" fill="currentColor" fill-opacity="0.12"/>
            <g transform="translate(48 48) scale(0.52) translate(-45 -50)">
              <path d="M60 18 L30 50 L52 82" fill="none" stroke="currentColor" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="60" cy="18" r="6" fill="currentColor"/>
              <circle cx="52" cy="82" r="6" fill="currentColor"/>
              <circle cx="30" cy="50" r="8" fill="var(--orange)"/>
            </g>
            <rect x="12" y="16" width="50" height="50" fill="none" stroke="currentColor" stroke-width="4"/>
            <rect x="34" y="30" width="50" height="50" fill="none" stroke="currentColor" stroke-width="4"/>
          </svg>'''
BRANDMARK = LOGO.replace('class="logo"', 'class="brandmark"')
APPCAM = '<svg class="appcam" viewBox="0 0 20 16" aria-hidden="true"><rect x="1" y="3" width="13" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M14 6.5 L19 4 V12 L14 9.5 Z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>'

EXTRA_CSS = """
/* ─── demo-only additions (switcher + single-view panels) ──────────────── */
.index button small{display:block;font-size:10.5px;color:var(--text-3);font-weight:400;margin-top:2px;letter-spacing:.01em;text-transform:none}
.index button[aria-current="true"] small{color:var(--text-2)}
.plot .trace.rgt{stroke:var(--orange-soft)}
.plot .trace.rgt.breach{stroke:var(--orange)}
.plot .bandfill{fill:var(--band)}
.plot .ghostband{stroke:var(--line-2);stroke-width:1;stroke-dasharray:2 3;vector-effect:non-scaling-stroke}
.plot .ghosttext{font-family:var(--mono);font-size:8.5px;fill:var(--text-3);letter-spacing:.07em;text-transform:uppercase}
.figlegend i.lft::before{border-top:2px solid var(--text)}
.figlegend i.rgt::before{border-top:2px solid var(--orange-soft)}
.riskline{margin:14px 16px 0;font-size:12.5px;line-height:1.5;color:var(--text-2);border-left:2px solid var(--orange);padding-left:11px}
.riskline.low{border-color:var(--green)}
.riskline b{color:var(--text);font-weight:600}
.panel.is3d .val{color:var(--text-3);font-weight:400;font-size:11px}
#notebox .note{display:block}
.trace-both-legend{display:flex;gap:4px 16px;flex-wrap:wrap;padding:6px 16px 0;font-size:10.5px;color:var(--text-3);letter-spacing:.04em;text-transform:uppercase}
.trace-both-legend i{font-style:normal;display:inline-flex;align-items:center;gap:6px}
.trace-both-legend i::before{content:"";width:15px;border-top:2px solid var(--text);flex:none}
.trace-both-legend i.r::before{border-top:2px solid var(--orange-soft)}
.trace-both-legend i.c::before{border-top:8px solid var(--band);height:0;width:15px}
/* screenshot mode: let the whole report show without the phone's inner scroll */
.still .device{height:auto;max-width:412px}
.still .viewport{overflow:visible}
.still .loading{display:none!important}
"""

BODY = '''
<div class="page">
  <header class="masthead">
    ''' + BRANDMARK + '''
    <h1>Joule Coach</h1>
    <span class="sub">Post-set report &middot; real dataset footage</span>
    <span class="spacer"></span>
    <button class="themetoggle" id="themebtn" type="button">Light</button>
  </header>

  <p class="strapline">
    The selected member-app direction &mdash; candidate 05, the lab report &mdash; rendered from
    <b>real pipeline output</b> on three squat videos from the datasets. Rep counts, joint angles,
    form scores and risk signals are the engine&rsquo;s own; nothing on this screen is authored by hand.
    Regenerate the data with <code>tools/build_demo.py</code>.
  </p>

  <div class="workbench">
    <nav class="index" aria-label="Footage">
      <h2>Footage</h2>
      <ol id="srclist">
        <li><button type="button" data-demo="clean" aria-current="true">Clean set<small>stu9_64 &middot; 14 reps</small></button></li>
        <li><button type="button" data-demo="asym">One-sided load<small>stu6_63 &middot; 17 reps</small></button></li>
        <li><button type="button" data-demo="fatigue">Fatigue at the edges<small>Fit3D s03 &middot; 8 reps</small></button></li>
      </ol>
      <p class="why" style="margin-top:18px;font-size:11.5px;color:var(--text-3);line-height:1.5">
        All three are back squats, so the sagittal panel, the corridor and the skeleton stay
        meaningful across the set. Variety is in the form, not the movement.
      </p>
    </nav>

    <div class="devicewrap">
      <div class="device">
        <div class="statusbar"><span>9:41</span><span id="sbright">Station bound</span></div>
        <div class="appbar">
          ''' + LOGO + '''
          <span class="name">JOULE COACH</span>
          <span class="spacer"></span>
          ''' + APPCAM + '''
        </div>
        <div class="viewport" id="viewport">

          <div class="loading" id="loading" aria-hidden="true">
            <div class="lt">Reading the set <b id="ltick">0.0s</b></div>
            <div class="sk" style="height:52px"></div>
            <div class="sk" style="height:150px"></div>
            <div class="sk" style="height:38px"></div>
            <div class="sk" style="height:96px"></div>
            <div class="sk" style="height:96px"></div>
          </div>

          <section class="screen" id="s-report" data-active>
            <div class="titleblock">
              <div class="row">
                <div><h3 id="rtitle">Back squat</h3><div class="meta" id="rmeta"></div></div>
                <span class="stamp single" id="rstamp">1 camera &middot; 2D</span>
              </div>
            </div>

            <div class="verdict">
              <div class="vcount"><b id="vcount"></b> <span id="vcountsub"></span></div>
              <div class="cue">
                <p id="cuetext"></p>
                <div class="where" id="cuewhere"></div>
              </div>
            </div>

            <div class="riskline" id="riskline"></div>

            <div class="sechead"><h4>Deepest point</h4><span class="aux" id="figlabel"></span></div>
            <div class="figure"><svg id="fig" viewBox="42 30 156 172" role="img" aria-labelledby="figdesc"><desc id="figdesc"></desc></svg></div>
            <div class="figlegend"><i class="ref">Reference vertical</i><i>Trunk lean measured</i><span class="side">Left leg toward camera</span></div>

            <div class="sechead"><h4>Every rep in the set</h4><span class="aux">Drag to scrub</span></div>
            <div class="strip">
              <div class="cells" id="cells" role="group" aria-label="Reps in this set. Drag or use arrow keys."></div>
              <div class="striplegend"><span class="unit">Form score, 0 to 100</span></div>
              <div class="striplegend"><i>Clean</i><i class="p">Flagged</i><i class="b">Below 78</i><i class="g">Not measured</i></div>
            </div>

            <div class="sechead"><h4>Knee angle by plane</h4><span class="aux" id="scrublabel"></span></div>
            <div id="panels"></div>
            <div class="trace-both-legend"><i class="lft">Left knee</i><i class="r">Right knee</i><i class="c">Depth corridor</i></div>

            <p class="interp" id="interptext"></p>

            <button class="action" type="button"><span>Watch the 40-second fix-it demo</span><span class="arrow">&rarr;</span></button>

            <div class="apparatus">
              <h4>Method and coverage</h4>
              <div id="method"></div>
            </div>
          </section>

        </div>
      </div>
    </div>

    <aside class="notes">
      <h2>Reading this screen</h2>
      <div id="notebox"></div>
      <div class="note" data-active style="margin-top:18px;color:var(--text-3)">
        <b>Pipeline.</b> YOLOv8n detection, ByteTrack, MediaPipe pose, adaptive rep state
        machine, per-rep form scoring, set-level risk signals. One camera, so frontal and
        transverse planes are left unfilled rather than estimated from a single view.
      </div>
    </aside>
  </div>

  <footer class="foot">
    <span><b>Design</b> candidate 05, lab report</span>
    <span><b>Footage</b> RepCount Part-A, Fit3D</span>
    <span><b>Data</b> design/prototypes/demo/data.js</span>
    <span><b>Engine output</b> results/demo3, results/demo_squat_s03</span>
  </footer>
</div>
'''

SCRIPT = r'''
<script src="data.js"></script>
<script>
(function(){
  'use strict';
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var DEG = Math.PI / 180;
  var DEMOS = {};
  (window.DEMOS || []).forEach(function(d){ DEMOS[d.id] = d; });

  var VALID = {clean:1, asym:1, fatigue:1};
  var sel = (location.hash.replace('#','') in VALID) ? location.hash.replace('#','') : 'clean';
  var current = 1;
  var STILL = /(^|[?&])still(=|&|$)/.test(location.search);   // screenshot mode: no loading shim
  if(STILL){
    document.documentElement.classList.add('still');
    reduce = true;
  }

  var btn = document.getElementById('themebtn');
  btn.addEventListener('click', function(){
    var light = document.documentElement.getAttribute('data-theme') === 'light';
    if(light){ document.documentElement.removeAttribute('data-theme'); btn.textContent = 'Light'; }
    else { document.documentElement.setAttribute('data-theme','light'); btn.textContent = 'Dark'; }
  });

  /* geometry, shared with candidate 05 */
  var W=300,H=104,L=32,R=294,T=8,B=86;
  function sx(p){ return L + p*(R-L); }
  function yFor(v,min,max){ return T + (1 - (v-min)/(max-min)) * (B-T); }
  function pathFrom(pts){ var d='',i; for(i=0;i<pts.length;i++){ d += (i?'L':'M')+pts[i][0].toFixed(2)+' '+pts[i][1].toFixed(2); } return d; }

  var cellHost   = document.getElementById('cells');
  var panelHost  = document.getElementById('panels');
  var fig        = document.getElementById('fig');
  var figLabel   = document.getElementById('figlabel');
  var scrubLabel = document.getElementById('scrublabel');

  /* ── sagittal panel: real left/right knee traces ──────────────────────── */
  function sliceWindow(series,t0,t1){
    var pad=(t1-t0)*0.18+0.25, out=[], i;
    for(i=0;i<series.length;i++){ var t=series[i][0]; if(t>=t0-pad && t<=t1+pad) out.push(series[i]); }
    if(out.length<2) out = series.slice(Math.max(0,series.length-5));
    return out;
  }
  function tracePts(series,t0,t1,min,max){
    var w = sliceWindow(series,t0,t1);
    var lo=w[0][0], span=(w[w.length-1][0]-lo)||1;
    return w.map(function(pt){ return [sx((pt[0]-lo)/span), yFor(pt[1],min,max)]; });
  }
  function buildSagittal(){
    var d = DEMOS[sel], min=d.knee.min, max=d.knee.max;
    var wrap=document.createElement('div'); wrap.className='panel';
    wrap.innerHTML =
      '<div class="gutter"><span>2D single view</span></div>'+
      '<div class="panelbody">'+
        '<div class="panelhead"><h5>Sagittal <span class="unit">knee angle, deg &middot; 180 is a straight leg</span></h5><span class="val" data-val></span></div>'+
        '<svg class="plot" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" role="img">'+
          '<path class="bandfill" data-band/>'+
          '<line class="axis" x1="'+L+'" y1="'+B+'" x2="'+R+'" y2="'+B+'"/>'+
          '<line class="axis" x1="'+L+'" y1="'+T+'" x2="'+L+'" y2="'+B+'"/>'+
          '<path class="trace" data-left/>'+
          '<path class="trace rgt" data-right/>'+
          '<text class="tlabel" x="'+L+'" y="'+(B+11)+'">TOP</text>'+
          '<text class="tlabel" x="'+((L+R)/2)+'" y="'+(B+11)+'" text-anchor="middle">BOTTOM</text>'+
          '<text class="tlabel" x="'+R+'" y="'+(B+11)+'" text-anchor="end">TOP</text>'+
          '<text class="tlabel" x="'+(L-4)+'" y="'+(T+4)+'" text-anchor="end">'+Math.round(max)+'</text>'+
          '<text class="tlabel" x="'+(L-4)+'" y="'+B+'" text-anchor="end">'+Math.round(min)+'</text>'+
        '</svg>'+
      '</div>';
    var y1=yFor(d.band[1],min,max), y0=yFor(d.band[0],min,max);
    wrap.querySelector('[data-band]').setAttribute('d','M'+L+' '+y1+' L'+R+' '+y1+' L'+R+' '+y0+' L'+L+' '+y0+'Z');
    return wrap;
  }
  function buildGhost(name,unit,note){
    var wrap=document.createElement('div'); wrap.className='panel is3d';
    wrap.innerHTML =
      '<div class="gutter"><span>3D only</span></div>'+
      '<div class="panelbody">'+
        '<div class="panelhead"><h5>'+name+' <span class="unit">'+unit+'</span></h5><span class="val">not on 1 camera</span></div>'+
        '<svg class="plot" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+
          '<line class="ghostband" x1="'+L+'" y1="'+((T+B)/2)+'" x2="'+R+'" y2="'+((T+B)/2)+'"/>'+
          '<text class="ghosttext" x="'+((L+R)/2)+'" y="'+((T+B)/2 - 6)+'" text-anchor="middle">'+note+'</text>'+
        '</svg>'+
      '</div>';
    return wrap;
  }
  function buildPanels(){
    panelHost.innerHTML='';
    panelHost.appendChild(buildSagittal());
    panelHost.appendChild(buildGhost('Frontal','knee valgus','needs the 2-camera station'));
    panelHost.appendChild(buildGhost('Transverse','hip rotation','needs the 2-camera station'));
  }

  /* ── figure: side-view squat, trunk lean is the drawn quantity ────────── */
  function drawFigure(r){
    var lean = Math.max(0, r.lean || 0);
    var drawn = Math.min(lean, 46) * DEG;          // clamp the drawing, keep the real number
    var hip=[120,120], trunkLen=52;
    var sh=[hip[0]+Math.sin(drawn)*trunkLen, hip[1]-Math.cos(drawn)*trunkLen];
    var head=[sh[0]+Math.sin(drawn)*15, sh[1]-Math.cos(drawn)*15];
    var plumbTop=[hip[0], hip[1]-trunkLen-4];
    var bad = lean > 60;   // src/form.py's own excessive-trunk-lean limit
    // legs: front (left, toward camera) bends more visibly; slight offset for the back leg
    var kneeF=[hip[0]+16, 150], ankF=[hip[0]+3, 190];
    var kneeB=[hip[0]-9, 151], ankB=[hip[0]-20, 190];
    function ln(a,b,c){ return '<line class="'+c+'" x1="'+a[0]+'" y1="'+a[1]+'" x2="'+b[0]+'" y2="'+b[1]+'"/>'; }
    function jt(p,c){ return '<circle class="'+c+'" cx="'+p[0]+'" cy="'+p[1]+'" r="2.9"/>'; }
    var off = bad ? ' off' : '';
    var s = '<line class="fig-plumb" x1="'+hip[0]+'" y1="'+hip[1]+'" x2="'+plumbTop[0]+'" y2="'+plumbTop[1]+'"/>';
    s += ln(hip,kneeB,'fig-bone') + ln(kneeB,ankB,'fig-bone');
    s += ln(hip,kneeF,'fig-bone') + ln(kneeF,ankF,'fig-bone');
    s += ln(hip,sh,'fig-bone'+off);
    s += ln(sh,[sh[0]+14,sh[1]+2],'fig-bone') + ln([sh[0]+14,sh[1]+2],[sh[0]+9,sh[1]+22],'fig-bone'); // arm
    s += '<line class="fig-bone" x1="'+(sh[0]-9)+'" y1="'+(sh[1]-2)+'" x2="'+(sh[0]+13)+'" y2="'+(sh[1]-6)+'"/>'; // bar
    s += '<circle class="fig-head" cx="'+head[0]+'" cy="'+head[1]+'" r="12"/>';
    [hip,kneeF,kneeB,ankF,ankB,sh].forEach(function(p){ s += jt(p, 'fig-joint'); });
    if(bad){
      var midT=[(hip[0]+sh[0])/2, (hip[1]+sh[1])/2];
      s += '<text class="fig-num" x="'+(midT[0]+14)+'" y="'+midT[1]+'">'+lean.toFixed(0)+'\u00b0</text>';
    }
    s += '<line class="fig-floor" x1="70" y1="192" x2="176" y2="192"/>';
    fig.innerHTML = '<desc id="figdesc">Sagittal view at the deepest point of rep '+r.n+
      '. Trunk leans '+lean.toFixed(0)+' degrees from vertical.</desc>' + s;
  }

  /* ── rep strip ───────────────────────────────────────────────────────── */
  function buildStrip(){
    var d = DEMOS[sel];
    cellHost.innerHTML='';
    cellHost.style.gridTemplateColumns = 'repeat('+d.reps.length+',1fr)';
    d.reps.forEach(function(r){
      var b=document.createElement('button'); b.type='button'; b.className='cell';
      b.setAttribute('data-state', r.state);
      b.setAttribute('aria-pressed','false');
      if(r.state==='ghost'){
        b.disabled=true;
        b.setAttribute('aria-label','Rep '+r.n+', not measured');
        b.innerHTML='<span class="num">'+r.n+'</span><span class="dev gh"><i class="nomark"></i></span>';
      } else {
        b.setAttribute('aria-label','Rep '+r.n+', form score '+r.score+' of 100');
        b.innerHTML='<span class="num">'+r.n+'</span><span class="dev'+(r.state==='breach'?' bad':'')+'">'+r.score+'</span>';
      }
      b.addEventListener('click', function(){ if(!b.disabled) select(r.n, true); });
      cellHost.appendChild(b);
    });
  }
  var dragging=false;
  function scrubAt(clientX){
    var d=DEMOS[sel], rect=cellHost.getBoundingClientRect();
    var t=(clientX-rect.left)/rect.width;
    var i=Math.floor(t*d.reps.length);
    i=Math.max(0,Math.min(d.reps.length-1,i));
    while(i>=0 && d.reps[i].state==='ghost') i--;
    if(i>=0) select(d.reps[i].n, false);
  }
  cellHost.addEventListener('pointerdown', function(e){
    dragging=true;
    try{ cellHost.setPointerCapture(e.pointerId); }catch(_){}
    scrubAt(e.clientX);
  });
  cellHost.addEventListener('pointermove', function(e){ if(dragging) scrubAt(e.clientX); });
  cellHost.addEventListener('pointerup',   function(){ dragging=false; });
  cellHost.addEventListener('pointercancel',function(){ dragging=false; });
  cellHost.addEventListener('keydown', function(e){
    if(e.key!=='ArrowLeft' && e.key!=='ArrowRight') return;
    e.preventDefault();
    var d=DEMOS[sel], step=e.key==='ArrowRight'?1:-1, n=current+step;
    while(d.reps[n-1] && d.reps[n-1].state==='ghost') n+=step;
    if(d.reps[n-1]){ select(n,false); cellHost.children[n-1].focus(); }
  });

  /* ── select a rep ────────────────────────────────────────────────────── */
  function select(n, animate){
    var d = DEMOS[sel], r = d.reps[n-1];
    if(!r || r.state==='ghost') return;
    current = n;
    Array.prototype.forEach.call(cellHost.children, function(c,i){
      c.setAttribute('aria-pressed', String(i===n-1));
    });
    var pl = panelHost.querySelector('.panel');            // first = sagittal
    var min=d.knee.min, max=d.knee.max;
    var lPts=tracePts(d.knee.left,  r.t0, r.t1, min, max);
    var rPts=tracePts(d.knee.right, r.t0, r.t1, min, max);
    var lPath=pl.querySelector('[data-left]'), rPath=pl.querySelector('[data-right]');
    lPath.setAttribute('d', pathFrom(lPts));
    rPath.setAttribute('d', pathFrom(rPts));
    var split = (r.gap!=null) ? r.gap : 0;
    var breach = r.state==='breach' || split > 18;
    lPath.classList.toggle('breach', false);
    rPath.classList.toggle('breach', split > 18);
    var val = pl.querySelector('[data-val]');
    val.textContent = 'L '+Math.round(r.depthL)+'\u00b0  R '+Math.round(r.depthR)+'\u00b0';
    val.className = 'val ' + (breach ? 'breach' : 'ok');
    if(animate && !reduce){
      [lPath,rPath].forEach(function(p,idx){
        var len=p.getTotalLength();
        p.style.strokeDasharray=len; p.style.strokeDashoffset=len;
        pl.querySelector('svg').classList.remove('drawn');
        pl.querySelector('svg').classList.add('drawing');
        void p.getBoundingClientRect();
        setTimeout(function(){
          pl.querySelector('svg').classList.remove('drawing');
          pl.querySelector('svg').classList.add('drawn');
          p.style.strokeDashoffset=0;
        }, idx*70);
      });
    } else {
      [lPath,rPath].forEach(function(p){ p.style.strokeDasharray='none'; p.style.strokeDashoffset=0; });
      pl.querySelector('svg').classList.add('drawn');
    }
    drawFigure(r);
    figLabel.textContent   = 'Rep '+n+', sagittal view';
    scrubLabel.textContent = 'Rep '+n+' of '+d.reps.length+
      (r.issues && r.issues.length ? ' \u00b7 '+r.issues[0] : ' \u00b7 clean');
  }

  /* ── render a whole demo ─────────────────────────────────────────────── */
  function renderDemo(){
    var d = DEMOS[sel];
    document.getElementById('rtitle').textContent = d.title;
    document.getElementById('rmeta').textContent =
      d.video + ' \u00b7 ' + d.counted + ' reps \u00b7 ' + d.durationSec + ' s';
    document.getElementById('sbright').textContent = 'Station bound';

    document.getElementById('vcount').textContent = String(d.counted);
    var match = d.counted === d.labeled;
    document.getElementById('vcountsub').textContent =
      'reps counted \u00b7 dataset label ' + d.labeled + (match ? ' \u00b7 exact match' : '');

    document.getElementById('cuetext').textContent  = d.verdict;
    document.getElementById('cuewhere').textContent = d.where;
    document.getElementById('interptext').textContent = d.interp;

    var rl = document.getElementById('riskline');
    if(d.risk.signals.length){
      rl.className = 'riskline';
      rl.innerHTML = '<b>Set risk: ' + d.risk.level + '.</b> ' + d.risk.signals.join(' ');
    } else {
      rl.className = 'riskline low';
      rl.innerHTML = '<b>Set risk: low.</b> No fatigue, range-of-motion or asymmetry signal crossed threshold.';
    }

    var m = document.getElementById('method');
    m.innerHTML = '';
    'abcd'.split('').forEach(function(k,idx){
      if(!d.method[idx]) return;
      var p=document.createElement('p');
      p.innerHTML = '<span class="k">'+k+'</span> '+d.method[idx];
      m.appendChild(p);
    });

    var nb = document.getElementById('notebox');
    nb.innerHTML = '';
    var notes = [
      '<b>Count.</b> Dataset labels ' + d.labeled + ' reps; the adaptive counter returned ' +
        d.counted + '. ' + (match ? 'Exact match, no tuning to this clip.' : 'Off by ' +
        Math.abs(d.counted - d.labeled) + '.'),
      '<b>What the engine flagged.</b> ' + (d.risk.signals.length
        ? d.risk.signals.join(' ') : 'Nothing at set level. Per-rep form scores carry the detail.'),
      '<b>Coverage.</b> One camera. Sagittal knee angle is real but perspective-biased; frontal ' +
        'valgus and transverse rotation need the two-camera station and are shown blank, not guessed.'
    ];
    notes.forEach(function(t){
      var el=document.createElement('div'); el.className='note'; el.setAttribute('data-active','');
      el.innerHTML=t; nb.appendChild(el);
    });

    buildStrip();
    buildPanels();
    var start = d.worstRep && d.reps[d.worstRep-1] && d.reps[d.worstRep-1].state!=='ghost'
      ? d.worstRep : 1;
    current = start;
    select(start, !reduce);
  }

  /* ── source switcher ─────────────────────────────────────────────────── */
  var loading = document.getElementById('loading');
  var ltick   = document.getElementById('ltick');
  function runLoading(cb){
    if(reduce){ cb(); return; }
    loading.setAttribute('data-on','');
    var t0=Date.now();
    var iv=setInterval(function(){ ltick.textContent=((Date.now()-t0)/1000).toFixed(1)+'s'; }, 80);
    setTimeout(function(){
      clearInterval(iv);
      loading.removeAttribute('data-on');
      cb();
    }, 900);
  }
  document.getElementById('srclist').addEventListener('click', function(e){
    var b = e.target.closest('button[data-demo]');
    if(!b || b.dataset.demo === sel) return;
    sel = b.dataset.demo;
    if(history.replaceState) history.replaceState(null,'','#'+sel);
    Array.prototype.forEach.call(document.querySelectorAll('#srclist button'), function(x){
      x.setAttribute('aria-current', String(x.dataset.demo === sel));
    });
    runLoading(renderDemo);
  });

  Array.prototype.forEach.call(document.querySelectorAll('#srclist button'), function(x){
    x.setAttribute('aria-current', String(x.dataset.demo === sel));
  });
  renderDemo();
  if(!reduce){
    loading.setAttribute('data-on','');
    var t0=Date.now();
    var iv=setInterval(function(){ ltick.textContent=((Date.now()-t0)/1000).toFixed(1)+'s'; }, 80);
    setTimeout(function(){ clearInterval(iv); loading.removeAttribute('data-on'); select(current, true); }, 1100);
  }
})();
</script>
'''

HEAD = '''<title>Joule Coach Real-Footage Demo</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
'''

out = HEAD + "\n<style>\n" + CORE_CSS + "\n" + EXTRA_CSS + "\n</style>\n" + BODY + SCRIPT
(ROOT / "design" / "prototypes" / "demo" / "index.html").write_text(out, encoding="utf-8")
print("wrote design/prototypes/demo/index.html", len(out), "chars")
