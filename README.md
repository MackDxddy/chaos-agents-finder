# Chaos Agents - Agent Finder

A local tool for the Steam auto-battler **Chaos Agents**. Search every agent by the
skills you want (sorted by cost), browse a full skills catalogue, and save your
favorite agents. Everything runs **100% on your own computer**.

---

## Download

**Just want to browse builds?** Download the zip for your system, unzip it, and
double-click **`Chaos Agents Build Finder.html`**. No install, nothing else needed.

| System | Download |
|--------|----------|
| 🪟 **Windows** | [Chaos-Finder-Windows.zip](../../releases/latest/download/Chaos-Finder-Windows.zip) |
| 🍎 **Mac** | [Chaos-Finder-Mac.zip](../../releases/latest/download/Chaos-Finder-Mac.zip) |

> If the links above don't work yet, click the **Releases** link on the right-hand
> side of this page and download the zip from there.

---

## What you get

- **Build Finder** — add requirement rows (each row is a must-have; put two skills in
  one row to mean "either of these"). Matching agents are listed cheapest-first, with
  the SP cost and column-depth of each skill.
- **Skills Catalogue** — every skill in the game, filterable by class, trigger type,
  and cost.
- **Favorites** — star any agent; your list is remembered between sessions.
- **Live Refresh** (optional) — pull the latest agents and current skill values from
  your own game account with one click.

---

## Two ways to run it

**1. Browse only (no install).** Double-click **`Chaos Agents Build Finder.html`**.
It's a single self-contained file — it opens in your web browser and works offline.

**2. With the live "Refresh" button (needs Python).**

1. Install Python from <https://www.python.org/downloads/>
   - Windows: tick **"Add Python to PATH"** on the first install screen.
   - Mac: recent macOS doesn't include Python; install it from the same link.
2. Start it:
   - Windows: double-click **`Start Chaos Finder.bat`**
   - Mac: double-click **`Start Chaos Finder.command`** (first time: right-click → Open
     to get past the "unidentified developer" warning)
3. Set up the one-time token bookmarklet — see **`Copy Chaos Token (bookmarklet).txt`**.
4. On the game site (logged in), click the "Copy Chaos token" bookmarklet, paste the
   token into the box in the app, and click **Refresh**.

The refresh uses **your** game account, so availability reflects your own agents. Your
token is stored only on your computer and never leaves it.

---

## After a game balance patch

Just click **Refresh** normally. Because a skill's value is the same on every agent,
each refresh re-reads a small covering set of agents (about a dozen) that together
contain every skill, and updates the Skills Catalogue to the current numbers
automatically — no slow full re-download needed. The "Full refresh" checkbox is only a
rarely-needed hard reset.

---

## Privacy & safety

- Runs entirely locally. No account, no server, no uploads.
- Your login token is stored only on your machine (in a file the download never
  includes) and is used only to talk to the game's own API.
- The included data snapshot contains game/agent information only — no credentials.

---

## For developers

- `chaos_tool.html` — the app (UI + logic), loads its data from `data.js`.
- `chaos_app.py` — a tiny local server (Python standard library only) that serves the
  app and handles the Refresh (scrapes the game's authenticated API from your machine).
- `data.js` — the current data snapshot (`window.CHAOS = {...}`).
- The skill cache (`agents_skillmaps.json`, `agents_meta.json`) and your token
  (`.chaos_token`) are generated locally and are **not** committed — see `.gitignore`.
  They're bundled inside the release zips so the download works out of the box.
