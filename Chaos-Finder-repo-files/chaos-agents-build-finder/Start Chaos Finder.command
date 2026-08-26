#!/bin/bash
# Mac launcher for the live-refresh version of Chaos Finder.
# Double-click to run. (First time: right-click -> Open to get past the
# "unidentified developer" warning.)

cd "$(dirname "$0")"

pause() { echo; read -n 1 -s -r -p "Press any key to close..."; echo; }

# --- make sure the files were actually extracted together ---
if [ ! -f "chaos_app.py" ] || [ ! -f "chaos_tool.html" ]; then
  echo
  echo "  The Chaos Finder files aren't all here."
  echo
  echo "  Please unzip the whole download into one folder, then run this from"
  echo "  that folder. Or, to just browse builds with nothing to install,"
  echo "  double-click \"Chaos Agents Build Finder.html\"."
  pause
  exit 1
fi

# --- find Python 3 ---
PY=""
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
fi
if [ -z "$PY" ]; then
  echo
  echo "  Python 3 isn't installed, so the live-refresh version can't start."
  echo
  echo "  To just browse builds (no install needed), double-click"
  echo "  \"Chaos Agents Build Finder.html\" instead."
  echo
  echo "  To use the Refresh button, install Python 3 from"
  echo "  https://www.python.org/downloads/  then run this again."
  pause
  exit 1
fi

echo "Starting Chaos Finder... your browser will open in a moment."
"$PY" chaos_app.py
echo
echo "Chaos Finder stopped. You can close this window."
pause
