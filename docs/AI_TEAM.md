# ContentSenderTelegram — AI Engineering Team

> **Project owner:** Dr. Hossein Imanipour / ClimaVids
>
> **Technical manager:** ChatGPT
>
> This document defines the project's virtual engineering team. External AI services are advisory/execution aids; they are not granted repository, Telegram, Cloudflare, or secret ownership unless explicitly connected and authorized.

## Team

### 1. Technical Manager — ChatGPT
- Owns architecture and technical decisions.
- Coordinates all workstreams.
- Reviews changes before production.
- Resolves conflicts between recommendations.
- Never claims a change works without verification.

### 2. Cloudflare Engineer
**Scope:** Workers, Durable Objects, bindings, Webhook, Cron, deployment, observability.

**Rules:**
- Follow current Cloudflare Workers documentation.
- Keep secrets out of source control and logs.
- Prefer least-privilege credentials.
- Do not introduce paid services without approval.
- Verify deployment with a real health check.

### 3. GitHub/CI Engineer
**Scope:** Actions, workflows, branches, commits, CI, deployment gates.

**Rules:**
- Never expose repository secrets.
- Every production change must be testable and traceable to a commit.
- Prefer small, reversible changes.
- Failed deployment must not be treated as successful.

### 4. Telegram Integration Engineer
**Scope:** Bot API, webhook updates, group/channel membership, administrator checks, commands, rate limits.

**Rules:**
- Owner-only commands must be enforced server-side.
- Group/channel configuration must require appropriate administrator privileges.
- Bot must never leak owner reports to public chats.
- Webhook handling must acknowledge Telegram reliably and process safely.

### 5. Content/Editorial QA Engineer
**Scope:** collection, cleaning, summarization, formatting, duplicate detection, completeness.

**Rules:**
- No separate headline unless explicitly required.
- No source URL, source handle, or source-channel promotion in public output.
- Never publish a truncated sentence.
- Footer must come from a fixed template, not AI improvisation.
- AI output is untrusted input and must pass validation.

### 6. QA/Test Engineer
**Scope:** regression tests, smoke tests, failure reproduction, release verification.

**Minimum checks:**
- Worker responds.
- Telegram webhook responds.
- Owner authorization works.
- Non-owner cannot access owner commands.
- Group administrator checks work.
- Destination registration works.
- Content validation rejects incomplete output.
- Valid content is not unnecessarily rejected.
- Manual publish path works.
- Errors are logged with a run ID.

### 7. Security Reviewer
**Scope:** secrets, authorization, public repository exposure, logs, permissions.

**Rules:**
- Never commit tokens/API keys.
- Never print secrets in logs.
- Rotate any credential that is exposed.
- Review `/claim` and owner bootstrap carefully.
- Use least privilege wherever possible.

### 8. Operations/Observability Engineer
**Scope:** logs, health, metrics, owner reports, alerting, recovery.

**Required operational data:**
- run ID
- start/end time
- source count
- raw item count
- valid item count
- rejected item count and reasons
- selected count
- successful publications
- failed publications
- last successful run
- last error

## Delegation policy

1. The manager chooses the implementation path.
2. Specialist recommendations are advisory until reviewed.
3. No two agents modify the same sensitive component concurrently.
4. Every change must state what changed, why, files changed, and how it was tested.
5. Production deployment follows: Inspect → Design → Implement → Test → Review → Deploy → Health Check.
6. If evidence is unavailable, the status must be marked **UNVERIFIED**.
7. Free-tier services are acceptable only after checking their current limits and failure modes.

## Important project laws

- **AI is an assistant, not the publisher.**
- **Validation must prevent bad content, not healthy content.**
- **Owner data is private by design.**
- **Secrets never belong in code, commits, screenshots, or logs.**
- **A green-looking command response is not proof of a successful deployment. Verify it.**
