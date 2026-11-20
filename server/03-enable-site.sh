#!/usr/bin/env bash
# 第 3 步：启用 Nginx 站点
#   证书二选一：
#   1) 服务器上已有 Let's Encrypt 证书 /etc/letsencrypt/live/shuweicao.org/ → 直接用（certbot 自动续期）
#   2) 否则用 Cloudflare 源站证书：/etc/ssl/cloudflare/origin.pem   /etc/ssl/cloudflare/origin.key
#   注意：同一域名的其他 Nginx 站点（如以前的网站）要先从 sites-enabled 移走，否则会抢 server_name
# 用法：bash 03-enable-site.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

LE=/etc/letsencrypt/live/shuweicao.org
if [ -s "$LE/fullchain.pem" ] && [ -s "$LE/privkey.pem" ]; then
  CERT="$LE/fullchain.pem"; KEY="$LE/privkey.pem"
  echo "· 使用已有的 Let's Encrypt 证书（只覆盖 shuweicao.org / www；以后开 pay 子域要另申请）"
else
  CERT=/etc/ssl/cloudflare/origin.pem; KEY=/etc/ssl/cloudflare/origin.key
  mkdir -p /etc/ssl/cloudflare && chmod 700 /etc/ssl/cloudflare
  for f in "$CERT" "$KEY"; do
    [ -s "$f" ] || { echo "缺少 $f：Cloudflare → SSL/TLS → 源服务器 → 创建证书，复制粘贴进来"; exit 1; }
  done
  chmod 600 "$KEY"
fi

sed -e "s|/etc/ssl/cloudflare/origin.pem|$CERT|g" -e "s|/etc/ssl/cloudflare/origin.key|$KEY|g" \
  "$SCRIPT_DIR/nginx/shuweicao.conf" > /etc/nginx/sites-available/shuweicao.conf
chmod 644 /etc/nginx/sites-available/shuweicao.conf
ln -sf /etc/nginx/sites-available/shuweicao.conf /etc/nginx/sites-enabled/shuweicao.conf
rm -f /etc/nginx/sites-enabled/default
sed -i 's/# *server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf

nginx -t || { echo "✗ Nginx 配置检查没通过，没有重载"; exit 1; }
systemctl reload nginx
echo "✓ 已启用：https://shuweicao.org"
