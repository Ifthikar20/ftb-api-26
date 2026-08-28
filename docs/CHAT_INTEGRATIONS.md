# Slack and Discord Integrations

Date: 2026-08-18

Cansee's chat integrations do two things:

1. **Outbound**: deliver the daily report digest, brand-security alerts, and agent
   insights into a Slack or Discord channel via that channel's incoming webhook.
2. **Inbound**: an in-channel bot. In Discord, `/cansee` slash commands
   (`report`, `security`, `ask`, `scan`, `help`). In Slack, the same command set via
   `/cansee` plus `@Cansee` mentions.

Both directions are tenant-bound: a connection row (Integrations page) links your
Cansee account to a Slack workspace (Team ID) or Discord server (Server ID), and every
inbound command resolves through that link. Unlinked workspaces get a private reply
explaining how to link, and nothing else.

## Architecture

No persistent bot process runs. Both platforms deliver signed HTTPS webhooks:

```
Slack / Discord ── signed POST ──> nginx ──> Django endpoint
    verify signature (HMAC-SHA256 / Ed25519, raw body)
    resolve IntegrationConnection by external_team_id -> (user, website)
    acknowledge within 3 seconds
        Discord: deferred response (type 5)
        Slack:   200 + ephemeral "thinking" text
    Celery task on the ai queue builds the real answer
        report   -> daily digest builders (deterministic)
        security -> open SafetyAlerts + detector recommended_action
        ask      -> agents chat pipeline (RAG + Claude synthesis, spend-capped)
        scan     -> audit_factory + scan_dispatch (saved prompts, spend-capped)
    reply posted back
        Discord: interaction follow-up webhook (15-minute token window)
        Slack:   response_url, or chat.postMessage for @mentions (bot token)
```

Endpoints (all POST, signature-verified, rate-limited per IP):

| Purpose | URL |
|---|---|
| Discord interactions | `/api/v1/notifications/discord/interactions/` |
| Slack events (mentions) | `/api/v1/notifications/slack/events/` |
| Slack slash commands | `/api/v1/notifications/slack/commands/` |

## Environment variables

Add to `.env` (dev) and `.env.prod` (production):

```
SLACK_SIGNING_SECRET=    # Slack app -> Basic Information -> Signing Secret
SLACK_BOT_TOKEN=         # Slack app -> OAuth & Permissions -> Bot User OAuth Token (xoxb-...)
DISCORD_PUBLIC_KEY=      # Discord application -> General Information -> Public Key
DISCORD_APPLICATION_ID=  # Discord application -> General Information -> Application ID
DISCORD_BOT_TOKEN=       # Discord application -> Bot -> Token (used only to register commands)
```

The webhook URLs users paste on the Integrations page are stored encrypted per
connection and are validated against platform hosts (`hooks.slack.com`,
`discord.com/api/webhooks`).

## Discord setup (one time, developer portal)

1. https://discord.com/developers/applications -> New Application -> name it Cansee.
2. General Information: copy **Application ID** and **Public Key** into the env vars.
3. Bot tab: copy the **Token** into `DISCORD_BOT_TOKEN`. No privileged intents needed.
4. General Information -> **Interactions Endpoint URL**: set to
   `https://cansee.ai/api/v1/notifications/discord/interactions/` and save. Discord
   sends a signed PING; the save only succeeds if the endpoint verifies it (deploy the
   backend with `DISCORD_PUBLIC_KEY` set first).
5. Register the slash commands (from the repo, once per deploy of command changes):

```bash
python manage.py register_discord_commands
```

   Add `--guild <server-id>` during testing — guild commands appear instantly, global
   commands can take up to an hour.
6. Invite the app to your server: OAuth2 -> URL Generator -> scope
   `applications.commands` (add scope `bot` if you also want the bot user visible),
   open the generated URL, pick the server.
7. In Discord, enable Developer Mode (Settings -> Advanced), right-click the server ->
   **Copy Server ID**.
