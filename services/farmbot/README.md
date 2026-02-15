# Farmbot Siri Local Container (Gunicorn)

This repository provides a local Dockerized webhook service for triggering Farmbot demo actions from Siri Shortcuts (or any HTTP client), with Flask served by **Gunicorn**.

## What this does

- Exposes a local HTTP API for action triggers
- Supports shortcuts like:
  - `water_the_rock`
  - `demo_the_bot`
  - `exercise_the_farmbot`
  - `yard_irrigation`
- Optionally posts updates to Microsoft Teams using `TEAMS_WEBHOOK_URL`

## Endpoints

- `GET /health` – health check
- `GET /actions` – available action names
- `POST /trigger/<action_name>` – execute an action
- `POST /webhooks/unifi-protect-motion` – handle UniFi Protect motion events and trigger FarmBot demo move

Example:

```bash
curl -X POST http://localhost:7777/trigger/water_the_rock \
  -H "Content-Type: application/json" \
  -d '{"x": 100, "y": 150, "water_seconds": 1}'
```


## UniFi Protect motion automation

This service now supports a UniFi Protect motion webhook flow with cooldown protection:

- Expects UniFi Protect motion webhook source host `192.168.1.59` by default
- Watches motion events for camera name `G4 Pro` (configurable)
- Calls `UNIFI_MOTION_TRIGGER_URL` on a matching motion event
- Ignores any additional motion events for 20 minutes after a successful trigger (cooldown starts only after the demo trigger request succeeds)

Configure your UniFi Protect motion bridge (`jturbett/unifi-protect-motion`) to POST event payloads to:

```text
http://192.168.1.55:7777/webhooks/unifi-protect-motion
```

Expected payload fields can include `camera_name` (or `event.cameraName`) and a motion indicator such as `motion`/`isMotionDetected`.
If you want to accept any webhook (and skip camera/motion checks), set:
`UNIFI_MOTION_REQUIRE_CAMERA=false` and `UNIFI_MOTION_REQUIRE_MOTION=false`.

If a UniFi webhook API key is configured, webhook calls must include either:
- `X-API-Key: <your-key>` header, or
- `Authorization: Bearer <your-key>` header.

Key sources are checked in this order:
1. `UNIFI_PROTECT_API_KEY_FILE`
2. `UNIFI_PROTECT_API_KEY`
3. `secrets/unifi_key` (repo-local fallback)

By default webhook requests are only accepted from `UNIFI_PROTECT_HOST=192.168.1.59`.
When running in Docker, set `UNIFI_MOTION_TRIGGER_URL` to `http://127.0.0.1:8000/...` so the webhook can call the local container.

## Local run with Docker

```bash
docker compose up --build
```

Service starts on `http://localhost:7777` and is served by Gunicorn.

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
  -e TEAMS_WEBHOOK_URL="https://..." \
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

## Siri Shortcut idea

Configure an iOS Shortcut to send a `POST` request to:

```text
http://<your-local-ip>:7777/trigger/water_the_rock
```

with optional JSON payload.

## Environment variables

- `PORT` (default `8000`)
- `LOG_LEVEL` (default `INFO`)
- `TEAMS_WEBHOOK_URL` (optional)
- `GUNICORN_WORKERS` (default `2`)
- `GUNICORN_THREADS` (default `4`)
- `GUNICORN_TIMEOUT` (default `120`)
- `UNIFI_MOTION_CAMERA_NAME` (default `G4 Pro`)
- `UNIFI_MOTION_TRIGGER_URL` (default `http://192.168.1.55:7777/trigger/demo_move_home?x=600&y=400&z=0`)
- `UNIFI_MOTION_COOLDOWN_SECONDS` (default `1200`, which is 20 minutes)
- `UNIFI_MOTION_TRIGGER_METHOD` (default `GET`, supports `POST`)
- `UNIFI_MOTION_TRIGGER_TIMEOUT` (default `60` seconds)
- `UNIFI_MOTION_REQUIRE_CAMERA` (default `true`)
- `UNIFI_MOTION_REQUIRE_MOTION` (default `true`)
- `UNIFI_PROTECT_API_KEY` / `UNIFI_PROTECT_API_KEY_FILE` (optional webhook auth secret)
- `UNIFI_PROTECT_HOST` (default `192.168.1.59`, expected webhook source host)

## Notes for real Farmbot integration

This container now uses the FarmBot Python client for movement and pin control. Ensure your token and pin mappings are correct before production use.
