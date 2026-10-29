#!/usr/bin/env bash
# Render deck/deck.md -> deck/deck.pdf. Always rebuilds from deck.md, so re-run after filling placeholders.
#   1. mermaid-cli pre-renders mermaid blocks to SVG (Marp has no native mermaid); on failure the diagram stays a code block.
#   2. Marp renders the PDF. If Marp's PDF step fails, Marp renders HTML and headless Chrome prints it.
# Usage: bash deck/build_pdf.sh
set -euo pipefail
cd "$(dirname "$0")"

BUILD=.build
rm -rf "$BUILD" && mkdir -p "$BUILD"
echo '{ "args": ["--no-sandbox"] }' > "$BUILD/puppeteer.json"

if npx -y @mermaid-js/mermaid-cli@11 -i deck.md -o "$BUILD/deck.md" -e svg -b transparent -p "$BUILD/puppeteer.json" -q; then
  sed -i.bak 's#\.\./brand/#../../brand/#g' "$BUILD/deck.md" && rm -f "$BUILD/deck.md.bak"
  SRC="$BUILD/deck.md"
else
  echo "mermaid-cli failed; the architecture diagram will render as a code block" >&2
  SRC=deck.md
fi

MARP="npx -y @marp-team/marp-cli@4"
if ! $MARP "$SRC" --pdf --allow-local-files -o deck.pdf; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  echo "Marp PDF failed; falling back to Marp HTML + headless Chrome" >&2
  $MARP "$SRC" --html --allow-local-files -o "$BUILD/deck.html"
  "$CHROME" --headless --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$(pwd)/deck.pdf" "file://$(pwd)/$BUILD/deck.html"
fi

rm -rf "$BUILD"
echo "Built $(pwd)/deck.pdf"
