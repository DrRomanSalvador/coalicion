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

- `CLOUDFLARE_API_TOKEN`: scoped to Workers Scripts edit and D1 edit/use for the account.
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID.
- `TELEGRAM_BOT_TOKEN`: token from BotFather.
- `TELEGRAM_ALLOWED_USER_ID`: operator's numeric Telegram user ID.

Never add secret values to source control. The deployment workflow generates a fresh webhook secret automatically and will refuse to run when any required secret is missing.

## Deploy

1. Add the four repository secrets listed above (the existing `TELEGRAM_BOT_TOKEN` is already used by the current bot workflow).
2. Open Actions → **Deploy COALICIÓN Telegram webhook** → **Run workflow**.
3. The workflow runs tests and type-checking, deploys the Worker, provisions its D1 binding, stores Worker secrets, registers Telegram's webhook, and verifies `/health`. It stops before deployment if any required secret is missing.
4. Open the bot in Telegram and send `/start`. Test `/tarea Preparar briefing`, `/tarea`, `/hoy`, and the task buttons.

The workflow discovers the deployed `workers.dev` URL and registers the webhook automatically; no manual `curl` command is required. If Cloudflare automatic D1 provisioning is rejected by the account, create the D1 database in Cloudflare and add its ID to `telegram-worker/wrangler.jsonc`, then rerun deployment.

## Local verification

```bash
cd telegram-worker
npm install --no-audit --no-fund
npm test
npm run typecheck
```

Free service is subject to Cloudflare's current quotas and account availability; this is not a contractual 24/7 SLA. Existing GitHub Actions polling remains separate until the webhook is deployed and verified.
