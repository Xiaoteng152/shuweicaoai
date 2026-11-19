#!/usr/bin/env bash
# 拉取 Cloudflare 最新 IP 段，做两件事：
#   1) 生成 Nginx real_ip 配置，让日志和 Dujiao 拿到顾客真实 IP
#   2) ufw 只允许 Cloudflare 访问 80/443（防止有人绕过 Cloudflare 直连源站）
# 用法：sudo bash cloudflare-ips.sh        （01-server-init.sh 会自动调用；建议每周 cron 跑一次）
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

V4=$(curl -fsS https://www.cloudflare.com/ips-v4)
V6=$(curl -fsS https://www.cloudflare.com/ips-v6)
[ -n "$V4" ] && [ -n "$V6" ] || { echo "拉取 Cloudflare IP 失败"; exit 1; }

# ---- 1) Nginx real_ip ----
CONF=/etc/nginx/conf.d/cloudflare-realip.conf
{
  echo "# 自动生成于 $(date -Is)，不要手改"
  for ip in $V4 $V6; do echo "set_real_ip_from $ip;"; done
  echo "real_ip_header CF-Connecting-IP;"
} > "$CONF"
nginx -t && systemctl reload nginx
echo "已写入 $CONF"

# ---- 2) ufw ----
# 先删掉旧的 Cloudflare 规则（带注释 cloudflare 的）
while :; do
  STATUS=$(ufw status numbered)
  LINE=$(grep -m1 'cloudflare' <<<"$STATUS" || true)
  [ -n "$LINE" ] || break
  n=$(sed -E 's/^\[ *([0-9]+)\].*/\1/' <<<"$LINE")
  ufw --force delete "$n" >/dev/null
done
for ip in $V4 $V6; do
  ufw allow proto tcp from "$ip" to any port 80,443 comment cloudflare >/dev/null
done
echo "ufw 已更新：80/443 仅放行 Cloudflare"
