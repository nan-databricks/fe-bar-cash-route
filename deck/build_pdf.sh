#!/usr/bin/env bash
# Builds deck/deck.pdf from the designed HTML deck (deck/slides.html).
# deck/deck.md holds the same content as plain text for reviewers.
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer --allow-file-access-from-files \
  --print-to-pdf="$PWD/deck.pdf" "file://$PWD/slides.html"
echo "wrote $PWD/deck.pdf"
