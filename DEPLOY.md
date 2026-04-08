# Deployment Guide

FetchBot (fetchbot.ai) is deployed manually to a single EC2 host running Docker
Compose. There is **no automatic deploy**: pushing to `main` only triggers the
GitHub Actions lint job (`.github/workflows/ci.yml`). Code reaches production
only when someone SSHes into the server and runs the deploy script.

## Architecture

- **Host:** Ubuntu 22.04 EC2 instance (sized around t3.small; the deploy script
  provisions a 2 GB swapfile to compensate for low RAM).
- **App directory on host:** `/opt/fetchbot/ftb-api-26`
- **Orchestration:** `docker/docker-compose.prod.yml`
- **Services:** `db` (Postgres 16), `redis`, `web` (Django/Gunicorn),
  `celery` (worker + beat in one container), `frontend` (Vue build artifact),
  `nginx` (TLS termination + static), `openclaw` (currently `restart: "no"`).
- **Edge:** Cloudflare (SSL: Full Strict) → nginx container on ports 80/443.
  TLS certs are mounted from `/opt/fetchbot/ssl` on the host.
- **Env file:** `/opt/fetchbot/ftb-api-26/.env.prod` (never committed; created
  from `.env.prod.example` on first deploy).

## Release flow

1. Merge changes into `main` on GitHub. Wait for the CI lint job to pass.
2. SSH to the production host:

   ```bash
   ssh ubuntu@<fetchbot-ec2-ip>
   ```

3. Run the deploy script:

   ```bash
   cd /opt/fetchbot/ftb-api-26
   bash scripts/deploy.sh
   ```

   The script (`scripts/deploy.sh`) performs:
   - `apt-get update && upgrade`
   - Ensures swap, Docker are present
   - `git pull origin main` in `/opt/fetchbot/ftb-api-26`
   - Verifies `.env.prod` exists
   - `docker compose -f docker/docker-compose.prod.yml down`
   - `docker compose -f docker/docker-compose.prod.yml up -d --build`
   - `python manage.py migrate --noinput`
   - `python manage.py collectstatic --noinput`
   - Hits `http://localhost/health/` as a smoke check

4. Verify:

   ```bash
   docker compose -f docker/docker-compose.prod.yml ps
   curl -I https://fetchbot.ai/health/
   ```

## First-time server bootstrap

On a fresh EC2 box:

```bash
sudo mkdir -p /opt/fetchbot && sudo chown $USER:$USER /opt/fetchbot
git clone <repo-url> /opt/fetchbot
cd /opt/fetchbot/ftb-api-26
cp .env.prod.example .env.prod
nano .env.prod   # fill in secrets, DB creds, API keys
REPO_URL=<repo-url> bash scripts/deploy.sh
```

Then point the `fetchbot.ai` A record at the EC2 public IP and set Cloudflare
SSL mode to **Full (Strict)**.

## Common operations

All commands run from `/opt/fetchbot/ftb-api-26` on the host.

| Task | Command |
|------|---------|
| Tail web logs | `docker compose -f docker/docker-compose.prod.yml logs -f web` |
| Tail celery logs | `docker compose -f docker/docker-compose.prod.yml logs -f celery` |
| Restart web only | `docker compose -f docker/docker-compose.prod.yml restart web` |
| Run a migration manually | `docker compose -f docker/docker-compose.prod.yml exec web python manage.py migrate` |
| Django shell | `docker compose -f docker/docker-compose.prod.yml exec web python manage.py shell_plus` |
| Postgres shell | `docker compose -f docker/docker-compose.prod.yml exec db psql -U postgres growthpilot` |
| Container status | `docker compose -f docker/docker-compose.prod.yml ps` |

## Rolling back

There is no built-in rollback. To revert:

```bash
cd /opt/fetchbot/ftb-api-26
git log --oneline -10
git checkout <previous-good-sha>
docker compose -f docker/docker-compose.prod.yml up -d --build
docker compose -f docker/docker-compose.prod.yml exec web python manage.py migrate
```

If the bad release included a forward migration that is not safely reversible,
restore the database from the most recent Postgres backup before rolling code
back.

## Things that are NOT automated

- Pushing to `main` does **not** deploy. CI only lints.
- There is no blue/green or canary. The deploy script takes the stack down
  with `docker compose down` before bringing it back up, so expect a brief
  outage on every release.
- Secrets rotation is manual: edit `.env.prod` on the host, then
  `docker compose -f docker/docker-compose.prod.yml up -d` to recreate
  affected containers.
- TLS certs in `/opt/fetchbot/ssl` are managed outside this repo.

## Pre-deploy checklist

- CI lint job is green on the commit being deployed.
- Local `pytest` and `ruff check .` pass.
- Any new env vars are added to `.env.prod` on the server **before** running
  the deploy script.
- New migrations have been reviewed for lock impact and reversibility.
- A recent Postgres backup exists.
