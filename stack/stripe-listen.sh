#!/usr/bin/env bash
# 本地测试 Stripe：把 Stripe 的付款事件（Webhook）转发到本机商城
#   Stripe 访问不到你的电脑，所以本地测试时用官方 Stripe CLI 中转。线上不用这个脚本，
#   线上在 Stripe 后台 Developers → Webhooks 直接填 https://shuweicao.org/api/v1/payments/webhook/stripe?channel_id=<渠道ID>
#
# 准备：
#   1. brew install stripe/stripe-cli/stripe
#   2. .env 里填 STRIPE_TEST_SECRET_KEY（只能是 sk_test_ 开头的 test 密钥）和 STRIPE_CHANNEL_ID（后台 Stripe 渠道的 ID）
#   3. 后台 Stripe 渠道的 webhook_secret 填 ./stripe-listen.sh --print-secret 打印出的 whsec_...（同一台电脑上一般不变）
#
# 用法：
#   cd stack && ./stripe-listen.sh                 # 开始转发，测试期间保持运行，Ctrl+C 停止
#   cd stack && ./stripe-listen.sh --print-secret  # 只打印 webhook 签名密钥
set -euo pipefail
cd "$(dirname "$0")"

command -v stripe >/dev/null || { echo "✗ 没装 Stripe CLI：brew install stripe/stripe-cli/stripe"; exit 1; }
# shellcheck disable=SC1091
source .env
: "${STRIPE_TEST_SECRET_KEY:?先在 stack/.env 里填 STRIPE_TEST_SECRET_KEY（sk_test_ 开头）}"
case "$STRIPE_TEST_SECRET_KEY" in
  sk_test_*|rk_test_*) ;;
  *) echo "✗ STRIPE_TEST_SECRET_KEY 必须是 test 密钥（sk_test_ / rk_test_ 开头），正式密钥不要放在本机"; exit 1 ;;
esac

# 开着代理（如 Clash）但代理连不上 Stripe 时，Stripe CLI 会一直卡在 "Getting ready..."：这种情况自动改为直连
if [ -n "${HTTPS_PROXY:-}${https_proxy:-}${ALL_PROXY:-}${all_proxy:-}" ] \
   && ! curl -s -o /dev/null -m 6 https://api.stripe.com/ \
   && curl -s --noproxy '*' -o /dev/null -m 6 https://api.stripe.com/; then
  echo "· 代理连不上 Stripe，本次改为直连"
  unset HTTPS_PROXY https_proxy HTTP_PROXY http_proxy ALL_PROXY all_proxy
fi

if [ "${1:-}" = "--print-secret" ]; then
  exec stripe listen --api-key "$STRIPE_TEST_SECRET_KEY" --print-secret
fi

URL="http://localhost:${APP_PORT:-8080}/api/v1/payments/webhook/stripe?channel_id=${STRIPE_CHANNEL_ID:-1}"
echo "→ 转发 Stripe 事件到 $URL（Ctrl+C 停止）"
exec stripe listen --api-key "$STRIPE_TEST_SECRET_KEY" \
  --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired \
  --forward-to "$URL"
