#!/usr/bin/env bash
# 升级 / 回滚 Dujiao-Next：先备份，再改 .env 里的 TAG，拉新镜像重启
# 用法：./upgrade.sh v1.5.1        （版本号见 https://github.com/dujiao-next/dujiao-next/releases）
# 回滚：./upgrade.sh <旧版本号>；若新版本已改动数据库结构，还需从备份恢复 data/db
set -euo pipefail
cd "$(dirname "$0")"

NEW="${1:-}"
[ -n "$NEW" ] || { echo "用法：./upgrade.sh <版本号，如 v1.5.1>"; exit 1; }
OLD=$(grep '^TAG=' .env | cut -d= -f2)
echo "当前 $OLD → 目标 $NEW（升级前请先看 release note）"
read -r -p "确认？[y/N] " ok
[ "$ok" = "y" ] || exit 0

./backup.sh
perl -pi -e "s|^TAG=.*|TAG=$NEW|" .env
docker compose pull dujiao-next
docker compose up -d dujiao-next
sleep 8
if [ "$(docker inspect -f '{{.State.Running}}' shuweicao-dujiao)" = "true" ]; then
  echo "✓ 已运行 $NEW。检查日志：docker compose logs --tail 50 dujiao-next"
else
  echo "✗ 启动失败，查看：docker compose logs --tail 100 dujiao-next"
  echo "  回滚：./upgrade.sh $OLD"
  exit 1
fi
