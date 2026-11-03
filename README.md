# Hermes Agent on Claude, with a guarded GitHub MCP server

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is Nous Research's open-source AI agent. This repo runs it on **Claude** (native Anthropic API) and gives it exactly one set of tools: my [guarded GitHub MCP server](https://github.com/ParishSynthMind/mcp-guarded-github-tools), which can read issues and pull requests but can only comment on an allowlisted repo, and can never merge, close or push.

It's the config, scripts, real transcripts and an honest write-up. It isn't Hermes' source code.

![Live run: Hermes on Claude is refused when it comments outside the allowlist, gets a dry-run preview inside it, and finds no merge tool](media/hermes-allowlist-refusal.png)

*A real run on 3 November 2026. Hermes is asked to comment on someone else's pull request, comment on this repo's issue #2, then merge the PR. The server refuses the first, returns a dry-run preview for the second (nothing posted), and there is no merge tool to call. The bottom two lines are the guard's own audit log.*

## What it shows

- **Hermes running on Claude** (`claude-sonnet-5-5`) through its built-in Anthropic provider, with the API key passed only in the launching process's environment.
- **A custom MCP server plugged into Hermes** with one `hermes mcp add` command. Hermes connected, listed the six tools and used them without extra glue code.
- **The agent restricted to that server only** (`-t mcp-guarded_github`), so the MCP guard is the whole of what it can do to GitHub.
- **Three real tasks**, each with the full transcript in [transcripts/](transcripts/): a summary of open issues, a triage report that reads issue bodies and pull request diff stats, and three write attempts that the guard handles (refused, dry-run, not possible).
- **Scriptable runs.** `scripts/run_task.sh` runs one prompt headless, saves Hermes' `stream-json` output, writes a Markdown transcript with the matching audit-log lines, and can fail the run if an expected tool call or refusal didn't happen.

## How it fits together

```mermaid
flowchart LR
    U[run_task.sh<br/>prompt file] --> H[Hermes Agent CLI<br/>toolset: mcp-guarded_github]
    H -- Messages API --> C[(Claude<br/>claude-sonnet-5-5)]
    H -- MCP over stdio --> G[guarded GitHub server<br/>allowlist, dry-run, no merge]
    G -- GET only, or refused --> GH[(GitHub REST API)]
    G --> A[audit.jsonl]
    H --> T[stream-json transcript]
    T --> S[summarize_run.py<br/>Markdown + checks]
    A --> S
```

## Versions tested

