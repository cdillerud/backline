# Run from the Backline repository root on Windows PowerShell 7.
# Deploys ONLY the separate disposable visual preview app. Never touches 'backline'.
$ErrorActionPreference = 'Stop'
$App = 'backline-visual-preview'
if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)) {
    throw 'Install flyctl first: https://fly.io/docs/flyctl/install/'
}
if (-not (Test-Path './fly.preview.toml')) {
    throw 'Run this from the Backline repository root.'
}
$branch = (git branch --show-current).Trim()
if ($branch -ne 'integration/backline-v0-4-rc') {
    throw "Switch to integration/backline-v0-4-rc first (current: $branch)"
}
flyctl auth whoami | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Please authenticate with flyctl auth login.' }
$existing = @(flyctl apps list --json | ConvertFrom-Json | Where-Object { $_.Name -eq $App })
if ($LASTEXITCODE -ne 0) { throw 'Unable to list Fly applications.' }
if ($existing.Count -eq 0) {
    flyctl apps create $App
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create isolated preview app.' }
}
# Generate a fresh password locally. It is not committed, logged in Git, or stored in Backline.
$passwordBytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(30)
$password = [Convert]::ToBase64String($passwordBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$secrets = "BACKLINE_PREVIEW_USER=preview`nBACKLINE_PREVIEW_PASSWORD=$password`n"
$secrets | flyctl secrets import --app $App --stage | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Unable to stage preview credentials.' }
flyctl deploy --config ./fly.preview.toml --app $App
if ($LASTEXITCODE -ne 0) { throw 'Preview deploy failed; production is untouched.' }
flyctl status --app $App | Out-Host
Write-Host "Preview URL: https://$App.fly.dev"
Write-Host 'Preview username: preview'
Write-Host "Preview password: $password"
Write-Host 'Note: this is a disposable demo. Data resets on machine replacement.'
