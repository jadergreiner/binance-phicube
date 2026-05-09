param(
  [string]$Root = "."
)

$ErrorActionPreference = "Stop"

$markdownlintCmd = Get-Command markdownlint -ErrorAction SilentlyContinue
if (-not $markdownlintCmd) {
  throw "markdownlint não encontrado no PATH."
}

$resolvedRoot = (Resolve-Path $Root).Path
Write-Output "Watcher iniciado em: $resolvedRoot"
Write-Output "Observando *.md (Create/Change/Rename). Pressione Ctrl+C para sair."

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $resolvedRoot
$watcher.Filter = "*.md"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

$debounce = @{}
$debounceMs = 400

$action = {
  $path = $Event.SourceEventArgs.FullPath
  $name = $Event.SourceEventArgs.Name
  $now = Get-Date

  if ($debounce.ContainsKey($path)) {
    $delta = ($now - $debounce[$path]).TotalMilliseconds
    if ($delta -lt $debounceMs) {
      return
    }
  }
  $debounce[$path] = $now

  if (-not (Test-Path $path)) {
    return
  }

  Write-Output ""
  Write-Output "Lint: $name"
  markdownlint $path
  if ($LASTEXITCODE -eq 0) {
    Write-Output "OK: $name"
  }
}

$createdSub = Register-ObjectEvent $watcher Created -Action $action
$changedSub = Register-ObjectEvent $watcher Changed -Action $action
$renamedSub = Register-ObjectEvent $watcher Renamed -Action $action

try {
  while ($true) {
    Start-Sleep -Seconds 1
  }
}
finally {
  Unregister-Event -SourceIdentifier $createdSub.Name
  Unregister-Event -SourceIdentifier $changedSub.Name
  Unregister-Event -SourceIdentifier $renamedSub.Name
  $watcher.Dispose()
}

