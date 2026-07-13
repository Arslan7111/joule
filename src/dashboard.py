"""
Lightweight web dashboard — zero extra dependencies.

Endpoints
---------
GET /                  → HTML page
GET /snapshot/<cam_id> → latest JPEG frame (polled by JS)
GET /data              → JSON snapshot of all cameras (polled by JS)
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DashboardServer:
    def __init__(self, port: int = 5000, gallery=None) -> None:
        self.port = port
        self.gallery = gallery
        self._frames: dict[str, bytes] = {}
        self._data:   dict[str, dict]  = {}
        self._lock = threading.Lock()

    def push_frame(self, cam_id: str, frame: np.ndarray) -> None:
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self._lock:
                self._frames[cam_id] = buf.tobytes()

    def push_data(
        self,
        cam_id: str,
        rep_counts: dict,
        angles: dict,
        state: str,
        exercise: str = '',
        form: dict | None = None,
        person: str = '',
    ) -> None:
        with self._lock:
            self._data[cam_id] = {
                'rep_counts': rep_counts,
                'angles': {
                    k: round(v, 1) if v is not None else None
                    for k, v in angles.items()
                },
                'state': state,
                'exercise': exercise,
                'form': form,
                'person': person,
            }

    def snapshot(self, cam_id: str) -> bytes | None:
        with self._lock:
            return self._frames.get(cam_id)

    def all_data(self) -> dict:
        with self._lock:
            return dict(self._data)

    def start(self) -> None:
        try:
            server = _Server(
                ('0.0.0.0', self.port),
                lambda *a, **kw: _Handler(*a, dash=self, **kw),
            )
        except OSError as exc:
            raise SystemExit(
                f"Dashboard port {self.port} is unavailable ({exc}). "
                f"Pick another with --port."
            ) from exc
        threading.Thread(target=server.serve_forever, daemon=True).start()
        logger.info(f"Dashboard → http://localhost:{self.port}")


class _Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, dash: DashboardServer, **kwargs):
        self.dash = dash
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        path = self.path.split('?')[0]
        if path == '/':
            self._send(200, 'text/html; charset=utf-8', _HTML.encode())
        elif path.startswith('/snapshot/'):
            cam_id = path[len('/snapshot/'):]
            data = self.dash.snapshot(cam_id)
            if data:
                self._send(200, 'image/jpeg', data, cache=False)
            else:
                self.send_response(404); self.end_headers()
        elif path == '/data':
            self._send(200, 'application/json',
                       json.dumps(self.dash.all_data()).encode(), cache=False)
        elif path == '/people':
            people = self.dash.gallery.people() if self.dash.gallery else []
            self._send(200, 'application/json',
                       json.dumps(people).encode(), cache=False)
        elif path == '/checkin':
            # GET /checkin?person=person_1&name=Ahmed  (kiosk integration later)
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            pid = (q.get('person') or [''])[0]
            name = (q.get('name') or [''])[0]
            ok = bool(
                pid and name and self.dash.gallery
                and self.dash.gallery.bind_name(pid, name)
            )
            self._send(200 if ok else 400, 'application/json',
                       json.dumps({'ok': ok, 'person': pid, 'name': name}).encode(),
                       cache=False)
        else:
            self.send_response(404); self.end_headers()

    def _send(self, code: int, ctype: str, body: bytes, cache: bool = True) -> None:
        try:
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            if not cache:
                self.send_header('Cache-Control', 'no-cache, no-store')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser closed the connection mid-response — harmless

    def log_message(self, *_) -> None:
        pass  # suppress request logs


# ── HTML / CSS / JS ───────────────────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Joule · Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f0f13;color:#ddd;font-family:'Segoe UI',system-ui,sans-serif}
header{display:flex;align-items:center;gap:14px;padding:10px 20px;
       background:#13131c;border-bottom:1px solid #23233a}
header h1{font-size:.9rem;font-weight:700;letter-spacing:3px;color:#7eb8f7}
#cams{display:flex;flex-wrap:wrap;gap:16px;padding:16px}

/* ── Card ── */
.card{background:#16161f;border-radius:10px;overflow:hidden;
      flex:1;min-width:340px;border:1px solid #23233a}
.card-head{display:flex;align-items:center;justify-content:space-between;
           padding:8px 14px;background:#1c1c28}
.cam-name{font-weight:700;font-size:.82rem;letter-spacing:1px}
.badge{padding:3px 10px;border-radius:20px;font-size:.65rem;
       font-weight:800;letter-spacing:1.5px;text-transform:uppercase}
.s-waiting   {background:#28283a;color:#888}
.s-descending{background:#7a4800;color:#ffbe5c}
.s-bottom    {background:#6b0000;color:#ff7070}
.s-ascending {background:#003d15;color:#4dff88}

/* ── Video ── */
.vid{width:100%;display:block;background:#000;min-height:180px}

/* ── Rep counter ── */
.reps{display:flex;gap:0;padding:14px 14px 6px}
.rep-item{flex:1;text-align:center}
.rep-num{font-size:3.4rem;font-weight:800;color:#7eb8f7;line-height:1}
.rep-lbl{font-size:.62rem;color:#555;text-transform:uppercase;
         letter-spacing:1.5px;margin-top:3px}

/* ── Exercise label & form score ── */
.ex-label{font-size:.68rem;font-weight:400;color:#f7a87e;margin-left:8px}
.form-box{padding:0 14px 4px;font-size:.72rem;min-height:18px}
.form-good{color:#4dff88}
.form-mid {color:#ffbe5c}
.form-bad {color:#ff7070}
.form-issues{color:#888;font-size:.66rem}

/* ── Angle bars ── */
.sec-title{font-size:.58rem;color:#444;text-transform:uppercase;
           letter-spacing:2px;padding:8px 14px 4px}
.angles{padding:2px 14px 8px}
.arow{display:flex;align-items:center;gap:8px;margin-bottom:5px}
.aname{width:108px;font-size:.7rem;color:#888;flex-shrink:0}
.abg{flex:1;height:6px;background:#1e1e2e;border-radius:3px}
.afill{height:100%;border-radius:3px;background:#7eb8f7;
       min-width:2px;transition:width .12s}
.aval{width:40px;text-align:right;font-size:.7rem;color:#bbb;flex-shrink:0}

/* ── Chart ── */
.chart-wrap{padding:4px 14px 14px}
svg.chart{width:100%;height:72px;background:#0a0a0d;
          border-radius:6px;display:block}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;padding:4px 14px 10px}
.leg-item{display:flex;align-items:center;gap:5px;font-size:.62rem;color:#888}
.leg-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
</style>
</head>
<body>
<header><h1>⬡  JOULE · LIVE DASHBOARD</h1></header>
<div id="cams"></div>

<script>
const HIST=30, W=400, H=72;
const COLORS=['#7eb8f7','#f7a87e','#7ef7b8','#f77eb8','#c4f77e','#b87ef7','#7ef7f7','#f7e87e','#ff9966'];
const hist={};

function stateClass(s){return 'badge s-'+(s||'waiting');}

function ensureCard(id){
  if(document.getElementById('c-'+id)) return;
  const d=document.createElement('div');
  d.className='card'; d.id='c-'+id;
  d.innerHTML=`
    <div class="card-head">
      <span class="cam-name">${id} <span class="ex-label" id="ex-${id}"></span></span>
      <span class="${stateClass()}" id="badge-${id}">WAITING</span>
    </div>
    <img class="vid" id="img-${id}" src="/snapshot/${id}" alt="">
    <div class="reps" id="reps-${id}"></div>
    <div class="form-box" id="form-${id}"></div>
    <div class="sec-title">Joint Angles</div>
    <div class="angles" id="ang-${id}"></div>
    <div class="sec-title">Angle History · last 30 s</div>
    <div class="chart-wrap">
      <svg class="chart" id="chart-${id}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"></svg>
    </div>
    <div class="legend" id="legend-${id}"></div>`;
  document.getElementById('cams').appendChild(d);
}

function angleRow(name, val){
  const pct = val!=null ? Math.min(100,(val/180)*100).toFixed(1) : 0;
  const disp = val!=null ? val.toFixed(1)+'°' : '--';
  const label = name.replace(/_/g,' ');
  return `<div class="arow">
    <div class="aname">${label}</div>
    <div class="abg"><div class="afill" style="width:${pct}%"></div></div>
    <div class="aval">${disp}</div>
  </div>`;
}

function drawChart(id, h){
  const svg=document.getElementById('chart-'+id);
  const leg=document.getElementById('legend-'+id);
  if(!svg) return;
  const now=Date.now()/1000, t0=now-HIST;
  let paths='', legendHtml='', ci=0;
  for(const [joint, pts] of Object.entries(h||{})){
    const r=pts.filter(p=>p.t>=t0);
    if(r.length<2){ci++;continue;}
    const c=COLORS[ci%COLORS.length];
    const coords=r.map(p=>`${((p.t-t0)/HIST*W).toFixed(1)},${(H-(p.v/180)*H).toFixed(1)}`);
    paths+=`<polyline points="${coords.join(' ')}" fill="none" stroke="${c}" stroke-width="1.5" vector-effect="non-scaling-stroke" opacity=".85"/>`;
    // dot at current value
    const last=r[r.length-1];
    const lx=((last.t-t0)/HIST*W).toFixed(1), ly=(H-(last.v/180)*H).toFixed(1);
    paths+=`<circle cx="${lx}" cy="${ly}" r="3" fill="${c}" vector-effect="non-scaling-stroke"/>`;
    legendHtml+=`<div class="leg-item"><div class="leg-dot" style="background:${c}"></div>${joint.replace(/_/g,' ')} ${last.v.toFixed(0)}°</div>`;
    ci++;
  }
  svg.innerHTML=paths;
  if(leg) leg.innerHTML=legendHtml;
}

function tick(){
  fetch('/data').then(r=>r.json()).then(data=>{
    const now=Date.now()/1000;
    for(const [id, cam] of Object.entries(data)){
      ensureCard(id);

      const b=document.getElementById('badge-'+id);
      if(b){b.className=stateClass(cam.state); b.textContent=(cam.state||'waiting').toUpperCase();}

      const rDiv=document.getElementById('reps-'+id);
      if(rDiv) rDiv.innerHTML=Object.entries(cam.rep_counts||{})
        .map(([k,v])=>`<div class="rep-item"><div class="rep-num">${v}</div><div class="rep-lbl">${k.replace('_',' ')}</div></div>`)
        .join('');

      const ex=document.getElementById('ex-'+id);
      if(ex) ex.textContent=(cam.person?cam.person+' · ':'')+(cam.exercise||'');

      const fDiv=document.getElementById('form-'+id);
      if(fDiv){
        if(cam.form&&cam.form.score!=null){
          const s=cam.form.score;
          const cls=s>=85?'form-good':s>=65?'form-mid':'form-bad';
          const issues=(cam.form.issues||[]).join(' · ');
          const cue=(cam.form.cues||[])[0];
          fDiv.innerHTML=`last rep form: <b class="${cls}">${s}</b>`+
            (issues?` <span class="form-issues">${issues}</span>`:'')+
            (cue?`<div class="form-issues">💡 ${cue}</div>`:'');
        } else fDiv.innerHTML='';
      }

      const aDiv=document.getElementById('ang-'+id);
      if(aDiv&&cam.angles) aDiv.innerHTML=Object.entries(cam.angles)
        .filter(([,v])=>v!=null)
        .map(([k,v])=>angleRow(k,v)).join('');

      if(!hist[id]) hist[id]={};
      for(const [j,v] of Object.entries(cam.angles||{})){
        if(v==null) continue;
        if(!hist[id][j]) hist[id][j]=[];
        hist[id][j].push({t:now,v});
        hist[id][j]=hist[id][j].filter(p=>p.t>=now-HIST);
      }
      drawChart(id, hist[id]);
    }
  }).catch(()=>{});
}

function refreshVideo(){
  document.querySelectorAll('.vid').forEach(img=>{
    const b=img.src.split('?')[0];
    img.src=b+'?'+Date.now();
  });
}

setInterval(tick,         300);  // data + charts ~3 fps
setInterval(refreshVideo, 120);  // video frames ~8 fps
tick();
</script>
</body>
</html>"""
