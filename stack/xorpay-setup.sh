#!/usr/bin/env bash
# 填写 XorPay 账号（aid / app secret）并启动转接服务。密钥只写进本机 .env，不经过任何人。
# 线上（在你自己的电脑终端里运行）：
#   ssh -t root@<服务器IP> 'cd /opt/shuweicao && ./xorpay-setup.sh'
# 本地：cd stack && ./xorpay-setup.sh
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "✗ 没有 .env，先运行 ./init.sh"; exit 1; }

# 有这一行就替换，没有就追加（值里有特殊字符也安全）
set_env() {
  if grep -q "^$1=" .env; then
    K="$1" V="$2" perl -pi -e 's/^\Q$ENV{K}\E=.*/$ENV{K}=$ENV{V}/' .env
  else
    printf '%s=%s\n' "$1" "$2" >> .env
  fi
}

echo "XorPay 后台 → 账号信息里能看到 aid 和 app secret"
read -r -p "aid: " AID
read -r -s -p "app secret（输入时不显示）: " SECRET; echo
[ -n "$AID" ] && [ -n "$SECRET" ] || { echo "✗ 两项都不能为空"; exit 1; }
case "$AID$SECRET" in *[[:space:]]*) echo "✗ 里面有空格，检查是不是多复制了"; exit 1 ;; esac
set_env XORPAY_AID "$AID"
set_env XORPAY_APP_SECRET "$SECRET"

CURRENT_URL=$(grep '^PUBLIC_BASE_URL=' .env | cut -d= -f2- || true)
case "$CURRENT_URL" in
  https://*) ;;
  *) read -r -p "站点公网地址 [https://shuweicao.org]: " URL
     set_env PUBLIC_BASE_URL "${URL:-https://shuweicao.org}" ;;
esac
grep -q '^XORPAY_API_BASE=' .env || set_env XORPAY_API_BASE https://xorpay.com
chmod 600 .env

docker compose up -d xorpay-bridge
sleep 2
docker compose logs --no-log-prefix --tail 2 xorpay-bridge

cat <<EOF

✓ 已保存并启动转接服务。接着到商城后台 → 支付渠道 → 新建：
  名称           支付宝
  提供方 / 渠道  易支付 / 支付宝（alipay），交互方式：扫码
  网关地址       http://xorpay-bridge:8080
  易支付版本     v1，签名类型 MD5
  商户号         $AID
  商户密钥       刚才输入的 app secret
  异步通知地址   http://dujiao-next:8080/api/v1/payments/callback
  同步跳转地址   $(grep '^PUBLIC_BASE_URL=' .env | cut -d= -f2-)/pay
  单笔最高金额   1000（个人身份的支付宝单笔上限），并勾选「超出范围时隐藏」
EOF
