Backup4App 容器自动重新部署。

## 使用方式

复制 `.env.example` 为 `.env`，填写 Back4App 账号信息和可选的 `BACK4APP_COOKIE`。

本项目支持两种 Docker 部署方式：

- 本地构建并启动：`docker compose up -d --build`
- 直接拉取 GitHub Container Registry 镜像：`ghcr.io/zczy-k/bk4app_auto_deploy:latest`

## GitHub 镜像自动构建

仓库内置了 GitHub Actions 工作流，在以下情况会自动构建并推送镜像到 GitHub Container Registry:

- 推送到 `master`
- 推送形如 `v*` 的标签
- 手动触发工作流

镜像地址：`ghcr.io/zczy-k/bk4app_auto_deploy`

常用标签：

- `latest`
- `master`
- `sha-<commit>`
- `vX.Y.Z`

## 拉取镜像部署

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

## 友情链接

https://linux.do/
