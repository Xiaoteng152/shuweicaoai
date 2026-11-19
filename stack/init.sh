#!/usr/bin/env bash
# 初始化应用栈（Mac 本地和 Linux 服务器通用，可重复运行，不会覆盖已有文件）
#   1. 生成 .env（随机 Redis 密码、备份口令）
#   2. 建 data/ 目录
#   3. 下载对应版本的 config.yml.example，第一次时复制成 config/config.yml
#   4. 打印 config.yml 需要修改的项（密钥已随机生成好）
# 用法：cd stack && ./init.sh
set -euo pipefail
cd "$(dirname "$0")"

REPO=dujiao-next/dujiao-next
rand() { openssl rand -hex "$1"; }
# 跨平台的就地替换（macOS 的 sed -i 语法不同，用 perl）
set_env() { perl -pi -e "s|^$1=.*|$1=$2|" .env; }

# ---- 1. .env ----
if [ ! -f .env ]; then
  cp .env.example .env
  set_env REDIS_PASSWORD "$(rand 24)"
  set_env BACKUP_PASSPHRASE "$(rand 32)"
  chmod 600 .env
  echo "✓ 已生成 .env"
else
  echo "· .env 已存在，保留"
fi
# shellcheck disable=SC1091
source .env

# ---- 2. 目录 ----
mkdir -p config data/db data/uploads data/logs data/redis data/bepusdt
echo "✓ data/ 目录就绪"

# ---- 3. config.yml ----
REF="${TAG:-latest}"
[ "$REF" = "latest" ] && REF=main
if [ ! -f config/config.yml.example ] || [ "${1:-}" = "--refresh-example" ]; then
  echo "· 下载 config.yml.example（$REF）"
  curl -fsSL "https://raw.githubusercontent.com/$REPO/$REF/config.yml.example" -o config/config.yml.example \
    || curl -fsSL "https://raw.githubusercontent.com/$REPO/main/config.yml.example" -o config/config.yml.example \
    || { echo "✗ 下载失败。手动从 https://github.com/$REPO 下载 config.yml.example 放到 stack/config/"; exit 1; }
fi

if [ -f config/config.yml ]; then
  echo "· config/config.yml 已存在，保留。"
  exit 0
fi

cp config/config.yml.example config/config.yml
chmod 600 config/config.yml
echo "✓ 已生成 config/config.yml"

cat <<EOF

=====================================================================
请编辑 stack/config/config.yml，至少修改以下几项（字段名以文件内注释为准）：

  app.secret_key    $(rand 32)
  jwt.secret        $(rand 32)
  user_jwt.secret   $(rand 32)
      ↑ 三个已随机生成，直接复制；三者必须不同。
        app.secret_key 要和数据库一起备份，丢了旧数据可能无法解密。

  web.admin_path    /m-$(rand 6)
      ↑ 后台入口，不要用默认的 /admin

  数据库            SQLite，路径 /app/db/dujiao.db（容器内路径）
  redis             host: redis   port: 6379   password: ${REDIS_PASSWORD}
  server.mode       本地可保持默认；线上改为 release
  trusted_proxies   127.0.0.1 和 172.16.0.0/12（商城前面有 gateway 容器，用于识别真实 IP）
  cors              线上只允许 https://shuweicao.org
  email / smtp      发卡密邮件用，本地测试可以先不配

改完后启动：
  docker compose up -d
  docker compose logs dujiao-next | grep -i password    # 首次随机管理员密码
本地访问：http://localhost:${APP_PORT:-8080}   后台：http://localhost:${APP_PORT:-8080}<你的 admin_path>
=====================================================================
EOF
