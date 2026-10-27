#requires -Version 7.0
<#
.SYNOPSIS
Preflight and (on explicit -Deploy) release the synthetic Backline auth demo.
Does not modify production or backline-visual-preview. Secret is set separately
in the Fly dashboard before running with -Deploy.
#>
[CmdletBinding()]
param([switch]$Deploy, [switch]$CreateApp)
$ErrorActionPreference = 'Stop'
$repo = 'cdillerud/backline'
$app = 'backline-auth-demo'
$branch = 'integration/backline-v0-4-rc'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$config = Join-Path $RepoRoot 'fly.auth-demo.toml'
if (!(Test-Path $config)) { throw 'Missing fly.auth-demo.toml' }
foreach ($exe in @('git','gh','flyctl')) {
  if (!(Get-Command $exe -ErrorAction SilentlyContinue)) { throw "Missing required command: $exe" }
}
Push-Location $RepoRoot
try {
  $current = (git branch --show-current).Trim()
  if ($current -ne $branch) { throw "Wrong branch: $current (expected $branch)" }
  # Untracked local preview config/files are intentionally preserved; only tracked changes block release.
  $trackedChanges = @(git status --porcelain --untracked-files=no | Where-Object { $_ -and $_.Trim() })
  if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect tracked working tree changes.' }
  if ($trackedChanges.Count -ne 0) { throw 'Tracked files contain local modifications. Commit or restore them before release.' }
  $head = (git rev-parse HEAD).Trim()
  git fetch origin $branch | Out-Null
  $remote = (git rev-parse "origin/$branch").Trim()
  if ($head -ne $remote) { throw 'Local HEAD differs from remote branch. Pull and re-run preflight.' }
  $runsJson = gh run list --repo $repo --workflow ci.yml --commit $head --limit 15 --json headSha,status,conclusion,databaseId
  if ($LASTEXITCODE -ne 0) { throw 'GitHub CI verification failed' }
  $runs = @($runsJson | ConvertFrom-Json)
  $passing = @($runs | Where-Object { $_.headSha -eq $head -and $_.status -eq 'completed' -and $_.conclusion -eq 'success' })
  if ($passing.Count -eq 0) { throw "No completed passing Backline CI for $head" }
  $configText = Get-Content $config -Raw
  if ($configText -notmatch "(?m)^app\s*=\s*'backline-auth-demo'\s*$") { throw 'Demo config targets unexpected app' }
  if ($configText -match "(?m)^\s*\[\[mounts\]\]") { throw 'Refusing a demo config with volume mounts' }
  Write-Host "PASS: branch=$branch; commit=$head; CI=$($passing[0].databaseId)"
  if (!$Deploy) { Write-Host 'Preflight only. Set demo password through Fly secrets and run -Deploy after reviewing.'; return }
  $listJson = flyctl apps list --json
  if ($LASTEXITCODE -ne 0) { throw 'Cannot verify Fly apps' }
  $apps = @($listJson | ConvertFrom-Json)
  $exists = @($apps | Where-Object { $_.Name -eq $app -or $_.name -eq $app }).Count -gt 0
  if (!$exists) {
    if (!$CreateApp) { throw "App $app does not exist. Re-run with -Deploy -CreateApp if intended." }
    flyctl apps create $app
    if ($LASTEXITCODE -ne 0) { throw 'Fly app creation failed' }
    throw "Created $app. Configure BACKLINE_DEMO_PASSWORD securely in Fly dashboard, then rerun with -Deploy."
  }
  # Newly created Fly apps have no machines. Dashboard-staged secrets can remain
  # invisible to the CLI until imported/synced; do not call 'secrets deploy' yet.
  $secretsText = flyctl secrets list --app $app
  if ($LASTEXITCODE -ne 0) { throw 'Unable to list demo application secrets' }
  if ($secretsText -notmatch 'BACKLINE_DEMO_PASSWORD') {
    Write-Host 'Password not visible in Fly CLI; syncing dashboard-staged secrets.'
    flyctl secrets sync --stage --app $app
    if ($LASTEXITCODE -ne 0) { Write-Host 'Staged secret sync unavailable before first machine; secure import will be offered.' }
    $secretsText = flyctl secrets list --app $app
    if ($LASTEXITCODE -ne 0) { $secretsText = '' }
  }
  if ($secretsText -notmatch 'BACKLINE_DEMO_PASSWORD') {
    Write-Host 'Enter the existing demo password securely. Input is hidden and is not passed as a command-line argument.'
    $secure = Read-Host 'BACKLINE_DEMO_PASSWORD' -AsSecureString
    $plain = ConvertFrom-SecureString -SecureString $secure -AsPlainText
    if ($plain.Length -lt 12) { throw 'Demo password must be at least 12 characters' }
    try {
      "BACKLINE_DEMO_PASSWORD=$plain" | flyctl secrets import --stage --app $app
      if ($LASTEXITCODE -ne 0) { throw 'Fly staged secret import failed' }
    } finally {
      Remove-Variable plain,secure -ErrorAction SilentlyContinue
    }
    # A staged secret is deliberately NOT listed as active before a first machine
    # exists. Successful import is the confirmation; the server also fails closed
    # at startup if BACKLINE_DEMO_PASSWORD is missing.
    Write-Host 'Demo password staged successfully. First deployment will activate it.'
  }
  flyctl deploy . --app $app --config $config
  if ($LASTEXITCODE -ne 0) { throw 'Fly deployment failed' }
  flyctl status --app $app
  $health = Invoke-WebRequest "https://$app.fly.dev/api/health" -SkipHttpErrorCheck -TimeoutSec 20
  if ($health.StatusCode -ne 200) { throw "Health check failed: $($health.StatusCode)" }
  $private = Invoke-WebRequest "https://$app.fly.dev/api/bands" -SkipHttpErrorCheck -TimeoutSec 20
  if ($private.StatusCode -ne 401) { throw "Private API should return 401 unsigned; got $($private.StatusCode)" }
  Write-Host 'PASS: isolated demo healthy; signed-out private API denied. Perform signed-in visual acceptance next.'
}
finally { Pop-Location }
