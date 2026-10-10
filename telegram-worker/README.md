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
- `TELEGRAM_WEBHOOK_SECRET`: random secret of 32+ characters using only A-Z, a-z, 0-9, underscore, and hyphen.

Never add secret values to source control. The deployment workflow will refuse to run when any required secret is missing.

## Deploy

The workflow `.github/workflows/deploy_telegram_worker.yml` deploys this directory after tests pass. Cloudflare's automatic binding provisioning creates the D1 resource on first deployment. Confirm the D1 binding exists in Cloudflare if the first deployment reports a provisioning limitation.

After deployment, obtain the URL shown in the workflow log (normally `https://coalicion-telegram.<your-subdomain>.workers.dev`). Then set the webhook once, replacing placeholders locally:

```bash
curl -sS -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H 'content-type: application/json' \
  -d "{\"url\":\"https://coalicion-telegram.<your-subdomain>.workers.dev/telegram/webhook\",\"secret_token\":\"$TELEGRAM_WEBHOOK_SECRET\",\"allowed_updates\":[\"message\",\"callback_query\"],\"drop_pending_updates\":false}"
```

Do not publish the expanded command or its secrets. Verify with `getWebhookInfo`, then open the bot in Telegram and send `/start`.

## Local verification

```bash
cd telegram-worker
npm install --no-audit --no-fund
npm test
npm run typecheck
```

Free service is subject to Cloudflare's current quotas and account availability; this is not a contractual 24/7 SLA. Existing GitHub Actions polling remains separate until the webhook is deployed and verified.
