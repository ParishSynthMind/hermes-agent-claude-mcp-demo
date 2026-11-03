import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_guard_config_is_locked_down():
    cfg = json.loads((ROOT / "config" / "guard-config.json").read_text())
    assert cfg["dryRun"] is True
    assert cfg["commentAllowlist"] == ["ParishSynthMind/hermes-agent-claude-mcp-demo"]
    assert cfg["maxCommentLength"] <= 2000


def test_hermes_example_uses_claude_and_never_borrows_logins():
    cfg = yaml.safe_load((ROOT / "config" / "hermes-mcp.example.yaml").read_text())
    assert cfg["model"]["provider"] == "anthropic"
    assert cfg["model"]["default"].startswith("claude-")
    assert cfg["auth"]["adopt_external_logins"] is False
    server = cfg["mcp_servers"]["guarded_github"]
    assert server["command"] == "node"
    assert "GITHUB_TOKEN" not in server["env"]


def test_run_script_restricts_hermes_to_the_mcp_toolset():
    script = (ROOT / "scripts" / "run_task.sh").read_text()
    assert "-t mcp-guarded_github" in script
    assert "gateway stop" in script  # no gateway keeps the key after a run


HOME_PATH = "/" + "Users/"  # split so this file does not match itself
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,}")


def test_no_secrets_or_home_paths_committed():
    skip = {".git", ".venv", "run", ".hermes-sandbox", "__pycache__", ".pytest_cache"}
    for p in ROOT.rglob("*"):
        if p.is_dir() or skip & set(p.relative_to(ROOT).parts) or p.suffix == ".png":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert not SECRET.search(text), f"secret-looking string in {p}"
        assert HOME_PATH not in text, f"personal path in {p}"
