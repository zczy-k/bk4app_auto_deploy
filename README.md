Backup4App 容器自动重新部署。

这个项目的目标是长期保活 Back4App 应用。

运行逻辑如下：

- 容器启动后运行 `scheduler.py`
- 按 `CRON_SCHEDULE` 定时执行 `auto_redeploy.py`
- 每次执行都会检查 Back4App 应用状态
- 如果应用状态是 `EXPIRED`，立即触发重新部署
- 如果本地没有可用 `BACK4APP_COOKIE`，会尝试使用账号密码自动重新获取

## 适用场景

- 自己的 Linux 服务器
- Docker 环境
- 支持自定义镜像的云平台
- 支持从 GHCR 拉取镜像的容器平台

## 镜像地址

GitHub Container Registry 镜像地址：

`ghcr.io/zczy-k/bk4app_auto_deploy:latest`

常用标签：

- `latest`
- `master`
- `sha-<commit>`
- `vX.Y.Z`

## 环境变量

最小必需配置：

```env
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
PORT=7860
RUN_ON_STARTUP=true
```

推荐完整配置：

```env
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
BACK4APP_COOKIE=可选，当前有效Cookie
CRON_SCHEDULE=*/1 * * * *
PORT=7860
LOG_LEVEL=INFO
RUN_ON_STARTUP=true
APP_ID_MAP_JSON={}
```

变量说明：

- `BACK4APP_EMAIL`：Back4App 登录邮箱
- `BACK4APP_PASSWORD`：Back4App 登录密码
- `BACK4APP_COOKIE`：可选。已有可用 Cookie 时建议一起提供，启动更快
- `CRON_SCHEDULE`：检查频率，默认 `*/1 * * * *`，表示每 1 分钟检查一次
- `PORT`：健康检查端口，默认 `7860`
- `LOG_LEVEL`：日志级别，建议 `INFO`
- `RUN_ON_STARTUP`：容器启动后立即执行一次检查，建议设为 `true`
- `APP_ID_MAP_JSON`：多应用映射表，单应用可保持 `{}`

说明：

- 最小可用配置只需要 `BACK4APP_EMAIL`、`BACK4APP_PASSWORD`、`PORT`、`RUN_ON_STARTUP`
- `CRON_SCHEDULE` 不写时，默认就是每 1 分钟检查一次
- `LOG_LEVEL` 不写时，默认就是 `INFO`
- `APP_ID_MAP_JSON` 不写时，程序会按空映射处理，并在需要时自动补全
- `BACK4APP_COOKIE` 会过期，不建议只依赖 Cookie
- 推荐同时设置 `BACK4APP_EMAIL`、`BACK4APP_PASSWORD`、`BACK4APP_COOKIE`
- 如果 Cookie 失效，程序会尝试用邮箱密码重新获取

## 服务器部署

### 方式一：使用仓库源码本地构建

1. 克隆仓库

```bash
git clone https://github.com/zczy-k/bk4app_auto_deploy.git
cd bk4app_auto_deploy
```

2. 复制环境变量模板

```bash
cp .env.example .env
```

3. 编辑 `.env`

```env
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
PORT=7860
RUN_ON_STARTUP=true
```

如果你想显式写全所有配置，再使用推荐完整配置。

4. 启动

```bash
docker compose up -d --build
```

5. 查看日志

```bash
docker compose logs -f
```

### 方式二：直接拉取 GHCR 镜像

1. 准备 `.env`

```bash
cat > .env <<'EOF'
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
PORT=7860
RUN_ON_STARTUP=true
EOF
```

如果你希望手动覆盖默认行为，可以再补充 `BACK4APP_COOKIE`、`CRON_SCHEDULE`、`LOG_LEVEL`、`APP_ID_MAP_JSON`。

2. 拉取镜像

```bash
docker pull ghcr.io/zczy-k/bk4app_auto_deploy:latest
```

3. 启动容器

```bash
docker run -d \
  --name auto_deploy \
  --restart unless-stopped \
  --env-file .env \
  -p 7860:7860 \
  -v $(pwd)/.env:/app/.env \
  ghcr.io/zczy-k/bk4app_auto_deploy:latest
```

