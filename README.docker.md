# Docker Deploy

## Behavior

- The container starts `scheduler.py`
- The scheduler reads `CRON_SCHEDULE` from `.env`
- Each scheduled run executes `python auto_redeploy.py`
- Each run checks the current Back4App app status and redeploys immediately when the domain status is `EXPIRED`
- A health endpoint listens on port `7860`
- `.env` stays persisted through bind mounts

## Environment

- `CRON_SCHEDULE`: cron expression, default `*/1 * * * *`
- `RUN_ON_STARTUP`: run once immediately after container start, default `false`
- `APP_ID_MAP_JSON`: JSON mapping for multi-app usage, example `{"app1":"env1","app2":"env2"}`
- `PORT`: health port, default `7860`
- `LOG_LEVEL`: log level, default `INFO`

## Start

1. Copy `.env.example` to `.env`
2. Fill `BACK4APP_EMAIL`, `BACK4APP_PASSWORD`, and optional `BACK4APP_COOKIE`
3. Run `docker compose up -d --build`

## Pull From GHCR

- Image: `ghcr.io/zczy-k/bk4app_auto_deploy:latest`
- The image is published by GitHub Actions on pushes to `master`, version tags, or manual runs

Example:

```bash
docker pull ghcr.io/zczy-k/bk4app_auto_deploy:latest
docker run -d \
  --name auto_deploy \
  --restart unless-stopped \
  --env-file .env \
  -p 7860:7860 \
  -v ${PWD}/.env:/app/.env \
  ghcr.io/zczy-k/bk4app_auto_deploy:latest
```

## Health Check

- `GET /`
- `GET /health`
- `GET /healthz`

## Logs

- `docker compose logs -f`

## Stop

- `docker compose down`
