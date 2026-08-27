# ContentSenderTelegram — Project Governance

## Authority

- **Owner:** ClimaVids / Dr. Hossein Imanipour
- **Technical manager:** ChatGPT
- **Repository:** `ClimaVids/ContentSenderTelegram`
- **Telegram bot:** `@Climavid_bot`

The owner is not expected to participate in routine debugging, code review, deployment diagnosis, or tool selection. The technical manager should proceed autonomously whenever the required access and evidence are available.

## Decision hierarchy

1. Telegram/Cloudflare/GitHub official documentation and observed runtime behavior.
2. Existing project requirements explicitly approved by the owner.
3. Security and reliability requirements in this document.
4. Specialist/AI recommendations.
5. Convenience.

When sources conflict, the higher item wins.

## Production gate

No production deployment is considered complete until all applicable checks pass:

- repository code is internally consistent;
- CI/tests pass;
- Wrangler configuration is valid;
- deployment output confirms success;
- Worker endpoint is reachable;
- Telegram Bot API responds;
- webhook is correctly configured;
- owner-only authorization is enforced;
- public/group commands work as designed;
- content validation does not reject valid content unnecessarily;
- at least one controlled smoke test succeeds;
- logs and reporting record the run.

## Change management

- Prefer small, atomic commits.
- Do not make unrelated changes in one commit.
- Do not deploy an unverified fix simply because the previous deployment failed.
- Preserve a known-good rollback point.
- Never overwrite secrets or sensitive state in source control.

## Content publication safety

Public content must:

- start directly with the intended body, not an automatically generated headline;
- contain complete sentences;
- not end abruptly because of truncation;
- not expose source URLs;
- not expose source channel IDs/handles;
- not reproduce source promotional hashtags;
- retain the fixed ClimaVids footer;
- pass length and Telegram-format validation.

A failed content-quality check should attempt a safe recovery/re-fetch where practical. It must not create an unnecessarily strict filter that blocks normal valid posts.

## Owner privacy

Owner reports, network statistics, destination names, internal logs, technical diagnostics, and operational details are private. They must only be returned after server-side owner authorization.

`/claim` must never allow an arbitrary person to take ownership of an already claimed production bot.

## Free-service policy

Use free services where they meet reliability and quota requirements. Before adding a service, record:

- free-tier limits;
- rate limits;
- whether a payment method is required;
- data/privacy implications;
- availability in the deployment environment;
- fallback behavior;
- risk of unexpected billing.

## Incident policy

When a production failure occurs:

1. Preserve evidence.
2. Identify the first failing boundary.
3. Avoid speculative rewrites.
4. Fix the smallest root cause.
5. Run regression tests.
6. Re-deploy.
7. Verify the live system.
8. Record the incident and prevention rule.

## Non-negotiable reminders

> **AI is an assistant, not the publisher.**

> **Validation must prevent bad content, not healthy content.**

> **Never expose secrets. Never log secrets.**

> **Never claim success without runtime evidence.**

> **Do not ask the owner to perform routine technical work when the project tools already provide the required access.**
