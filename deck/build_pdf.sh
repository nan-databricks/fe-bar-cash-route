#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [[ ! -x "$CHROME" ]]; then
  echo "Google Chrome is required to print deck.html to PDF" >&2
  exit 1
fi
# deck.html is generated alongside deck.md; regenerate if missing
if [[ ! -f deck.html ]]; then
  echo "deck.html missing — copy from last render or re-run the HTML generator"
  exit 1
fi
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$(pwd)/deck.pdf" "file://$(pwd)/deck.html"
ls -la "$(pwd)/deck.pdf"