8. In Cansee -> Integrations -> Discord -> connect: paste a channel **webhook URL**
   (Server Settings -> Integrations -> Webhooks -> New Webhook) for outbound digests,
   and the **Server ID** to link `/cansee` commands to your account.

## Slack setup (one time, api.slack.com/apps)

1. Create New App -> From scratch -> name Cansee, pick the workspace.
2. Basic Information: copy the **Signing Secret** into `SLACK_SIGNING_SECRET`.
3. OAuth & Permissions: add bot scopes `chat:write`, `commands`, `app_mentions:read`.
   Install to workspace; copy the **Bot User OAuth Token** into `SLACK_BOT_TOKEN`.
4. Event Subscriptions: enable, set Request URL to
   `https://cansee.ai/api/v1/notifications/slack/events/` (Slack sends a
   `url_verification` challenge; the endpoint echoes it once the backend is deployed
   with the signing secret). Subscribe to the bot event `app_mention`.
5. Slash Commands: create `/cansee`, Request URL
   `https://cansee.ai/api/v1/notifications/slack/commands/`, usage hint
   `report | security | ask <question> | scan`.
6. Find the workspace **Team ID** (starts with T): visible in the Slack app's URL or
   under the workspace's About page.
7. In Cansee -> Integrations -> Slack -> connect: paste an **Incoming Webhook URL**
   (the app's Incoming Webhooks feature) for outbound digests, and the **Team ID** to
   link commands and mentions.

## Command reference

| Command | What it does |
|---|---|
| `/cansee report` | The daily digest, on demand: traffic summary, GEO visibility deltas, open brand-security counts. |
| `/cansee security` | Open brand-security findings, severity-ordered, each with its recommended mitigation. |
| `/cansee ask <question>` | Free-form question answered by the agent pipeline: RAG over your brand data + latest audit results, synthesized by Claude. Subject to your plan's AI allowance. |
| `/cansee scan` | Queues an LLM visibility audit of your saved prompts. Refuses with a pointer when no prompts are saved. |
| `/cansee help` | Lists the commands. |

In Slack, `@Cansee <question>` behaves like `ask`.

## Local testing without a public domain

Discord must be able to POST to the interactions endpoint, so localhost alone is not
enough — expose the local backend through a free tunnel:

1. Install cloudflared (`winget install Cloudflare.cloudflared`) and run:
   `cloudflared tunnel --url http://localhost:8000`
   It prints a URL like `https://<random>.trycloudflare.com`. (ngrok works too but
   needs an account.) The URL changes each restart — re-save it in the portal when it
   does.
2. Put the Discord keys in the local `.env`, restart the web and celery containers.
3. If Discord's PING save fails with a DisallowedHost error in the web logs, add the
   trycloudflare host to ALLOWED_HOSTS for dev.
4. Set the portal's Interactions Endpoint URL to
   `https://<random>.trycloudflare.com/api/v1/notifications/discord/interactions/`.
5. Dev runs Celery eagerly, so quick commands answer inline; if `ask` times out
   (3-second window vs LLM latency), run a real worker (`make celery`) with eager mode
   off.

When the new production domain exists, the only integration changes are the portal
URLs (Discord interactions; Slack events/commands) and the env on the new host — no
code changes.

## Operational notes

- Signature failures return 401 and are logged; stale Slack retries (>5 minutes) are
  acknowledged and dropped, matching the Stripe webhook's replay policy.
- All LLM work triggered from chat goes through the core.llm gateway: it is recorded in
  AITokenUsage (module "notifications", or the agent-chat role when routed through a
  hired agent) and blocked by the monthly AI allowance like every other AI feature.
- Digest scheduling: connections with frequency "weekly" send on Mondays; "daily" every
  morning at the beat schedule time; "realtime" connections receive alerts only.
- The daily digest reports only real data; sections with nothing to show say so and
  name the action that produces data.
