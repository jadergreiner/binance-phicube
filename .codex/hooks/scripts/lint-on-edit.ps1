#!/usr/bin/env pwsh
# lint-on-edit.ps1
# Hook PostToolUse — aplica lint automaticamente em .py e .md recém-editados.
# Recebe JSON do agente via stdin com informações da ferramenta invocada.

$input_json = $null
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw -and $raw.Trim() -ne "") {
        $input_json = $raw | ConvertFrom-Json -ErrorAction Stop
    }
} catch {
    exit 0  # stdin inválido ou vazio — não bloquear
}

if (-not $input_json) { exit 0 }

# Ferramentas que editam arquivos
$edit_tools = @("create_file", "replace_string_in_file", "multi_replace_string_in_file")
# VS Code envia tool_name e tool_input em snake_case no nível raiz
$tool_name = $input_json.tool_name

if ($tool_name -notin $edit_tools) { exit 0 }

# Extrair caminho do arquivo (tool_input usa camelCase interno do VS Code)
$file_path = $null

if ($input_json.tool_input.filePath) {
    $file_path = $input_json.tool_input.filePath
} elseif ($input_json.tool_input.replacements) {
    # multi_replace_string_in_file — usar primeiro arquivo
    $file_path = $input_json.tool_input.replacements[0].filePath
}

if (-not $file_path) { exit 0 }

# Normalizar para caminho relativo se possível
$repo_root = (Get-Location).Path
if ($file_path.StartsWith($repo_root)) {
    $file_path = $file_path.Substring($repo_root.Length).TrimStart('\', '/')
}

# Verificar se arquivo existe
if (-not (Test-Path $file_path)) { exit 0 }

$ext = [System.IO.Path]::GetExtension($file_path).ToLower()

# ── Python: ruff check --fix + ruff format ──────────────────────────────────
if ($ext -eq ".py") {
    Write-Host "🔍 lint-on-edit: $file_path"

    # 1. Lint com autocorreção
    $check = & ruff check --fix $file_path 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  ruff check: erros remanescentes (correção manual necessária):"
        Write-Host ($check | Out-String)
    } else {
        Write-Host "✅ ruff check OK"
    }

    # 2. Formatação
    $fmt = & ruff format $file_path 2>&1
    Write-Host "✅ ruff format: $fmt"

    exit 0
}

# ── Markdown: markdownlint se disponível, senão skip ────────────────────────
if ($ext -eq ".md") {
    Write-Host "🔍 lint-on-edit: $file_path"

    $has_mdlint = Get-Command "markdownlint" -ErrorAction SilentlyContinue
    if ($has_mdlint) {
        $md = & markdownlint $file_path 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  markdownlint: $md"
        } else {
            Write-Host "✅ markdownlint OK"
        }
    } else {
        Write-Host "ℹ️  markdownlint não instalado — pulando lint de .md"
        Write-Host "   Para instalar: npm install -g markdownlint-cli"
    }

    exit 0
}

exit 0
