param(
  [ValidateSet("changed", "all")]
  [string]$Mode = "changed",
  [string]$Path
)

$ErrorActionPreference = "Stop"

function Test-Markdownlint {
  $cmd = Get-Command markdownlint -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "markdownlint não encontrado no PATH."
  }
}

function Get-ChangedMarkdownFiles {
  $files = git diff --name-only HEAD | Where-Object { $_ -match '\.md$' }
  return @($files)
}

function Invoke-MarkdownlintFile([string]$filePath) {
  if (-not (Test-Path $filePath)) {
    Write-Warning "Arquivo não encontrado: $filePath"
    return
  }
  markdownlint $filePath
}

Test-Markdownlint

if ($Path) {
  Invoke-MarkdownlintFile $Path
  exit $LASTEXITCODE
}

if ($Mode -eq "all") {
  markdownlint "**/*.md"
  exit $LASTEXITCODE
}

$changed = Get-ChangedMarkdownFiles
if ($changed.Count -eq 0) {
  Write-Output "Nenhum arquivo .md alterado desde HEAD."
  exit 0
}

$exitCode = 0
foreach ($file in $changed) {
  Write-Output "Lint: $file"
  markdownlint $file
  if ($LASTEXITCODE -ne 0) {
    $exitCode = $LASTEXITCODE
  }
}

exit $exitCode

