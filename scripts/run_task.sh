#!/usr/bin/env bash
# Run one prompt through Hermes on Claude with ONLY the guarded GitHub MCP tools enabled,
# save the stream-json transcript, and write a Markdown summary next to it.
#
#   scripts/run_task.sh prompts/1-summarise-issues.txt transcripts/run1 [summarize_run.py --expect-* args]
#
# The Anthropic key comes from ANTHROPIC_API_KEY if set, otherwise from the macOS Keychain
# item named by ANTHROPIC_KEYCHAIN_ITEM (default anthropic-api-key). It lives only in this
# process's environment and the Hermes gateway it starts, never in a file.
set -euo pipefail

PROMPT_FILE="${1:?prompt file}"; OUT="${2:?output path without extension}"; shift 2
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="${HERMES_SANDBOX:-$REPO_DIR/.hermes-sandbox}"
MAX_TURNS="${HERMES_MAX_TURNS:-15}"

# Read the key BEFORE swapping HOME: the Keychain lookup uses the real home.
if [ -z "${ANTHROPIC_API_KEY:-}" ] && command -v security >/dev/null; then
  ANTHROPIC_API_KEY="$(security find-generic-password -s "${ANTHROPIC_KEYCHAIN_ITEM:-anthropic-api-key}" -w)"
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "No ANTHROPIC_API_KEY" >&2; exit 1; }
export ANTHROPIC_API_KEY

export HOME="$SANDBOX" HERMES_HOME="$SANDBOX/.hermes"
HERMES="$SANDBOX/.local/bin/hermes"
mkdir -p "$SANDBOX/work" "$(dirname "$OUT")"

# `hermes chat` hands the turn to a background gateway (a launchd job on macOS) that keeps the
# environment it was first started with. Stop any old one so this run's key is the one used,
# and stop it again afterwards so no process keeps the key once the run is over.
"$HERMES" gateway stop >/dev/null 2>&1 || true
trap '"$HERMES" gateway stop >/dev/null 2>&1 || true' EXIT

"$HERMES" chat --oneshot -t mcp-guarded_github --max-turns "$MAX_TURNS" --in "$SANDBOX/work" \
  --format stream-json --query-file "$PROMPT_FILE" > "$OUT.jsonl"

python3 "$REPO_DIR/scripts/summarize_run.py" "$OUT.jsonl" --audit "$REPO_DIR/run/audit.jsonl" \
  --title "$(basename "$PROMPT_FILE" .txt)" --prompt "$(cat "$PROMPT_FILE")" --out "$OUT.md" "$@"
echo "Wrote $OUT.jsonl and $OUT.md"
