# shuweicao 发卡站

AI 账号自动发卡站，第一个商品是 GPT 成品号。基于开源 [Dujiao-Next](https://github.com/dujiao-next/dujiao-next)，以 Docker Compose 部署在 DigitalOcean，前面是 Cloudflare。

## 文档

> 接手开发先读 [HANDOFF.md](HANDOFF.md)：当前进度、未验证项、访问权限现状、待办。

| 文档 | 内容 |
| --- | --- |
| [docs/01-business-spec.md](docs/01-business-spec.md) | 业务：目标、上线路线、商品、支付、备案、售后、风险、待拍板事项 |
| [docs/02-tech-spec.md](docs/02-tech-spec.md) | 技术栈：选型、架构、环境、配置、支付对接、安全、二期开发方式 |
| [docs/00-local-setup.md](docs/00-local-setup.md) | 技术准备：在 Mac 上跑起整套系统 |
| [docs/03-deployment-guide.md](docs/03-deployment-guide.md) | 部署：买什么服务器、去哪注册接入、逐步上线、验收 |
| [docs/04-tiance-teardown.md](docs/04-tiance-teardown.md) | 竞品拆解：天策怎么做的，两种开发方向的优缺点 |
| [docs/05-alipay-xorpay.md](docs/05-alipay-xorpay.md) | 支付宝收款：XorPay 个人接口（不用备案、不用营业执照），费用、风险、接入步骤 |

## 路线图和进度

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 技术准备：Mac 本地跑通（[00-local-setup](docs/00-local-setup.md)） | 🟡 已跑通测试订单，主题待看 |
| 1 | 部署上线 shuweicao.org | 🟡 2026-11-20 商城已部署（替换了原来的形象画布），支付渠道待在线上后台配置 |
| 2 | 上架 GPT 成品号（同时开 USDT） | ⬜ |
| 3 | 国外支付：USDT → Stripe | 🟡 加密货币 USDT / USDC（BEpusdt）本地跑通，线上 pay.shuweicao.org 已部署、待填钱包地址和建渠道（[步骤](docs/03-deployment-guide.md)）；Stripe 本地 test 模式跑通（[步骤](docs/00-local-setup.md#7-stripe-测试模式本地)），待上线 |
| 4 | 国内备案（新域名 + 国内服务器 + 企业主体） | ⬜ 需营业执照 |
| 5 | 国内支付：支付宝 | 🟡 走 XorPay 个人接口（不用备案、不用营业执照），转接服务已做好并本地测通，等开通 XorPay（[步骤](docs/05-alipay-xorpay.md)）；支付宝官方仍需执照 + 备案 |

## 现在就能并行做的事

- [x] Mac 装 Docker Desktop，按 [00-local-setup](docs/00-local-setup.md) 本地跑起来
- [x] Cloudflare 添加站点，Spaceship 改 NS（DNS 生效需要时间）
- [ ] 加密货币收款：登录 pay.shuweicao.org 后台，改密码 / 重置对接令牌，填自己的 USDT·TRC20 收款地址，商城后台建 BEpusdt 渠道（[部署指南第 8 步](docs/03-deployment-guide.md)）
- [ ] 开通 XorPay 个人收款（¥100，用自己的支付宝签约），见 [docs/05](docs/05-alipay-xorpay.md) 第 5 节
- [ ] 提交 Stripe 正式账户资料审核（现在用的是沙盒）
- [ ] 定 Stripe 收款规则：美元汇率、是否只收银行卡、是否按买家当地货币显示
- [ ] 定 GPT 成品号的价格、货源、质保规则（[业务 spec 第 4 节](docs/01-business-spec.md)）

## 目录

```
docs/           业务 / 技术 / 部署文档
stack/          应用栈（本地和线上共用）：docker-compose.yml、init.sh、backup.sh、upgrade.sh、stripe-listen.sh（本地测 Stripe）
stack/theme/    白色 + 暖黄主题（样式、首页文案、预览页）
stack/gateway/  在页面中插入主题的 Nginx 配置（也转发 /xorpay/ 回调）
stack/xorpay-bridge/  XorPay ⇄ 易支付 转接服务（支付宝收款），附假 XorPay 和测试；xorpay-setup.sh 填账号
server/         线上服务器脚本：初始化、部署、Nginx、Cloudflare IP
```

`stack/.env`、`stack/config/config.yml`、`stack/data/` 含密钥和数据，已在 `.gitignore` 中排除。
