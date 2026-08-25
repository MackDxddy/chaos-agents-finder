#!/usr/bin/env python3
"""
Chaos Finder — local launcher.

Double-click "Start Chaos Finder.bat" (or run:  python chaos_app.py) from the
folder that holds chaos_tool.html + data.js.

It opens the Build Finder in your browser AND runs a tiny server on your own
computer so the in-app "Refresh available agents" button works:
  - paste your login token into the box in the app (grab it with the
    "Copy Chaos token" bookmarklet), then click Refresh.
  - it re-pulls the currently-available agents and updates the list live,
    showing progress the whole time.

100% local. The only network calls are the same game-API requests the website
itself makes; nothing about you leaves your machine. Close the window to stop.

Needs Python 3.8+ (standard library only).
"""
import json, os, glob, re, time, base64, threading, webbrowser
import urllib.request, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PORT = 8765
BASE = "https://chaos-agents.popularium.com"
LIST_PATH  = "/api/agents/list/bench?player=current"        # bench = available to you
OTHER_PATH = "/api/agents/list/contracted?player=current"   # contracted = the "other agents" tab (unavailable)
SKILL_PATH = "/api/agents/{id}/skill-map"
DELAY_SEC = 0.35
TOKEN_CACHE = os.path.join(HERE, ".chaos_token")

# ---- locate the data folder (run from Downloads or inside chaos_skills_out) ----
if os.path.isdir("chaos_skills_out"):
    OUT = "chaos_skills_out"
elif os.path.isdir("raw") or os.path.exists("data.js"):
    OUT = "."
else:
    OUT = "."
RAW = os.path.join(OUT, "raw")
SKILLMAPS = os.path.join(OUT, "agents_skillmaps.json")
META = os.path.join(OUT, "agents_meta.json")

CLASS={"SCLSASSASIN":"Assassin","SCLSBERSRKR":"Berserker","SCLSBIOSCLPT":"Biosculptor","SCLSENGINEER":"Engineer","SCLSEXPLORE":"Explorer","SCLSPALADIN":"Paladin","SCLSSENTINL":"Sentinel","SCLSSNIPER":"Sniper","SCLSTRAPMSTR":"Trapmaster"}
POWER={"PTYCHAOS":"Chaos","PTYDARK":"Dark","PTYLIFE":"Life","PTYTIME":"Time","PTYHONOR":"Honor","PTYFORCE":"Force","PTYSHIELD":"Shield","PTYSPACE":"Space","PTYBRAIN":"Brain","PTYTIMEMIN":"Time"}

_lock = threading.Lock()
# live progress the app polls via /api/progress
_state = {"running": False, "msg": "", "pct": 0, "done": False, "ok": None, "error": None, "summary": None}

def set_msg(m, pct=None):
    _state["msg"] = m
    if pct is not None:
        _state["pct"] = pct
    print("  " + m)

def token_valid(tok):
    try:
        p = tok.split(".")[1]; p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p)).get("exp", 0) > time.time()
    except Exception:
        return False

def load_cached_token():
    try:
        t = open(TOKEN_CACHE, encoding="utf-8").read().strip()
        return t if t and token_valid(t) else ""
    except Exception:
        return ""

def save_token(t):
    try:
        open(TOKEN_CACHE, "w", encoding="utf-8").write(t.strip())
    except Exception:
        pass

