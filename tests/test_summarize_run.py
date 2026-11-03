import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import summarize_run as sr  # noqa: E402

T = ROOT / "transcripts"


def test_real_run1_calls_list_issues_and_answers():
    s = sr.summarize(sr.load_events(T / "run1-summarise-issues.jsonl"))
    assert s["exit_code"] == 0
    mcp = [sr.short_tool(c["name"]) for c in s["calls"] if c["mcp"]]
    assert mcp == ["list_issues"]
    for n in ("#1", "#2", "#3"):
        assert n in s["answer"]


def test_real_run3_refusal_and_dry_run_are_in_the_audit_log():
    s = sr.summarize(sr.load_events(T / "run3-write-attempts.jsonl"))
    audit = sr.load_audit(T / "audit.jsonl", since_ms=s["started_ms"], until_ms=s["ended_ms"])
    assert {r["status"] for r in audit} == {"refused", "dry_run"}
    refused = [r for r in audit if r["status"] == "refused"][0]
    assert refused["args"]["owner"] == "modelcontextprotocol"
    assert sr.check(s, audit, ["add_issue_comment"], ["refused", "dry_run"]) == []
    # nothing merge-like was ever called
    assert not any("merge" in c["name"] for c in s["calls"])


def test_audit_is_filtered_to_the_run_window():
    s = sr.summarize(sr.load_events(T / "run1-summarise-issues.jsonl"))
    all_rows = sr.load_audit(T / "audit.jsonl")
    run_rows = sr.load_audit(T / "audit.jsonl", since_ms=s["started_ms"], until_ms=s["ended_ms"])
    assert len(run_rows) == 1 < len(all_rows)
    assert run_rows[0]["tool"] == "list_issues"


def test_check_reports_missing_tool_status_and_bad_exit():
    s = {"exit_code": 1, "error": "No Anthropic credentials found", "calls": []}
    problems = sr.check(s, [], ["get_issue"], ["refused"])
    assert len(problems) == 3
    assert "exit code 1" in problems[0]


def test_unfinished_transcript_is_an_error(tmp_path):
    p = tmp_path / "cut.jsonl"
    p.write_text(json.dumps({"type": "system", "subtype": "init", "timestamp": 1}) + "\n")
    with pytest.raises(ValueError, match="did not finish"):
        sr.summarize(sr.load_events(p))


def test_bad_json_line_names_the_line(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"type": "system"}\nnot json\n')
    with pytest.raises(ValueError, match=":2:"):
        sr.load_events(p)


def test_cli_exit_codes(tmp_path):
    out = tmp_path / "r.md"
    ok = sr.main([str(T / "run3-write-attempts.jsonl"), "--audit", str(T / "audit.jsonl"),
                  "--out", str(out), "--expect-status", "refused"])
    assert ok == 0 and "refused" in out.read_text()
    bad = sr.main([str(T / "run1-summarise-issues.jsonl"), "--audit", str(T / "audit.jsonl"),
                   "--out", str(out), "--expect-status", "refused"])
    assert bad == 1


def test_long_outputs_are_clipped():
    assert sr.clip("x" * 1000).endswith("[400 more characters]")
