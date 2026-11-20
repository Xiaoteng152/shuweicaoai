#!/usr/bin/env bash
# 第 1 步：新服务器初始化（Ubuntu 22.04 / 24.04，root 运行，可重复执行）
#   系统更新 · 2 GB swap · Docker · Nginx · sqlite3/rclone/gpg
#   ufw：22 放行，80/443 只放行 Cloudflare · SSH 加固 · fail2ban · 自动安全更新
# 用法：cd /root/shuweicao/server && bash 01-server-init.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
log() { echo -e "\n\033[1;32m==> $*\033[0m"; }
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }

log "更新系统、安装依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y nginx sqlite3 fail2ban unattended-upgrades ufw curl jq rclone gnupg perl ca-certificates openssl
dpkg-reconfigure -f noninteractive unattended-upgrades || true

log "swap"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf && sysctl -p /etc/sysctl.d/99-swappiness.conf
else
  echo "已有 swap，跳过"
fi

log "Docker"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

log "防火墙"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
bash "$SCRIPT_DIR/cloudflare-ips.sh"

log "SSH 加固"
{
  echo "PermitRootLogin prohibit-password"
  if [ -s /root/.ssh/authorized_keys ]; then
    echo "PasswordAuthentication no"
    echo "KbdInteractiveAuthentication no"
  fi
} > /etc/ssh/sshd_config.d/99-shuweicao.conf
[ -s /root/.ssh/authorized_keys ] && echo "已关闭密码登录" || echo "⚠ 未检测到 SSH 公钥，暂不关闭密码登录；配好密钥后重跑本脚本"
sshd -t && systemctl restart ssh

systemctl enable --now fail2ban
log "完成。下一步：bash $SCRIPT_DIR/02-deploy-stack.sh"
