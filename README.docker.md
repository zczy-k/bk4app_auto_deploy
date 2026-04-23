# Docker Deploy

Main deployment documentation has been moved to `README.md`.

This file is kept as a short Docker-specific reference.

## Quick Start

1. Copy `.env.example` to `.env`
2. Fill `BACK4APP_EMAIL`, `BACK4APP_PASSWORD`, and optional `BACK4APP_COOKIE`
3. Start with `docker compose up -d --build`

## GHCR Image

- `ghcr.io/zczy-k/bk4app_auto_deploy:latest`

Example:

```bash
docker pull ghcr.io/zczy-k/bk4app_auto_deploy:latest
docker run -d \
  --name auto_deploy \
  --restart unless-stopped \
  --env-file .env \
  -p 7860:7860 \
  -v $(pwd)/.env:/app/.env \
  ghcr.io/zczy-k/bk4app_auto_deploy:latest
```

## Health Check

- `GET /`
- `GET /health`
- `GET /healthz`

## Logs

- `docker compose logs -f`
- `docker logs -f auto_deploy`
