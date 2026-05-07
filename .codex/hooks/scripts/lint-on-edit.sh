#!/usr/bin/env bash
# lint-on-edit.sh
# Hook PostToolUse — aplica lint automaticamente em .py e .md recém-editados.
# Recebe JSON do agente via stdin com informações da ferramenta invocada.

set -euo pipefail

RAW=$(cat)
if [ -z "$RAW" ]; then exit 0; fi

TOOL_NAME=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('toolName',''))" 2>/dev/null || true)

case "$TOOL_NAME" in
  create_file|replace_string_in_file|multi_replace_string_in_file) ;;
  *) exit 0 ;;
esac

# Extrair filePath
FILE_PATH=$(echo "$RAW" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('toolInput', {})
if 'filePath' in ti:
    print(ti['filePath'])
elif 'replacements' in ti and ti['replacements']:
    print(ti['replacements'][0].get('filePath',''))
" 2>/dev/null || true)

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then exit 0; fi

EXT="${FILE_PATH##*.}"

# ── Python: ruff check --fix + ruff format ──────────────────────────────────
if [ "$EXT" = "py" ]; then
    echo "🔍 lint-on-edit: $FILE_PATH"
    ruff check --fix "$FILE_PATH" && echo "✅ ruff check OK" || echo "⚠️  ruff check: erros remanescentes"
    ruff format "$FILE_PATH" && echo "✅ ruff format OK"
    exit 0
fi

# ── Markdown: markdownlint se disponível ────────────────────────────────────
if [ "$EXT" = "md" ]; then
    echo "🔍 lint-on-edit: $FILE_PATH"
    if command -v markdownlint &>/dev/null; then
        markdownlint "$FILE_PATH" && echo "✅ markdownlint OK" || echo "⚠️  markdownlint: erros encontrados"
    else
        echo "ℹ️  markdownlint não instalado — pulando lint de .md"
        echo "   Para instalar: npm install -g markdownlint-cli"
    fi
    exit 0
fi

exit 0
