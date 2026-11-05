"""Static guardrails for the isolated Fly demo release script.

These tests never contact Fly.io and do not require any credentials.
"""
from pathlib import Path


def test_auth_demo_deploy_remains_isolated_and_pinned():
    script = Path("scripts/deploy-auth-demo.ps1").read_text(encoding="utf-8")
    assert "$app = 'backline-auth-demo'" in script
    # The same script is pinned to integration during development and to the
    # frozen RC branch during release, so never hard-code one source branch here.
    assert "$branch = '" in script
    assert "Wrong branch:" in script
    assert "Local HEAD differs from remote branch" in script
    assert "fly.auth-demo.toml" in script
    assert "--ha=false" in script
    assert '--build-arg "BACKLINE_BUILD_SHA=$head"' in script
    assert "$healthBody.build_sha -ne $head" in script
    assert "$private.StatusCode -ne 401" in script
    assert "No completed passing Backline CI" in script


def test_existing_demo_password_is_never_silently_replaced():
    script = Path("scripts/deploy-auth-demo.ps1").read_text(encoding="utf-8")
    assert "flyctl secrets list --app $app" in script
    assert "if ($LASTEXITCODE -ne 0)" in script
    assert "BACKLINE_DEMO_PASSWORD" in script
    assert "not deployed yet" in script
    assert "Cannot verify existing Fly secrets" in script
    assert "Read-Host" not in script
    assert "flyctl secrets import" not in script
    assert "flyctl secrets set" not in script
    assert "flyctl secrets sync" not in script
