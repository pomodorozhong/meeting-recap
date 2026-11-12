"""Run recap settings on three synthetic calls, write blinded grading sheets, and count the grades.

Usage: collection_recap_pairs.py FIXTURES PAIRS [--report | --serve [--port N]]

FIXTURES is the verified synthetic collection and PAIRS a new absolute folder outside Git. Without --report this
runs every setting on every call through the pipeline (rerunning the command skips finished runs), then writes
PAIRS/grading/<call>.md with the recaps under letters, PAIRS/key.json (which letter is which setting) and an empty
PAIRS/grades.json. Grade in the browser with --serve (it saves to grades.json as you click) or edit grades.json by hand, then run with --report to check it is complete and write
PAIRS/report.json. The plan is in docs/experiments/2026-11-06-recap-recognizer-vs-diarizer.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

from collection import build, digest, load

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent / "pipelines" / "whisper-sortformer"
CHECKS = load(HERE / "reference/recap-checks.json")["calls"]
SETTINGS = {
    "whisper-sortformer": [],
    "turbo-sortformer": ["--asr", "turbo-q4"],
    "whisper-who": ["--diarizer", "who"],
    "turbo-who": ["--asr", "turbo-q4", "--diarizer", "who"],
    # Used by docs/experiments/2026-11-06-keep-segments-defaults.md; the other settings are shared.
    "whisper-sortformer-segments": ["--keep-asr-segments"],
}
VERDICTS = ("full", "partial", "wrong_or_absent")
STAMP = re.compile(r"\d\d:\d\d:\d\d")


def commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()


def run(fixtures, pairs):
    if any((p / ".git").exists() for p in [pairs, *pairs.parents]):
        raise ValueError("PAIRS must be outside Git")
    build(fixtures, check_only=True)
    marker = pairs / "batch.json"
    if pairs.exists() and not marker.exists():
        raise ValueError("PAIRS exists but is not a folder this script started; choose a new path")
    pairs.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(json.dumps({"code_commit": commit(), "settings": SETTINGS, "calls": list(CHECKS)}, indent=2))
    for call, info in CHECKS.items():
        for name, options in SETTINGS.items():
            folder = pairs / call / name
            if (folder / "summary.json").exists():
                continue
            resume = ["--resume"] if folder.exists() else []
            print(f"== {call} / {name}", flush=True)
            subprocess.run([PIPE / ".venv/bin/python", PIPE / "recap.py", "run", fixtures / call / "call.wav", folder,
                            "--language", info["language"], *options, *resume],
                           check=True, env={**os.environ, "HF_HUB_OFFLINE": "1"})
    sheets(pairs)


def cited_lines(folder, recap):
    transcript = (folder / "transcript.md").read_text(encoding="utf-8").splitlines()
    lines = []
    for stamp in dict.fromkeys(STAMP.findall(recap)):
        lines += [f"- {line.replace('**', '')}" for line in transcript if line.startswith(f"**[{stamp}]")]
    return lines


def sheets(pairs):
    batch = load(pairs / "batch.json")
    key, grades = {}, {}
    (pairs / "grading").mkdir(exist_ok=True)
    for call, info in CHECKS.items():
        # A fixed order by hash hides which setting is which without needing a random seed.
        order = sorted(batch["settings"], key=lambda s: hashlib.sha256(f"7/{call}/{s}".encode()).hexdigest())
        key[call] = {chr(65 + i): name for i, name in enumerate(order)}
        grades[call] = {label: {"verdicts": [None] * len(info["checks"]), "supported": [None] * len(info["checks"]),
                                "reopens_settled_issue": None, "unsupported_or_garbled_detail": None}
                        for label in key[call]}
        text = [f"# Grading sheet: {call}", "",
                "For each recap, grade every check **full**, **partial** or **wrong_or_absent**, and say whether a line "
                "the recap cites supports it (`supported`). Also say whether the recap reopens a question the call "
                "settled, and whether it contains unsupported or garbled detail. Put the answers in `grades.json`.", "",
                "Checks, in the order of the `verdicts` and `supported` lists:", ""]
        text += [f"{n + 1}. {check}" for n, check in enumerate(info["checks"])]
        for label, name in key[call].items():
            folder = pairs / call / name
            recap = (folder / "summary.md").read_text(encoding="utf-8")
            text += ["", f"## Recap {label}", "", recap, "", f"### Lines cited by recap {label}", ""]
            text += cited_lines(folder, recap) or ["(none)"]
        (pairs / "grading" / f"{call}.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    for name, content in (("key.json", key), ("grades.json", grades)):
        if not (pairs / name).exists():
            (pairs / name).write_text(json.dumps(content, indent=2) + "\n")
    print(f"Grading sheets are in {pairs / 'grading'}. Fill in {pairs / 'grades.json'}, then rerun with --report.")


PAGE = """<!doctype html><meta charset=utf-8><title>Recap grading</title>
<style>body{font:15px system-ui;max-width:1400px;margin:1rem auto;padding:0 1rem}nav button{margin-right:.5rem}
.card{border:1px solid #888;border-radius:6px;padding:.8rem;margin:1rem 0}pre{white-space:pre-wrap;background:#8881;padding:.6rem}
.row{margin:.4rem 0}.ok{color:#080}.todo{color:#b60}audio{width:100%;position:sticky;top:0;background:Canvas;z-index:2}.cols{display:grid;grid-template-columns:1fr 1fr;gap:1rem}@media(max-width:900px){.cols{grid-template-columns:1fr}}.tr{max-height:78vh;overflow:auto;position:sticky;top:3rem;align-self:start;border:1px solid #8884;border-radius:4px;padding:.4rem;font-size:13px}.ln{padding:2px 4px 2px 6px;border-radius:3px;margin:2px 0}.ln.cited{background:#fc03}.ln.hit{outline:2px solid #06c}a.t{cursor:pointer;color:#06c;text-decoration:underline}</style><h1>Recap grading</h1><nav id=nav></nav><div id=progress></div><div id=main></div>
<script>
const TOKEN=new URLSearchParams(location.search).get('token');const D=__DATA__;let G=__GRADES__;let call=Object.keys(D)[0];
const V=['full','partial','wrong_or_absent'];
function save(){fetch('/save?token='+TOKEN,{method:'POST',body:JSON.stringify(G)});render(false)}
function done(c,l){const g=G[c][l];return g.verdicts.every(v=>v)&&g.supported.every(v=>v!==null)&&g.reopens_settled_issue!==null&&g.unsupported_or_garbled_detail!==null}
function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function lnk(t,l){return esc(t).replace(/\\d\\d:\\d\\d:\\d\\d/g,m=>`<a class=t onclick="seek('${m}','${l}')">${m}</a>`)}
function seek(s,l){const a=document.getElementById('player'),[h,m,x]=s.split(':').map(Number);a.currentTime=h*3600+m*60+x;a.play();
 if(l){document.querySelectorAll('.ln.hit').forEach(e=>e.classList.remove('hit'));const e=[...document.querySelectorAll('#tr-'+l+' .ln')].filter(e=>e.dataset.t==s);e.forEach(x=>x.classList.add('hit'));if(e[0])e[0].scrollIntoView({block:'center'})}}
function col(sp){const m=sp.match(/[A-Z]$/);const i=m?m[0].charCodeAt(0)-65:sp.length;return `hsl(${[210,25,140,285,50,350,175,90][i%8]} 65% 42%)`}
function trans(r){const c=new Set(r.recap.match(/\\d\\d:\\d\\d:\\d\\d/g)||[]);return r.transcript.map(x=>`<div class="ln${c.has(x.t)?' cited':''}" data-t="${x.t}" style="border-left:5px solid ${col(x.s)}"><a class=t onclick="seek('${x.t}')">${x.t}</a> <b style="color:${col(x.s)}">${esc(x.s)}</b> ${esc(x.x)}</div>`).join('')}
function render(full=true){let all=0,n=0;for(const c in D)for(const r of D[c].recaps){n++;if(done(c,r.label))all++}
 document.getElementById('progress').innerHTML=`<p>${all} of ${n} recaps fully graded. ${all==n?'<b class=ok>Done. Run the --report command.</b>':''}</p>`;
 document.getElementById('nav').innerHTML=Object.keys(D).map(c=>`<button onclick="call='${c}';render()">${c} (${D[c].recaps.filter(r=>done(c,r.label)).length}/${D[c].recaps.length})</button>`).join('');
 if(!full)return;const d=D[call];let h=`<h2>${call}</h2><audio id=player controls preload=metadata src="/audio/${call}?token=${TOKEN}"></audio><p>Click any timestamp to play from there.</p><ol>${d.checks.map(c=>`<li>${esc(c)}</li>`).join('')}</ol>`;
 for(const r of d.recaps){const g=G[call][r.label];h+=`<div class=card><h3>Recap ${r.label} <span class="${done(call,r.label)?'ok':'todo'}">${done(call,r.label)?'graded':'not finished'}</span></h3><div class=cols><div><pre>${lnk(r.recap,r.label)}</pre>`;
  d.checks.forEach((c,i)=>{h+=`<div class=row><b>${i+1}.</b> ${esc(c)}<br>`+V.map(v=>`<label><input type=radio name="${call}${r.label}v${i}" ${g.verdicts[i]==v?'checked':''} onchange="G['${call}']['${r.label}'].verdicts[${i}]='${v}';save()"> ${v}</label> `).join('')+` &nbsp; <label><input type=checkbox ${g.supported[i]===true?'checked':''} onchange="G['${call}']['${r.label}'].supported[${i}]=this.checked;save()"> a cited line supports it</label></div>`});
  for(const [k,t] of [['reopens_settled_issue','Reopens a question the call settled?'],['unsupported_or_garbled_detail','Unsupported or garbled detail?']]){h+=`<div class=row>${t} `+[true,false].map(b=>`<label><input type=radio name="${call}${r.label}${k}" ${g[k]===b?'checked':''} onchange="G['${call}']['${r.label}'].${k}=${b};save()"> ${b?'yes':'no'}</label>`).join(' ')+`</div>`}
  h+=`</div><div class=tr id="tr-${r.label}">${trans(r)}</div></div></div>`}
 document.getElementById('main').innerHTML=h}
G=Object.fromEntries(Object.entries(G).map(([c,ls])=>[c,Object.fromEntries(Object.entries(ls).map(([l,g])=>[l,{...g,supported:g.supported.map(x=>x===null?null:x)}]))]));render();
</script>"""


def serve(pairs, port, fixtures):
    """Serve a local grading page on 127.0.0.1 that plays each call's audio and saves to PAIRS/grades.json as answers are clicked."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    key, path = load(pairs / "key.json"), pairs / "grades.json"
    data = {}
    for call, info in CHECKS.items():
        recaps = []
        for label, name in key[call].items():
            folder = pairs / call / name
            text = (folder / "summary.md").read_text(encoding="utf-8")
            lines = [re.match(r"\*\*\[(\d\d:\d\d:\d\d)\] (.*?):\*\* (.*)", line) for line in
                     (folder / "transcript.md").read_text(encoding="utf-8").splitlines()]
            recaps.append({"label": label, "recap": text,
                           "transcript": [{"t": m.group(1), "s": m.group(2), "x": m.group(3)} for m in lines if m]})
        data[call] = {"checks": info["checks"], "recaps": recaps}
    token = secrets.token_urlsafe(9)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def ok(self):
            return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost") and f"token={token}" in self.path

        def reply(self, body, kind="text/html; charset=utf-8", status=200):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.end_headers()
            self.wfile.write(body.encode())

        def audio(self):
            call = self.path[len("/audio/"):].split("?")[0]
            if call not in CHECKS:
                return self.reply("not found", status=404)
            blob = (fixtures / call / "call.wav").read_bytes()
            start, end = 0, len(blob) - 1
            match = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            if match and (match.group(1) or match.group(2)):
                if match.group(1):
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else end
                else:
                    start = max(0, len(blob) - int(match.group(2)))
                end = min(end, len(blob) - 1)
            self.send_response(206 if match else 200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if match:
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(blob)}")
            self.end_headers()
            self.wfile.write(blob[start:end + 1])

        def do_GET(self):
            if self.ok() and self.path.startswith("/audio/"):
                return self.audio()
            if not self.ok() or not self.path.startswith("/?"):
                return self.reply("not found", status=404)
            grades = path.read_text(encoding="utf-8")
            self.reply(PAGE.replace("__DATA__", json.dumps(data)).replace("__GRADES__", grades))

        def do_POST(self):
            if not self.ok() or not self.path.startswith("/save?"):
                return self.reply("not found", status=404)
            new = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            old = load(path)
            if {c: sorted(v) for c, v in new.items()} != {c: sorted(v) for c, v in old.items()}:
                return self.reply("unexpected calls or letters", status=400)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(new, indent=2) + "\n")
            tmp.replace(path)
            self.reply("saved", "text/plain")

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Open http://127.0.0.1:{port}/?token={token}  (Ctrl-C stops; answers save as you click)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def report(pairs):
    key, grades = load(pairs / "key.json"), load(pairs / "grades.json")
    rows = {}
    for call, info in CHECKS.items():
        for label, name in key[call].items():
            g = grades[call][label]
            n = len(info["checks"])
            if (len(g["verdicts"]) != n or len(g["supported"]) != n or any(v not in VERDICTS for v in g["verdicts"])
                    or any(not isinstance(s, bool) for s in g["supported"])
                    or not isinstance(g["reopens_settled_issue"], bool)
                    or not isinstance(g["unsupported_or_garbled_detail"], bool)):
                raise ValueError(f"grades for {call} recap {label} are incomplete")
            folder = pairs / call / name
            summary = load(folder / "summary.json")
            rows.setdefault(call, {})[name] = {
                **g, "summary_md_sha256": digest(folder / "summary.md"),
                "transcript_sha256": digest(folder / "transcript.md"),
                "line_count": len(load(folder / "turns.json")), "citation_checks": summary["checks"],
                "summary_seconds": load(folder / "stages.json")["summary"]["seconds"]}
    (pairs / "report.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"{'setting':30} {'fully correct':>14} {'with citations':>15} {'uncited':>8} {'invalid':>8} {'reopened':>9} {'unsupported':>12}")
    for name in SETTINGS:
        full = sum(v == "full" for c in rows.values() for v in c[name]["verdicts"])
        cited = sum(v == "full" and s for c in rows.values() for v, s in zip(c[name]["verdicts"], c[name]["supported"]))
        uncited = sum(c[name]["citation_checks"]["items_without_evidence"] for c in rows.values())
        invalid = sum(c[name]["citation_checks"]["evidence_dropped"] for c in rows.values())
        reopened = sum(c[name]["reopens_settled_issue"] for c in rows.values())
        garbled = sum(c[name]["unsupported_or_garbled_detail"] for c in rows.values())
        total = sum(len(i["checks"]) for i in CHECKS.values())
        print(f"{name:30} {full:>11}/{total:<2} {cited:>12}/{total:<2} {uncited:>8} {invalid:>8} {reopened:>9} {garbled:>12}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("--report", action="store_true", help="check the filled-in grades and write report.json")
    parser.add_argument("--serve", action="store_true", help="grade in the browser on 127.0.0.1")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    if not args.pairs.is_absolute():
        sys.exit("PAIRS must be an absolute path")
    if args.serve:
        serve(args.pairs, args.port, args.fixtures.resolve())
    elif args.report:
        report(args.pairs)
    else:
        run(args.fixtures.resolve(), args.pairs)
