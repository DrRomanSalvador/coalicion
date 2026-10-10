# COALICIÓN Telegram Worker

Persistent Cloudflare Workers webhook frontend for the COALICIÓN dispatch bot. It uses D1 for idempotency, tasks, and preferences; it does not depend on GitHub Actions polling or a runner filesystem.

## Security and scope

- Webhook requests require Telegram's `X-Telegram-Bot-Api-Secret-Token`.
- Only the numeric account in `TELEGRAM_ALLOWED_USER_ID` can invoke commands or callbacks.
- Tokens are secrets and must never be committed or pasted into chat.
- D1 writes are persistent. Duplicate Telegram update IDs are ignored.
- `/hoy`, `/urgente`, and `/resumen` currently summarize persisted dispatch tasks. They do **not** claim fresh election evidence. `/buscar` searches tasks only. The existing Python bot and electoral pipeline are not silently represented as migrated.

## Required GitHub Actions secrets

Set these in repository Settings → Secrets and variables → Actions → Repository secrets:

- `CLOUDFLARE_API_TOKEN`: scoped to the Cloudflare account's required Worker deployment permissions.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.
- `TELEGRAM_BOT_TOKEN`: token from BotFather.
- `TELEGRAM_ALLOWED_USER_ID`: operator's numeric Telegram user ID (digits only).

Never add secret values to source control. The workflow validates required secrets without printing them and generates a fresh webhook secret for the Worker.

## One-time Cloudflare setup

Before the first deploy, open the Cloudflare Dashboard → **Workers & Pages** and complete the account's **workers.dev** onboarding/register a workers.dev subdomain. Wrangler cannot complete this interactive account setup from a non-interactive GitHub Actions runner. The workflow now detects this specific failure and prints an actionable error instead of a generic deployment failure.

## Deploy

1. Add the four repository secrets listed above (the existing `TELEGRAM_BOT_TOKEN` may already be used by the current bot workflow; verify that it exists).
2. Complete the one-time `workers.dev` onboarding described above.
3. Open Actions → **Deploy COALICIÓN Telegram webhook** → **Run workflow**.
4. The workflow validates secrets, runs tests and type-checking, deploys the Worker, configures Worker secrets, registers Telegram's webhook, and verifies `/health`. It stops if a required secret is missing or Cloudflare rejects deployment.
5. Open the bot in Telegram and send `/start`. Test `/tarea Preparar briefing`, `/tarea`, `/hoy`, and the task buttons.

The workflow discovers the deployed `workers.dev` URL and registers the webhook automatically; no manual `curl` command is required. If Cloudflare rejects the D1 binding because the database has not been created or linked, inspect the Wrangler error and configure the D1 database ID in `telegram-worker/wrangler.jsonc` before rerunning.

## Local verification

```bash
cd telegram-worker
npm install --no-audit --no-fund
npm test
npm run typecheck
```

Free service is subject to Cloudflare's current quotas and account availability; this is not a contractual 24/7 SLA. Existing GitHub Actions polling remains separate until the webhook is deployed and verified.
