#!/usr/bin/env bash
# 加密备份：商城数据库 + 上传文件 + 配置 + BEpusdt 数据
# 本地 backups/ 保留 7 天；如已配置 rclone 远端，同时上传并保留 30 天
# 线上 cron（每天 4:15）：
#   15 4 * * * /opt/shuweicao/backup.sh >> /var/log/shuweicao-backup.log 2>&1
# 恢复：gpg -d backups/xxx.tar.gz.gpg | tar -xz -C /某个目录
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source .env

STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR=backups
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"; docker unpause shuweicao-bepusdt >/dev/null 2>&1 || true' EXIT

echo "[$(date '+%F %T')] 开始备份"

# 1) 商城 SQLite：在线一致性备份
mkdir -p "$WORK/data"
if [ -f data/db/dujiao.db ]; then
  sqlite3 data/db/dujiao.db ".backup '$WORK/data/dujiao.db'"
else
  echo "⚠ 未找到 data/db/dujiao.db（数据库文件名不同？请检查 data/db/）"
  cp -a data/db "$WORK/data/db"
fi
cp -a data/uploads "$WORK/data/uploads"

# 2) BEpusdt：暂停几秒再拷，避免拷到写了一半的数据
docker pause shuweicao-bepusdt >/dev/null 2>&1 || true
cp -a data/bepusdt "$WORK/data/bepusdt"
docker unpause shuweicao-bepusdt >/dev/null 2>&1 || true

# 3) 配置
cp -a config "$WORK/config"
cp -a .env docker-compose.yml "$WORK/"

# 4) 打包加密
OUT="$OUT_DIR/shuweicao-$STAMP.tar.gz.gpg"
tar -C "$WORK" -czf - . | gpg --batch --yes --pinentry-mode loopback --symmetric \
  --cipher-algo AES256 --passphrase "$BACKUP_PASSPHRASE" -o "$OUT"
chmod 600 "$OUT"
echo "✓ 本地备份 $OUT ($(du -h "$OUT" | cut -f1))"

# 5) 本地保留 7 天
find "$OUT_DIR" -name 'shuweicao-*.tar.gz.gpg' -mtime +7 -delete

# 6) 远端
REMOTE_NAME="${BACKUP_REMOTE%%:*}"
if command -v rclone >/dev/null && rclone listremotes 2>/dev/null | grep -qx "${REMOTE_NAME}:"; then
  rclone copy "$OUT" "$BACKUP_REMOTE/"
  rclone delete --min-age 30d "$BACKUP_REMOTE/" || true
  echo "✓ 已上传 $BACKUP_REMOTE"
else
  echo "⚠ 未配置 rclone 远端「$REMOTE_NAME」，只有本地备份"
fi
echo "[$(date '+%F %T')] 完成"
