#!/usr/bin/env python3
"""Turn a Hermes `--format stream-json` transcript (plus the guard's audit log)
into a readable Markdown transcript, and optionally check what happened.

Usage:
  python3 scripts/summarize_run.py RUN.jsonl [--audit run/audit.jsonl] [--title "..."]
      [--expect-tool NAME ...] [--expect-status STATUS ...] [--out FILE.md]

Exit code 1 if any --expect-* check fails, so it can gate a demo script.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MCP_PREFIX = "mcp__guarded_github__"
CLIP = 600


def load_events(path: Path) -> list[dict]:
    events = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{n}: not valid JSON ({exc.msg})") from None
    return events


def load_audit(path: Path | None, since_ms: int | None = None, until_ms: int | None = None) -> list[dict]:
    if not path or not path.exists():
        return []
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if since_ms is not None or until_ms is not None:
        since_ms = since_ms or 0
        from datetime import datetime
        def ms(row):
            return int(datetime.fromisoformat(row["ts"].replace("Z", "+00:00")).timestamp() * 1000)
        rows = [r for r in rows if ms(r) >= since_ms and (until_ms is None or ms(r) <= until_ms)]
    return rows


def short_tool(name: str) -> str:
    return name[len(MCP_PREFIX):] if name.startswith(MCP_PREFIX) else name


def summarize(events: list[dict]) -> dict:
    calls, results, final = [], {}, None
    for ev in events:
        kind = ev.get("type")
        if kind == "tool_use":
            calls.append({"id": ev.get("tool_call_id"), "name": ev.get("name", ""), "input": ev.get("input", {})})
        elif kind == "tool_result":
            results[ev.get("tool_call_id")] = ev.get("output", "")
        elif kind == "result":
            final = ev
    for call in calls:
        call["output"] = results.get(call["id"], "")
        call["mcp"] = call["name"].startswith(MCP_PREFIX)
    if final is None:
        raise ValueError("transcript has no final 'result' event (run did not finish)")
    start = next((ev.get("timestamp") for ev in events if ev.get("type") == "system"), None)
    return {
        "calls": calls,
        "answer": final.get("text", ""),
        "exit_code": final.get("exit_code"),
        "error": final.get("error"),
        "tokens": final.get("tokens", {}),
        "duration_ms": final.get("duration_ms"),
        "started_ms": start,
        "ended_ms": final.get("timestamp"),
    }


def clip(text: str, limit: int = CLIP) -> str:
    text = text if isinstance(text, str) else json.dumps(text)
    return text if len(text) <= limit else text[:limit] + f" ... [{len(text) - limit} more characters]"


def to_markdown(title: str, prompt: str | None, s: dict, audit: list[dict]) -> str:
    out = [f"# {title}", ""]
    if prompt:
        out += ["**Prompt:**", "", "> " + prompt.replace("\n", "\n> "), ""]
    out += ["## Tool calls, in order", ""]
    for i, c in enumerate(s["calls"], 1):
        label = short_tool(c["name"]) + (" (MCP)" if c["mcp"] else " (Hermes built-in)")
        out += [f"{i}. `{label}` `{json.dumps(c['input'])}`", "", "   ```", "   " + clip(c["output"]).replace("\n", "\n   "), "   ```", ""]
    out += ["## Final answer", "", s["answer"].strip(), ""]
    t = s["tokens"]
    out += ["## Run stats", "",
            f"- Exit code: {s['exit_code']}",
            f"- Tokens: {t.get('total', 0):,} total ({t.get('input', 0):,} in, {t.get('output', 0):,} out, {t.get('cache_read', 0):,} read from cache)",
            f"- Wall time reported by Hermes: {s['duration_ms']} ms", ""]
    if audit:
        out += ["## Guard audit log for this run", "", "| time (UTC) | tool | status | detail |", "|---|---|---|---|"]
        for r in audit:
            detail = r.get("error", "") or json.dumps(r.get("args", {}))
            out.append(f"| {r['ts']} | {r['tool']} | {r['status']} | {clip(detail, 140).replace('|', '/')} |")
        out.append("")
    return "\n".join(out)


def check(s: dict, audit: list[dict], tools: list[str], statuses: list[str]) -> list[str]:
    problems = []
    if s["exit_code"] != 0:
        problems.append(f"Hermes exit code {s['exit_code']}: {s['error']}")
    called = {short_tool(c["name"]) for c in s["calls"] if c["mcp"]}
    for t in tools:
        if t not in called:
            problems.append(f"expected MCP tool {t} was not called")
    seen = {r["status"] for r in audit}
    for st in statuses:
        if st not in seen:
            problems.append(f"expected an audit entry with status {st}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcript", type=Path)
    ap.add_argument("--audit", type=Path)
    ap.add_argument("--title", default="Hermes run")
    ap.add_argument("--prompt")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--expect-tool", action="append", default=[])
    ap.add_argument("--expect-status", action="append", default=[])
    args = ap.parse_args(argv)

    try:
        s = summarize(load_events(args.transcript))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    audit = load_audit(args.audit, since_ms=s["started_ms"], until_ms=s["ended_ms"])
    md = to_markdown(args.title, args.prompt, s, audit)
    if args.out:
        args.out.write_text(md + "\n", encoding="utf-8")
    else:
        print(md)
    problems = check(s, audit, args.expect_tool, args.expect_status)
    for p in problems:
        print(f"CHECK FAILED: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
