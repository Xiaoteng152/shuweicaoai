#!/usr/bin/env bash
# 第 2 步：把应用栈部署到 /opt/shuweicao（不会覆盖已有的 .env / config.yml / data）
# 用法：cd /root/shuweicao/server && bash 02-deploy-stack.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/../stack"
DEST=/opt/shuweicao
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

mkdir -p "$DEST/config" "$DEST/gateway" "$DEST/theme"
for f in docker-compose.yml .env.example init.sh backup.sh upgrade.sh; do
  install -m 755 "$SRC/$f" "$DEST/$f"
done
chmod 644 "$DEST/docker-compose.yml" "$DEST/.env.example"
cp -n "$SRC/config/README.md" "$DEST/config/" 2>/dev/null || true
# gateway 配置和主题是代码，每次部署都覆盖（docker-compose.yml 会挂载这两个目录）
cp -R "$SRC/gateway/." "$DEST/gateway/"
cp -R "$SRC/theme/." "$DEST/theme/"
chmod -R a+rX "$DEST/gateway" "$DEST/theme"

cd "$DEST"
./init.sh

# 线上默认固定版本，避免 latest 自动变化
if grep -q '^TAG=latest' .env; then
  LATEST=$(curl -fsSL https://api.github.com/repos/dujiao-next/dujiao-next/releases/latest | jq -r .tag_name || true)
  if [ -n "$LATEST" ] && [ "$LATEST" != "null" ]; then
    perl -pi -e "s|^TAG=.*|TAG=$LATEST|" .env
    echo "✓ 已把 TAG 固定为 $LATEST"
  fi
fi

cat <<EOF

下一步：
  1. nano $DEST/config/config.yml       按上面清单修改（线上 server.mode 改 release）
  2. cd $DEST && docker compose up -d gateway               # 不用 USDT 时先不起 bepusdt
  3. docker compose logs dujiao-next | grep 随机密码        # 首次管理员密码
  4. curl -s http://127.0.0.1:8080/health                  # 健康检查
  5. bash $SCRIPT_DIR/03-enable-site.sh                    # 有 Let's Encrypt 证书直接用，否则先放好 Cloudflare 源站证书
EOF
