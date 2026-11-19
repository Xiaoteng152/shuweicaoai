#!/usr/bin/env bash
# 第 3 步：启用 Nginx 站点（先放好 Cloudflare 源站证书）
#   /etc/ssl/cloudflare/origin.pem   /etc/ssl/cloudflare/origin.key
# 用法：bash 03-enable-site.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

mkdir -p /etc/ssl/cloudflare && chmod 700 /etc/ssl/cloudflare
for f in /etc/ssl/cloudflare/origin.pem /etc/ssl/cloudflare/origin.key; do
  [ -s "$f" ] || { echo "缺少 $f：Cloudflare → SSL/TLS → 源服务器 → 创建证书，复制粘贴进来"; exit 1; }
done
chmod 600 /etc/ssl/cloudflare/origin.key

install -m 644 "$SCRIPT_DIR/nginx/shuweicao.conf" /etc/nginx/sites-available/shuweicao.conf
ln -sf /etc/nginx/sites-available/shuweicao.conf /etc/nginx/sites-enabled/shuweicao.conf
rm -f /etc/nginx/sites-enabled/default
sed -i 's/# *server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf

nginx -t && systemctl reload nginx
echo "✓ 已启用：https://shuweicao.org   https://pay.shuweicao.org"
