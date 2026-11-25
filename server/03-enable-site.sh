#!/usr/bin/env bash
# 第 3 步：启用 Nginx 站点（主站 shuweicao.org + 加密货币收银台 pay.shuweicao.org）
#   证书二选一：
#   1) 服务器上已有 Let's Encrypt 证书 /etc/letsencrypt/live/shuweicao.org/ → 直接用（certbot 自动续期）
#      pay 子域另有 /etc/letsencrypt/live/pay.shuweicao.org/ 时，pay 站点用它；没有就先借用主站证书
#   2) 否则用 Cloudflare 源站证书（*.shuweicao.org 通配，pay 子域也覆盖）：
#      /etc/ssl/cloudflare/origin.pem   /etc/ssl/cloudflare/origin.key
#   证书验证统一走 webroot：/var/www/html/.well-known/acme-challenge/（80 和 443 都放行）
#   注意：同一域名的其他 Nginx 站点（如以前的网站）要先从 sites-enabled 移走，否则会抢 server_name
# 用法：bash 03-enable-site.sh                  启用 / 更新站点配置
#       bash 03-enable-site.sh --issue-pay-cert 另外给 pay.shuweicao.org 申请 Let's Encrypt 证书（用已有的 certbot 账号）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

LE=/etc/letsencrypt/live/shuweicao.org
LE_PAY=/etc/letsencrypt/live/pay.shuweicao.org
WEBROOT=/var/www/html
mkdir -p "$WEBROOT/.well-known/acme-challenge"

if [ -s "$LE/fullchain.pem" ] && [ -s "$LE/privkey.pem" ]; then
  MODE=letsencrypt
  CERT="$LE/fullchain.pem"; KEY="$LE/privkey.pem"
  echo "· 主站使用已有的 Let's Encrypt 证书"
else
  MODE=cloudflare
  CERT=/etc/ssl/cloudflare/origin.pem; KEY=/etc/ssl/cloudflare/origin.key
  mkdir -p /etc/ssl/cloudflare && chmod 700 /etc/ssl/cloudflare
  for f in "$CERT" "$KEY"; do
    [ -s "$f" ] || { echo "缺少 $f：Cloudflare → SSL/TLS → 源服务器 → 创建证书，复制粘贴进来"; exit 1; }
  done
  chmod 600 "$KEY"
fi

render_and_reload() {
  local pay_cert="$CERT" pay_key="$KEY"
  if [ "$MODE" = letsencrypt ]; then
    if [ -s "$LE_PAY/fullchain.pem" ] && [ -s "$LE_PAY/privkey.pem" ]; then
      pay_cert="$LE_PAY/fullchain.pem"; pay_key="$LE_PAY/privkey.pem"
      echo "· pay.shuweicao.org 使用自己的 Let's Encrypt 证书"
    else
      echo "· pay.shuweicao.org 还没有自己的证书，暂时借用主站证书（经 Cloudflare 访问会报 526）；用 --issue-pay-cert 申请"
    fi
  fi
  # 先替换 pay 子域那两行（行尾注释 PAY_CERT / PAY_KEY），再替换其余站点
  sed -e "/# PAY_CERT/ s|/etc/ssl/cloudflare/origin.pem|$pay_cert|" \
      -e "/# PAY_KEY/ s|/etc/ssl/cloudflare/origin.key|$pay_key|" \
      -e "s|/etc/ssl/cloudflare/origin.pem|$CERT|g" -e "s|/etc/ssl/cloudflare/origin.key|$KEY|g" \
      "$SCRIPT_DIR/nginx/shuweicao.conf" > /etc/nginx/sites-available/shuweicao.conf
  chmod 644 /etc/nginx/sites-available/shuweicao.conf
  ln -sf /etc/nginx/sites-available/shuweicao.conf /etc/nginx/sites-enabled/shuweicao.conf
  rm -f /etc/nginx/sites-enabled/default
  sed -i 's/# *server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf
  nginx -t || { echo "✗ Nginx 配置检查没通过，没有重载"; exit 1; }
  systemctl reload nginx
}

render_and_reload

if [ "${1:-}" = "--issue-pay-cert" ]; then
  [ "$MODE" = letsencrypt ] || { echo "· 用的是 Cloudflare 通配源站证书，pay 子域已覆盖，不用另申请"; exit 0; }
  certbot certonly --webroot -w "$WEBROOT" -d pay.shuweicao.org --non-interactive --keep-until-expiring
  render_and_reload
fi
echo "✓ 已启用：https://shuweicao.org   https://pay.shuweicao.org"
