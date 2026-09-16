# Security Notes

## 2026-09 security hardening

This file records security-hardening work so future maintenance does not require reconstructing decisions from chat history.

### What was reviewed
- GitHub Actions workflow permissions and third-party Action references.
- Workflows that use `contents: write`.
- Workflows capable of modifying repository source automatically.
- Telegram bot code, including token usage, authorization checks, database queries, and callback handling.
- Encrypted private state handling.

### Decisions
- Third-party GitHub Actions should be pinned to full commit SHAs where practical.
- `GITHUB_TOKEN` permissions should remain at the minimum required level. Workflows that genuinely persist runtime state may retain `contents: write`.
- Source-transforming automation must not silently push generated source directly to the default branch. Generated changes should be reviewed through the normal PR process.
- Existing application behavior should not be changed merely because a pattern looks unusual; changes require evidence and should be isolated in a PR.
- No evidence of malware/backdoor was established during the 2026-09 review.

### Button-upgrade workflow
The `tools/enable_bot_buttons.py` script intentionally transforms `workers/bot-interface/src/index.js`. Previously, its workflow had permission to commit and push that generated source directly. The security branch changes this workflow to read-only permissions, pins checkout to an immutable commit, validates the generated JavaScript, and reports the diff instead of pushing it automatically.

This is a supply-chain/integrity hardening change, not a claim that the upgrade script is malicious.

### Follow-up items
- Review remaining workflows for source mutation and unnecessary write permissions.
- Keep required runtime-state writes separate from source-code writes where possible.
- Periodically re-verify pinned Action SHAs and dependency updates.
- Record future security changes in this file with date, scope, decision, and rationale.