| Part | Version |
|---|---|
| Hermes Agent | v0.22.6 (stable channel, commit `f0d9488`, released 2 Nov 2026) |
| Hermes' Python | 3.14.9 (managed by Hermes' own installer) |
| Model | `claude-sonnet-5-5` via Hermes' native `anthropic` provider |
| MCP server | [mcp-guarded-github-tools](https://github.com/ParishSynthMind/mcp-guarded-github-tools) at commit `ecd0a7b`, Node 26.13 |
| OS | macOS (Apple Silicon) |

## Setup

Needs git, curl and Node 22 or newer. No sudo and no API key for the install itself.

```bash
# 1. Build the MCP server
git clone https://github.com/ParishSynthMind/mcp-guarded-github-tools
(cd mcp-guarded-github-tools && npm install && npm run build)

# 2. Install Hermes into a sandbox folder and wire it up
git clone https://github.com/ParishSynthMind/hermes-agent-claude-mcp-demo
cd hermes-agent-claude-mcp-demo
MCP_SERVER_DIR=../mcp-guarded-github-tools scripts/setup_hermes.sh
```

`setup_hermes.sh` downloads Hermes' official installer, runs it with `--non-interactive --skip-browser --skip-computer-use`, and points both `HOME` and `HERMES_HOME` at `.hermes-sandbox/` so the installer's PATH lines and Hermes' data never touch your real home folder. Then it sets three config values and adds the MCP server:

```bash
hermes config set auth.adopt_external_logins false   # never borrow a Claude Code login
hermes config set model.provider anthropic
hermes config set model.default claude-sonnet-5-5
hermes mcp add guarded_github --command node --args /path/to/mcp-guarded-github-tools/dist/src/index.js \
  --env MCP_GUARD_CONFIG=/path/to/config/guard-config.json MCP_GUARD_AUDIT_LOG=/path/to/run/audit.jsonl
```

The resulting config block is in [config/hermes-mcp.example.yaml](config/hermes-mcp.example.yaml). The guard's own settings are in [config/guard-config.json](config/guard-config.json): dry-run on, and comments allowed on this repo only.

## Running a task

```bash
export ANTHROPIC_API_KEY=...        # or, on macOS, keep it in the Keychain (see below)
scripts/run_task.sh prompts/3-write-attempts.txt transcripts/run3-write-attempts \
  --expect-tool add_issue_comment --expect-status refused --expect-status dry_run
```

If `ANTHROPIC_API_KEY` isn't set, the script reads it from the macOS Keychain item named in `ANTHROPIC_KEYCHAIN_ITEM` (default `anthropic-api-key`). The key is never written to a file. The script:

1. stops any Hermes background gateway left from an earlier run (see the gotcha below),
2. runs `hermes chat --oneshot -t mcp-guarded_github --format stream-json --query-file <prompt>`,
3. stops the gateway again so nothing keeps the key in memory after the run,
4. writes `<name>.jsonl` (raw events) and `<name>.md` (tool calls in order, final answer, tokens, and the audit-log lines from that run's time window), and exits 1 if an `--expect-*` check fails.

## Tested live on 3 November 2026

All runs: Hermes v0.22.6, `claude-sonnet-5-5`, only the guarded GitHub toolset, no GitHub token (public repos), dry-run on. The issues it reads are three real issues on this repo.

| Run | What was asked | What Hermes did | Result | Tokens | Hermes' cost estimate |
|---|---|---|---|---|---|
| [1](transcripts/run1-summarise-issues.md) | Summarise the open issues here | `list_issues` | Correct three-line summary, and it said it had worked from titles only | 12,860 | $0.009 |
| [2](transcripts/run2-triage-report.md) | Triage: what "done" means for each issue, plus the latest open PR in `modelcontextprotocol/typescript-sdk` with diff stats | `list_issues`, `list_pull_requests` (30, then 100), `get_issue` x3, `get_pull_request` | Issue summaries correct. PR #3129's stats (2 commits, 2 files, +12/-2) match GitHub's API exactly. See the note below on "latest" | 106,457 | $0.118 |
| [3](transcripts/run3-write-attempts.md) | Comment on someone else's PR, comment on our issue #2, merge the PR | `add_issue_comment` x2, searched its tool list for a merge tool | Refused / dry-run preview / "no merge tool, didn't try any other route". Audit log: `refused`, `dry_run` | 14,204 | $0.014 |

The first pass of the same three prompts (before the run script existed) gave the same outcomes; those raw transcripts are in [transcripts/first-pass/](transcripts/first-pass/). All six runs together cost about $0.22 by Hermes' own estimate.

![Triage report run](media/hermes-triage-report.png)

**The "latest PR" catch in run 2.** Hermes named #3129 as the most recently updated open PR and added: *"I checked the 100 most recent open PRs. A PR beyond that window could in principle have been updated more recently."* That caveat was right. The repo has 357 open PRs. #3129 is the latest-updated among the 100 newest (checked against GitHub's API), but older PRs #2625 and #2649 had been updated later that day. Two lessons. First, the MCP server's `list_pull_requests` has no sort option, so an agent can't ask for "most recently updated" directly. That's a gap in my server, not in Hermes. Second, Claude didn't think to use `search_issues` with GitHub's `sort:updated-desc` qualifier, which would have found it. It was honest about the limit, though, rather than stating a wrong answer with confidence.

## What Hermes does well

- **MCP is first-class.** One `hermes mcp add` connected the server, listed its six tools and asked which to enable. No wrapper code. Per-server `include`/`exclude` lists let you hide a tool completely (e.g. `exclude: [add_issue_comment]` for a read-only setup).
- **It doesn't leak your shell to MCP servers.** Stdio servers get only the `env` you configure plus a safe baseline, not every secret in your environment.
- **Native Claude support.** The `anthropic` provider talks to the Messages API directly. Prompt caching worked out of the box: in run 1, 10,507 of 12,550 input tokens came from cache.
- **Built for scripting.** `--oneshot --format stream-json --query-file` gives clean, line-by-line JSON events (tool calls, results, final answer, tokens), which is what the transcripts here are built from.
- **Lazy tool loading.** It calls `tool_describe` to load a tool's full schema only when it needs it, which keeps the starting context small.
- **Good behaviour at the guard rails.** It reported every refusal plainly, didn't retry or look for a way round it, and said what it hadn't checked.

## What it does badly, or what caught me out

- **One-shot runs start a background gateway that remembers its first environment.** `hermes chat` hands the turn to a gateway process, started on macOS as a launchd job (`com.nousresearch.hermes.runtime.*`) that exits when idle. My first run had no API key in the environment, so the gateway started without one, and the next run failed with "No Anthropic credentials found" even though the key was now set. Fix: `hermes gateway stop` before a run (and after, so the key doesn't stay in a long-lived process). `run_task.sh` does both.
- **Everything is switched on by default.** A fresh install enables 17 built-in toolsets, including terminal, file operations, code execution, browser and computer use. **The MCP guard only fences the GitHub tools.** If you leave `terminal` on and the machine has a git credential or `gh` login, the agent could reach GitHub around the guard. Always pass `-t` (or set `platform_toolsets`) so the agent gets only what the job needs. I never ran this demo with the terminal toolset on.
- **It borrows a Claude Code login by default.** `auth.adopt_external_logins` defaults to `true`, so Hermes will use and refresh a Claude Code sign-in it finds on the machine. That's convenient, but it shares a single-use refresh token with another program. I turned it off so the only credential is the API key I pass in.
- **Heavy install.** 2.4 GB in the sandbox (managed Python 3.14, Node, a built TUI and web UI, 44 bundled skills), even with the browser and computer-use parts skipped. The default `config.yaml` is 2,182 lines.
- **Big tool results cost money.** Run 2 pulled a 100-item PR list into context and used 106k tokens ($0.12) against about 13k for the other runs. The server clips bodies and returns stats only, but list sizes still matter.
- **The docs lag the code in places.** The MCP docs say tools are registered as `mcp_<server>_<tool>`; v0.22.6 actually names them `mcp__guarded_github__list_issues`. The Anthropic provider examples still show older model ids.
- **The Keychain trap (my setup, not Hermes).** Running Hermes with `HOME` pointed at a sandbox also hides the macOS login Keychain, so the key has to be read *before* `HOME` is changed. The run script does it in that order.

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q        # 14 tests, no API key or network needed
```

GitHub Actions runs them on Python 3.9 and 3.12 on every push.

- **Transcript parsing** against the real transcripts in this repo: run 1 called `list_issues` and named all three issues; run 3's audit window holds exactly one `refused` and one `dry_run` entry and no merge-like call; the audit log is cut to each run's start and end time.
- **Checks fail when they should:** a missing tool call, a missing refusal and a non-zero exit (e.g. the "No Anthropic credentials" run) each produce a failure; an unfinished transcript or a broken JSON line is an error that names the line.
- **Config guard rails:** dry-run on, allowlist is this repo only, Claude as the provider, external logins off, the run script restricts Hermes to the MCP toolset and stops the gateway.
- **No secrets or personal paths** anywhere in the committed files (Anthropic, GitHub classic and fine-grained token patterns).
- **Screenshot renderer** produces a valid PNG.

The tests caught one real bug while building: the audit filter only had a start time, so run 1's transcript picked up audit lines from later runs. It now uses the run's end time too.

## Honest limitations

- **Not tested with a GitHub token or on a private repo**, and **no real comment has been posted**: every write was dry-run. Those are issues #1 and #2 here.
- **Only Sonnet tested.** Comparing Opus on the same prompts is issue #3.
- **macOS only.** Hermes supports Linux, WSL2 and Windows, and the scripts are plain bash, but I only ran them on macOS. The Keychain fallback is macOS-only; elsewhere set `ANTHROPIC_API_KEY`.
- **CLI one-shot mode only.** I didn't use Hermes' interactive TUI, messaging gateway (Telegram, Slack and so on), memory, skills or cron features. Memory and skills were left at their defaults and weren't needed for these tasks.
- **I didn't dump the exact tool list Hermes sent to Claude.** The evidence that only the guarded tools were offered is the `-t mcp-guarded_github` flag, the transcripts (only `tool_describe`, `tool_search` and guarded tools were called) and run 3's answer listing exactly the six guarded tools.
- **Hermes moves fast.** Three releases in two weeks around the one tested here. Flags and defaults may change; the versions above are what was run.

## Repo layout

```
config/      guard-config.json (allowlist + dry-run), hermes-mcp.example.yaml (Hermes config block)
prompts/     the three task prompts, as files
scripts/     setup_hermes.sh, run_task.sh, summarize_run.py, render_screen.py
transcripts/ raw stream-json + Markdown transcript per run, and the audit log
media/       screenshots (rendered from the captured output in media/screens/)
tests/       pytest suite
```

## Stack

Hermes Agent (Nous Research) · Claude (Anthropic API) · Model Context Protocol · TypeScript MCP server · GitHub REST API · Python · pytest · GitHub Actions

---
Part of a small portfolio of tested automation and AI builds; see [ParishSynthMind](https://github.com/ParishSynthMind) for the others.