4. 查看日志

```bash
docker logs -f auto_deploy
```

## 通用云平台部署

适用于爪云、1Panel 应用商店、自建 PaaS、支持自定义镜像的容器平台。

平台侧通常只需要配置这几项：

- 镜像：`ghcr.io/zczy-k/bk4app_auto_deploy:latest`
- 容器端口：`7860`
- 健康检查路径：`/health`
- 启动命令：留空
- 环境变量：优先使用上面的最小必需配置

平台最小环境变量：

```env
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
PORT=7860
RUN_ON_STARTUP=true
```

平台推荐完整环境变量：

```env
BACK4APP_EMAIL=你的Back4App登录邮箱
BACK4APP_PASSWORD=你的Back4App登录密码
BACK4APP_COOKIE=你的当前有效Cookie
CRON_SCHEDULE=*/1 * * * *
PORT=7860
LOG_LEVEL=INFO
RUN_ON_STARTUP=true
APP_ID_MAP_JSON={}
```

建议把以下变量设成密文或 Secret：

- `BACK4APP_EMAIL`
- `BACK4APP_PASSWORD`
- `BACK4APP_COOKIE`

说明：

- 平台部署时一般不需要额外填写启动命令
- 如果平台不支持挂载 `.env` 文件，只配置环境变量也可以运行
- 但如果平台不持久化容器文件，程序写回的新 Cookie 不一定会保留到下次重建
- 因此推荐始终保留账号密码，作为 Cookie 失效后的兜底方式

## 健康检查

健康检查接口：

- `GET /`
- `GET /health`
- `GET /healthz`

建议平台健康检查路径填：

`/health`

## 如何判断是否运行正常

启动后日志里通常会看到以下内容：

- `Health server listening on 0.0.0.0:7860`
- `Scheduler started, cron=*/1 * * * *`
- `Running auto_redeploy.py at ...`
- `Fetched X apps`

如果容器启动时没有有效 Cookie，还可能看到：

- `Refreshing cookie on startup`
- `Starting cookie fetch`

## 调度说明

`CRON_SCHEDULE=*/1 * * * *` 的意思是：

- 每 1 分钟检查一次 Back4App 应用状态
- 如果应用正常，不会重新部署
- 如果应用状态为 `EXPIRED`，会立即触发重新部署

如果你只是想降低检查频率，也可以改成：

- `*/5 * * * *`：每 5 分钟检查一次
- `*/10 * * * *`：每 10 分钟检查一次

但如果你的应用大约 1 小时就可能失效，推荐继续使用：

`CRON_SCHEDULE=*/1 * * * *`

## 常见问题

### 1. 镜像拉取失败

如果平台提示无法拉取 `ghcr.io/zczy-k/bk4app_auto_deploy:latest`，通常是因为 GHCR 包还不是公开状态。

需要去 GitHub 仓库对应的 `Packages` 页面，把镜像包改成 `public`。

### 2. 登录失败或无法自动获取 Cookie

通常原因有：

- `BACK4APP_EMAIL` 或 `BACK4APP_PASSWORD` 填错
- Back4App 登录流程出现验证码或二次验证
- 登录页面发生变化，导致 Playwright 无法找到输入框

### 3. Cookie 有效但过一段时间失效

这是正常现象，Cookie 不是永久有效凭证。

所以建议：

- 不要只配置 `BACK4APP_COOKIE`
- 同时配置 `BACK4APP_EMAIL` 和 `BACK4APP_PASSWORD`

### 4. 容器运行正常但没有触发部署

需要确认：

- Back4App 返回的状态是否确实是 `EXPIRED`
- 日志中是否能正常获取应用列表
- `APP_ID_MAP_JSON` 是否为空或已被程序自动补全

## 镜像自动构建

仓库内置 GitHub Actions 工作流，在以下情况会自动构建并推送镜像到 GHCR：

- 推送到 `master`
- 推送形如 `v*` 的标签
- 手动触发工作流

镜像仓库地址：

`ghcr.io/zczy-k/bk4app_auto_deploy`

## 友情链接

https://linux.do/