def fetch(url, token):
    req = urllib.request.Request(url, headers={"Authorization":"Bearer "+token,
        "Accept":"application/json","x-app-origin":"Web","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def collect_available(token, path=LIST_PATH, label="available"):
    ids, meta, page = set(), {}, 1
    sep = "&" if "?" in path else "?"
    while True:
        data = fetch(f"{BASE}{path}{sep}page={page}", token)
        rows = data.get("data", data if isinstance(data, list) else [])
        for row in rows:
            gu = row.get("game_unit", row)
            if gu.get("id") is not None:
                ids.add(str(gu["id"])); meta[str(gu["id"])] = gu
        set_msg(f"Reading {label} list — page {page} ({len(ids)} agents so far)", pct=min(30, 5 + page * 3))
        if not data.get("has_more") or not rows:
            break
        page += 1; time.sleep(DELAY_SEC)
    return ids, meta

def rebuild(token, full=False):
    set_msg("Contacting the game…", pct=3)
    avail, m1 = collect_available(token, LIST_PATH, "available")
    other, m2 = collect_available(token, OTHER_PATH, "other/contracted")
    roster = avail | other
    set_msg(f"{len(avail)} available, {len(other)} other. Checking cache…", pct=32)
    skillmaps = json.load(open(SKILLMAPS, encoding="utf-8")) if os.path.exists(SKILLMAPS) else {}
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    meta.update(m1); meta.update(m2)
    os.makedirs(RAW, exist_ok=True)

    # full=True re-downloads EVERY agent's skill-map (a hard reset; rarely needed).
    #
    # A skill's VALUE is the same on every agent that has it — when the game rebalances
    # a skill, all agents get the new number (only the skill's NAME can differ by
    # generation). So to read CURRENT values we don't need the whole roster: on a normal
    # refresh we (a) download any brand-new agents, and (b) re-pull a small "covering
    # set" of agents that together contain every skill, so each skill is read fresh from
    # the live game. The Skills Catalogue is then built from these freshly-pulled agents,
    # which keeps it in step with balance changes without the slow full refresh.
    if full:
        missing = list(roster)
    else:
        missing = [a for a in roster if a not in skillmaps]
        # greedy set-cover over cached agents that are STILL in the roster: the fewest
        # agents whose skills span every skill, so we re-pull just those to read values.
        agent_skills = {}
        for aid in roster:
            sm = skillmaps.get(aid)
            if not sm: continue
            s = set()
            for sc in sm:
                for col in sc["skills"]:
                    for sk in col: s.add(sk["skill_name"])
            agent_skills[aid] = s
        remaining = set().union(*agent_skills.values()) if agent_skills else set()
        pool = dict(agent_skills)
        while remaining and pool:
            best = max(pool, key=lambda a: len(pool[a] & remaining))
            gain = pool[best] & remaining
            if not gain: break
            remaining -= gain
            if best not in missing:
                missing.append(best)          # re-pull this agent to read current values
            pool.pop(best)
    fresh = set(missing) if not full else set(roster)   # agents read live THIS run
    if missing:
        verb = "Re-downloading ALL agents (patch refresh)" if full else "Refreshing agents + skill values"
        for i, aid in enumerate(missing, 1):
            try:
                sm = fetch(f"{BASE}{SKILL_PATH.format(id=aid)}", token)
                skillmaps[aid] = sm
                json.dump(sm, open(os.path.join(RAW, f"{aid}.json"), "w", encoding="utf-8"))
            except Exception as ex:
                print("  skip", aid, ex)
            if i % 3 == 0 or i == len(missing):
                set_msg(f"{verb}… {i}/{len(missing)}", pct=32 + int(55 * i / len(missing)))
            time.sleep(DELAY_SEC)
    set_msg("Saving and rebuilding the list…", pct=90)
    json.dump(skillmaps, open(SKILLMAPS, "w", encoding="utf-8"))
    json.dump(meta, open(META, "w", encoding="utf-8"))

    agents, allskills = [], set()
    for aid, sm in skillmaps.items():
        if not sm: continue
        md = meta.get(str(aid), {})
        classes, elems, cols = [], [], []
        for sc in sm:
            cls = CLASS.get(sc.get("skill_class")); classes.append(cls)
            ptiles = sc.get("power_tiles", [])
            colidxs = sorted({sk["skill_column_index"] for col in sc["skills"] for sk in col})
            for k, ci in enumerate(colidxs):
                pw = POWER.get(ptiles[k].get("power_type"), "") if k < len(ptiles) else ""
                if pw and pw not in elems: elems.append(pw)
            bycol = {}
            for col in sc["skills"]:
                for sk in col:
                    bycol.setdefault(sk["skill_column_index"], {})[sk["skill_index"]] = (sk["skill_name"], sk["skill_points_cost"])
                    allskills.add(sk["skill_name"])
            for ci in sorted(bycol):
                items = [bycol[ci][d] for d in sorted(bycol[ci])]
                cols.append([cls, ci, items])
        agents.append({"n": md.get("friendly_name", str(aid)), "id": int(aid),
                       "c": classes, "e": elems, "a": 1 if str(aid) in avail else 0, "t": cols})
    # skill catalogue: per-skill class(es), trigger type, effect text, cheapest cost
    def _trig(txt):
        for t in ("On Round Start","On Shard Collect","On KO","On Survive"):
            if t in txt: return t
        if "Boost" in txt: return "Boost"
        if "Temporary" in txt or "Temp" in txt or "for " in txt: return "Temporary"
        return "Passive"
    # A skill's value is the same on every agent (a rebalance changes it everywhere).
    # The cache can briefly hold BOTH numbers only because agents pulled before a patch
    # still carry the old value until they're re-pulled. So we take each skill's value
    # from the agents pulled fresh THIS run (authoritative/current), and only fall back
    # to the wider cache for a skill no fresh agent happened to include. `multi` flags
    # the rare case where even the fresh reads disagree.
    def _collapse(vals):                      # vals: effect strings, most-common first
        if len(vals) == 1: return vals[0]
        pref = vals[0].split(":")[0]
        if all(v.split(":")[0] == pref for v in vals):   # share a trigger prefix -> show once
            return pref + ": " + " / ".join(v.split(":", 1)[1].strip() for v in vals)
        return " / ".join(vals)
    catx = {}
    for aid, sm in skillmaps.items():
        if not sm: continue
        is_fresh = aid in fresh
        for sc in sm:
            cls = CLASS.get(sc.get("skill_class"), "?")
            for col in sc["skills"]:
                for sk in col:
                    nm = sk["skill_name"]; cost = sk["skill_points_cost"]
                    eff = " | ".join(re.sub(r"<[^>]+>", "", e.get("name","")).strip() for e in sk.get("effects", []))
                    e = catx.setdefault(nm, {"cls": set(), "vals": {}, "fresh": {}, "sp": cost})
                    e["cls"].add(cls); e["sp"] = min(e["sp"], cost)
                    if eff:
                        e["vals"][eff] = e["vals"].get(eff, 0) + 1
                        if is_fresh: e["fresh"][eff] = e["fresh"].get(eff, 0) + 1
    catalogue = []
    for nm, v in sorted(catx.items()):
        src = v["fresh"] or v["vals"]         # prefer values read live this run
        vals = [t for t, _ in sorted(src.items(), key=lambda x: -x[1])]
        catalogue.append({"n": nm, "c": sorted(v["cls"]), "tr": _trig(vals[0]) if vals else "Passive",
                          "e": _collapse(vals), "sp": v["sp"], "multi": len(vals) > 1})

    data = {"date": time.strftime("updated %Y-%m-%d %H:%M"), "agents": agents, "skills": sorted(allskills), "catalogue": catalogue}
    datajs = "window.CHAOS=" + json.dumps(data, separators=(',', ':')) + ";"
    open(os.path.join(OUT, "data.js"), "w", encoding="utf-8").write(datajs)
    if OUT != ".":
        open("data.js", "w", encoding="utf-8").write(datajs)
    for tp in ("chaos_tool.html", os.path.join(HERE, "chaos_tool.html")):
        if os.path.exists(tp):
            share = open(tp, encoding="utf-8").read().replace('<script src="data.js"></script>', "<script>\n"+datajs+"\n</script>")
            open("Chaos Agents Build Finder.html", "w", encoding="utf-8").write(share)
            break
    return {"agents": len(agents), "available": len(avail), "other": len(other), "date": data["date"]}

def run_refresh(token, full=False):
    _state.update(running=True, done=False, ok=None, error=None, summary=None, msg="Starting…", pct=1)
    try:
        summary = rebuild(token, full)
        save_token(token)
        _state.update(running=False, done=True, ok=True, summary=summary,
                      msg=f"Done — {summary['available']} available.", pct=100)
    except urllib.error.HTTPError as e:
        code = getattr(e, "code", "?")
        _state.update(running=False, done=True, ok=False, pct=0, msg="Failed.",
                      error=("Token expired — grab a fresh one with the bookmarklet." if code == 401 else f"Game API error {code}."))
    except Exception as e:
        _state.update(running=False, done=True, ok=False, pct=0, msg="Failed.", error=f"Refresh failed: {e}")
    finally:
        if _lock.locked():
            _lock.release()


class Handler(SimpleHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        if self.path.split("?")[0].endswith("data.js"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/status":
            tok = load_cached_token()
            date = ""
            try:
                f = os.path.join(OUT, "data.js") if os.path.exists(os.path.join(OUT, "data.js")) else "data.js"
                raw = open(f, encoding="utf-8").read()
                date = json.loads(raw[raw.find("{"):raw.rfind("}")+1]).get("date", "")
            except Exception:
                pass
            return self._json(200, {"hasToken": bool(tok), "date": date})
        if p == "/api/progress":
            return self._json(200, _state)
        if self.path in ("/", ""):
            self.path = "/chaos_tool.html"
        # friendly message if the app file isn't sitting next to this script (usually
        # means the zip wasn't fully extracted / it was launched from inside the zip)
        if self.path.split("?")[0] == "/chaos_tool.html" and not os.path.exists(os.path.join(HERE, "chaos_tool.html")):
            msg = ("<html><body style='font-family:sans-serif;max-width:640px;margin:60px auto;color:#222;line-height:1.6'>"
                   "<h2>Almost there — the app file is missing</h2>"
                   "<p><b>chaos_tool.html</b> isn't in the same folder as the launcher. This usually means the "
                   "zip wasn't fully extracted.</p>"
                   "<p><b>Fix:</b> right-click the zip &rarr; <b>Extract All</b> to a real folder, open that folder, "
                   "and run <b>Start Chaos Finder.bat</b> from there (not from inside the zip).</p>"
                   "<p>Or, to just browse builds with nothing to install, double-click "
                   "<b>Chaos Agents Build Finder.html</b> instead.</p></body></html>")
            body = msg.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/refresh":
            return self._json(404, {"ok": False, "error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        token = (body.get("token") or "").strip() or load_cached_token()
        if not token:
            return self._json(200, {"ok": False, "error": "No token. Paste your login token (use the Copy Chaos token bookmarklet)."})
        if not token_valid(token):
            return self._json(200, {"ok": False, "error": "That token looks expired — grab a fresh one with the bookmarklet."})
        if not _lock.acquire(blocking=False):
            return self._json(200, {"ok": False, "error": "A refresh is already running."})
        full = bool(body.get("full"))
        threading.Thread(target=run_refresh, args=(token, full), daemon=True).start()
        return self._json(200, {"ok": True, "started": True})

    def log_message(self, *a):
        pass


def main():
    url = f"http://localhost:{PORT}/"
    print("Chaos Finder is running.")
    print(f"  Open:  {url}")
    print("  (Leave this window open. Close it to stop.)")
    try:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
