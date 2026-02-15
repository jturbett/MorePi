# Farmbot Siri Local Container (Gunicorn)

This repository provides a local Dockerized webhook service for triggering Farmbot demo actions from Siri Shortcuts (or any HTTP client), with Flask served by **Gunicorn**.

## What this does

- Exposes a local HTTP API for action triggers
- Supports shortcuts like:
  - `water_the_rock`
  - `demo_the_bot`
  - `exercise_the_farmbot`
  - `yard_irrigation`
  - `light_on` (turn peripheral #7 on)
  - `light_off` (turn peripheral #7 off)
- Optionally posts updates to Discord using `DISCORD_WEBHOOK_URL`.

## Endpoints

- `GET /health` – health check
- `GET /actions` – available action names
- `POST /trigger/<action_name>` – execute an action

Example:

```bash
curl -X POST http://localhost:7777/trigger/water_the_rock \
  -H "Content-Type: application/json" \
  -d '{"x": 100, "y": 150, "water_seconds": 1}'
```

## Local run with Docker

```bash
docker compose up --build
```

Service is exposed on `http://localhost:7777` for users/Shortcuts.
Internally, Gunicorn listens on container port `8000` and Docker maps `7777:8000`.

## Can I deploy this via Codex CLI?

Yes—**if your Codex CLI session has access to Docker and your target host/registry**, you can deploy from the CLI by running normal Docker commands.

Codex CLI is an automation interface for running commands; it is **not** a hosting platform by itself.

### Typical Codex CLI deployment flow

```bash
# 1) Build

docker build -t farmbot-siri-local:latest .

# 2) Run locally on the deployment machine

docker run -d --name farmbot-siri -p 7777:8000 \
  -e LOG_LEVEL=INFO \
  -e DISCORD_WEBHOOK_URL_FILE="/run/secrets/discord_webhook" \
  -v $(pwd)/secrets/discord.txt:/run/secrets/discord_webhook:ro \
  farmbot-siri-local:latest

# 3) Verify

curl http://localhost:7777/health
```

If you plan to deploy to a remote server, push to a registry and pull/run there:

```bash
docker tag farmbot-siri-local:latest <registry>/<namespace>/farmbot-siri:latest
docker push <registry>/<namespace>/farmbot-siri:latest
```

Then on the remote host:

```bash
docker pull <registry>/<namespace>/farmbot-siri:latest
docker run -d --restart unless-stopped --name farmbot-siri -p 7777:8000 \
  <registry>/<namespace>/farmbot-siri:latest
```


## Can this be auto-committed to GitHub?

Yes—if the Codex CLI environment has GitHub credentials configured, it can run normal `git`/`gh` commands to commit and push automatically.

### Requirements

- A remote configured (for example `origin`)
- Write access to the target repository
- Authentication available in the runtime (SSH key, PAT, or `gh auth login`)

### Example flow

```bash
# confirm branch and changes
git status
git branch --show-current

# commit changes
git add .
git commit -m "Update Farmbot workflow"

# push to GitHub
git push origin $(git branch --show-current)
```

If authentication is missing, the commit can still be created locally, but `git push` will fail until credentials are provided.


## How do I update a file to serve secrets?

Use a **file-based secret** and point the app to it with `DISCORD_WEBHOOK_URL_FILE`.

1. Create/update a local secret file:

```bash
mkdir -p secrets
printf "%s" "https://discord.com/api/webhooks/<id>/<token>" > secrets/discord.txt
```

2. Start with Docker Compose (already wired in `docker-compose.yml`):

```bash
docker compose up --build
```

3. The app reads secret values in this order:

- `DISCORD_WEBHOOK_URL_FILE` (file contents, preferred)
- `DISCORD_WEBHOOK_URL` (env fallback)

This keeps webhook URLs out of source code and out of command history.

> Security note: if a real Discord webhook URL was shared publicly, rotate it now in Discord server settings and replace the secret file with the new value.


## Where should I put the Farmbot secret?

Put it in a local file at:

- Host path (on your machine, in this repo): `./secrets/farmbot_authorization_token.json`

Then Docker Compose mounts that file into the container as:

- Container path: `/run/secrets/farmbot_authorization_token`
- Env var inside container: `FARMBOT_API_TOKEN_FILE=/run/secrets/farmbot_authorization_token`

So: create/edit the file in your **repo directory on the host** (not in your home dir unless the repo is there).

Quick setup:

```bash
mkdir -p secrets
cp ~/compose-stack/secrets/farmbot_authorization_token.json secrets/farmbot_authorization_token.json
```

This file is ignored by git (`secrets/*.txt` and `secrets/*.json`), so it stays local.

Given your setup, your source files can live at `~/compose-stack/secrets/` (for example `discord.txt` and `farmbot_authorization_token.json`) and be copied or bind-mounted into this project path expected by compose.


## Discord restart notification on container start

When the container starts/restarts, Gunicorn sends a Discord message that includes:

- restart time (UTC)
- your status URL link

This runs once from Gunicorn master on startup.

Set these env vars:

- `DISCORD_WEBHOOK_URL` or `DISCORD_WEBHOOK_URL_FILE`
- `STATUS_URL` (for example `https://your-host-or-ddns:7777/health`)
- `DISCORD_RESTART_NOTIFY` (`true` or `false`, default `true`)

## Siri Shortcut idea

Configure an iOS Shortcut to send a `POST` request to:

```text
http://<your-local-ip>:7777/trigger/water_the_rock
```

with optional JSON payload.

Light endpoints example:

```bash
curl -X POST http://localhost:7777/trigger/light_on
curl -X POST http://localhost:7777/trigger/light_off
```

## Ports (what you should use)

- Use this from your browser/Shortcut/remote host: **`7777`**
- Internal container port: `8000`
- Docker mapping: `7777:8000`

## Environment variables

- `PORT` (container internal app port, default `8000`; host access remains `7777`)
- `LOG_LEVEL` (default `INFO`)
- `DISCORD_WEBHOOK_URL` (optional, plain env fallback)
- `DISCORD_WEBHOOK_URL_FILE` (optional, preferred for secrets)
- `FARMBOT_API_TOKEN` (optional, plain env fallback for future Farmbot integration)
- `FARMBOT_API_TOKEN_FILE` (optional, preferred file-based token for future Farmbot integration)
- `GUNICORN_WORKERS` (default `2`)
- `GUNICORN_THREADS` (default `4`)
- `GUNICORN_TIMEOUT` (default `120`)

## Notes for real Farmbot integration

Current action implementations are safe stubs that log step-by-step behavior. Replace `_mock_farmbot_step(...)` with your Farmbot MQTT command layer and add secure credential management before production use.
