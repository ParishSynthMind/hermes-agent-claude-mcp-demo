# 1-summarise-issues

**Prompt:**

> Using only the guarded_github tools: list the open issues in ParishSynthMind/hermes-agent-claude-mcp-demo, then give me a three-bullet summary of what work is outstanding, one bullet per issue, with the issue number.

## Tool calls, in order

1. `tool_describe (Hermes built-in)` `{"names": ["mcp__guarded_github__list_issues"]}`

   ```
   {"tools": {"mcp__guarded_github__list_issues": {"description": "List issues (not pull requests) in a repository.", "parameters": {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "properties": {"owner": {"type": "string", "pattern": "^[A-Za-z0-9-]{1,39}$", "description": "Repository owner, e.g. octocat"}, "repo": {"type": "string", "pattern": "^[A-Za-z0-9_.-]{1,100}$", "description": "Repository name"}, "state": {"default": "open", "type": "string", "enum": ["open", "closed", "all"]}, "per_page": {"default": 20, "type": "integer", "minimum": 1, "maximum": 100}}, "require ... [25 more characters]
   ```

2. `list_issues (MCP)` `{"owner": "ParishSynthMind", "repo": "hermes-agent-claude-mcp-demo", "state": "open"}`

   ```
   {"result": "[\n  {\n    \"number\": 3,\n    \"title\": \"Compare Sonnet and Opus on the same Hermes task\",\n    \"state\": \"open\",\n    \"author\": \"ParishSynthMind\",\n    \"labels\": [],\n    \"comments\": 0,\n    \"created_at\": \"2026-11-03T06:47:40Z\",\n    \"updated_at\": \"2026-11-03T06:47:40Z\",\n    \"url\": \"https://github.com/ParishSynthMind/hermes-agent-claude-mcp-demo/issues/3\"\n  },\n  {\n    \"number\": 2,\n    \"title\": \"Post one real comment with dry-run switched off\",\n    \"state\": \"open\",\n    \"author\": \"ParishSynthMind\",\n    \"labels\": [],\n    \"comments ... [613 more characters]
   ```

## Final answer

Three open issues in ParishSynthMind/hermes-agent-claude-mcp-demo. This is based on the titles only, because I didn't open the issue bodies.

- #1: Test the guarded server with a fine-grained token on a private repo.
- #2: Post one real comment with dry-run switched off.
- #3: Compare Sonnet and Opus on the same Hermes task.

## Run stats

- Exit code: 0
- Tokens: 12,860 total (12,550 in, 310 out, 10,507 read from cache)
- Wall time reported by Hermes: 11956 ms

## Guard audit log for this run

| time (UTC) | tool | status | detail |
|---|---|---|---|
| 2026-11-03T06:52:15.120Z | list_issues | ok | {"owner": "ParishSynthMind", "repo": "hermes-agent-claude-mcp-demo", "state": "open", "per_page": 20} |

