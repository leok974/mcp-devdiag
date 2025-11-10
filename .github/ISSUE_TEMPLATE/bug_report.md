---
name: Bug report
about: Report a bug or unexpected behavior
labels: bug
---

## What happened

A clear description of the bug.

## Expected behavior

What you expected to happen instead.

## Reproduction steps

1. Configure devdiag.yaml with...
2. Run command...
3. See error...

## DevDiag output

```bash
curl -s -G "$BASE/mcp/diag/status_plus" \
  --data-urlencode "base_url=$APP" \
  -H "Authorization: Bearer $JWT" | jq
```

<details>
<summary>Output</summary>

```json
{
  "problems": [...],
  "score": ...,
  "severity": "..."
}
```
</details>

## Environment

- **mcp-devdiag version**: x.y.z
- **Python version**: 3.x.x
- **Driver**: http | playwright
- **Mode**: dev | staging | prod:observe | prod:incident
- **OS**: Windows | Linux | macOS

## Additional context

Any other relevant information (logs, screenshots, configuration snippets).
