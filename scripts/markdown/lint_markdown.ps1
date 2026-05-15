param(
  [ValidateSet("changed", "all")]
  [string]$Mode = "changed",
  [string]$Path,
  [string]$OpenSpecChange
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

function Invoke-OpenSpecValidate([string]$changeId) {
  if (-not $changeId) {
    return
  }
  $cmd = Get-Command openspec -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "openspec não encontrado no PATH."
  }
  Write-Output "OpenSpec validate: $changeId"
  openspec validate $changeId
}

Test-Markdownlint

if ($Path) {
  Invoke-MarkdownlintFile $Path
  if ($LASTEXITCODE -eq 0) {
    Invoke-OpenSpecValidate $OpenSpecChange
  }
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

if ($exitCode -eq 0) {
  Invoke-OpenSpecValidate $OpenSpecChange
  if ($LASTEXITCODE -ne 0) {
    $exitCode = $LASTEXITCODE
  }
}

exit $exitCode
