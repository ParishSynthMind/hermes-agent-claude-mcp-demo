#!/usr/bin/env bash
# Install Hermes Agent into its own folder and wire it to Claude and the guarded MCP server.
#
#   HERMES_SANDBOX=./.hermes-sandbox MCP_SERVER_DIR=../mcp-guarded-github-tools scripts/setup_hermes.sh
#
# HERMES_SANDBOX becomes HOME for Hermes, so the installer's PATH lines go into the
# sandbox's .zshrc/.zprofile and its data into the sandbox's .hermes, not your real home.
# Needs: git, curl, node 22+ (for the MCP server). No sudo. No API key needed here.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$(mkdir -p "${HERMES_SANDBOX:-$REPO_DIR/.hermes-sandbox}" && cd "${HERMES_SANDBOX:-$REPO_DIR/.hermes-sandbox}" && pwd)"
MCP_SERVER_DIR="$(cd "${MCP_SERVER_DIR:?set MCP_SERVER_DIR to your mcp-guarded-github-tools checkout}" && pwd)"
MODEL="${HERMES_MODEL:-claude-sonnet-5-5}"
NODE_BIN="$(command -v node)"

[ -f "$MCP_SERVER_DIR/dist/src/index.js" ] || { echo "Build the MCP server first: (cd $MCP_SERVER_DIR && npm install && npm run build)" >&2; exit 1; }

export HOME="$SANDBOX" HERMES_HOME="$SANDBOX/.hermes"
HERMES="$SANDBOX/.local/bin/hermes"

if [ ! -x "$HERMES" ]; then
  curl -fsSL -o "$SANDBOX/install.sh" https://hermes-agent.nousresearch.com/install.sh
  echo "Read $SANDBOX/install.sh before running it if you haven't already."
  bash "$SANDBOX/install.sh" --dir "$HERMES_HOME/hermes-agent" --hermes-home "$HERMES_HOME" \
    --non-interactive --skip-browser --skip-computer-use
fi

"$HERMES" config set auth.adopt_external_logins false
"$HERMES" config set model.provider anthropic
"$HERMES" config set model.default "$MODEL"

mkdir -p "$REPO_DIR/run"
"$HERMES" mcp remove guarded_github >/dev/null 2>&1 || true
# `mcp add` connects, lists the tools and asks whether to enable them all.
echo Y | "$HERMES" mcp add guarded_github --connect-timeout 60 \
  --env "MCP_GUARD_CONFIG=$REPO_DIR/config/guard-config.json" "MCP_GUARD_AUDIT_LOG=$REPO_DIR/run/audit.jsonl" \
  --command "$NODE_BIN" --args "$MCP_SERVER_DIR/dist/src/index.js"

"$HERMES" --version | head -1
"$HERMES" mcp list
