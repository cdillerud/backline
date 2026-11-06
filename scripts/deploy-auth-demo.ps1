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
$branch = 'release/backline-v0.6-show-first-rc6'
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
  # Fail closed when the Fly API is unreachable. A missing/failed secret list
  # must NEVER trigger an unsolicited password replacement on an existing demo.
  # Configure BACKLINE_DEMO_PASSWORD separately and securely, before deployment.
  $secretResult = @(flyctl secrets list --app $app 2>&1)
  if ($LASTEXITCODE -ne 0) {
    throw 'Cannot verify existing Fly secrets. Check DNS/Fly API connectivity and retry; no secret was changed.'
  }
  $secretLines = @($secretResult | ForEach-Object { [string]$_ })
  $demoSecret = @($secretLines | Where-Object { $_ -match 'BACKLINE_DEMO_PASSWORD' })
  if ($demoSecret.Count -ne 1) {
    throw 'Deployed BACKLINE_DEMO_PASSWORD was not found. Set it securely in Fly first; refusing to prompt or overwrite.'
  }
  if ($demoSecret[0] -notmatch 'Deployed') {
    throw 'BACKLINE_DEMO_PASSWORD is not deployed yet. Activate the existing staged secret before deploying.'
  }
  # Prevent automatic redundant machines with independent, unreplicated SQLite files.
  flyctl deploy . --app $app --config $config --ha=false --build-arg "BACKLINE_BUILD_SHA=$head"
  if ($LASTEXITCODE -ne 0) { throw 'Fly deployment failed' }
  flyctl status --app $app
  $health = Invoke-WebRequest "https://$app.fly.dev/api/health" -SkipHttpErrorCheck -TimeoutSec 20
  if ($health.StatusCode -ne 200) { throw "Health check failed: $($health.StatusCode)" }
  try { $healthBody = $health.Content | ConvertFrom-Json -ErrorAction Stop }
  catch { throw 'Health check returned invalid JSON; cannot certify release SHA.' }
  if ($healthBody.status -ne 'ok') { throw "Unhealthy application status: $($healthBody.status)" }
  if ($healthBody.build_sha -ne $head) { throw "Build SHA mismatch: expected $head; observed $($healthBody.build_sha)" }
  $private = Invoke-WebRequest "https://$app.fly.dev/api/bands" -SkipHttpErrorCheck -TimeoutSec 20
  if ($private.StatusCode -ne 401) { throw "Private API should return 401 unsigned; got $($private.StatusCode)" }
  Write-Host 'PASS: isolated demo healthy; signed-out private API denied. Perform signed-in visual acceptance next.'
}
finally { Pop-Location }
