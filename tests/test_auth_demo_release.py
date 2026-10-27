"""Prevent accidental reuse of production resources for the synthetic authenticated demo."""
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]

def test_authenticated_fly_app_isolated_from_production_and_visual_preview():
    prod=tomllib.loads((ROOT/"fly.toml").read_text())
    demo=tomllib.loads((ROOT/"fly.auth-demo.toml").read_text())
    assert demo["app"] not in {prod["app"],"backline-visual-preview"}
    assert demo["app"]=="backline-auth-demo"
    assert "mounts" not in demo, "Synthetic demo must never attach an existing volume"
    env=demo["env"]
    assert env["BACKLINE_ACCOUNTS_ENABLED"]=="1"
    assert env["BACKLINE_DEMO_ACCOUNTS"]=="1"
    assert env["BACKLINE_DEMO_SEED"]=="1"
    assert env["BACKLINE_PUBLIC_SHARING_ENABLED"]=="0"
    assert env["BACKLINE_DB"]=="/data/backline.db"
    for forbidden in ("BACKLINE_DEMO_PASSWORD","BACKLINE_PREVIEW_PASSWORD","BACKLINE_LOCAL_DEV"):
        assert forbidden not in env
    assert demo["build"]["dockerfile"]=="Dockerfile"
    assert demo["http_service"]["force_https"] is True
