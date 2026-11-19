# shuweicao 发卡站

AI 账号自动发卡站，第一个商品是 GPT 成品号。基于开源 [Dujiao-Next](https://github.com/dujiao-next/dujiao-next)，以 Docker Compose 部署在 DigitalOcean，前面是 Cloudflare。

## 文档

| 文档 | 内容 |
| --- | --- |
| [docs/01-business-spec.md](docs/01-business-spec.md) | 业务：目标、上线路线、商品、支付、备案、售后、风险、待拍板事项 |
| [docs/02-tech-spec.md](docs/02-tech-spec.md) | 技术栈：选型、架构、环境、配置、支付对接、安全、二期开发方式 |
| [docs/00-local-setup.md](docs/00-local-setup.md) | 技术准备：在 Mac 上跑起整套系统 |
| [docs/03-deployment-guide.md](docs/03-deployment-guide.md) | 部署：买什么服务器、去哪注册接入、逐步上线、验收 |
| [docs/04-tiance-teardown.md](docs/04-tiance-teardown.md) | 竞品拆解：天策怎么做的，两种开发方向的优缺点 |

## 路线图和进度

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 技术准备：Mac 本地跑通（[00-local-setup](docs/00-local-setup.md)） | ⬜ |
| 1 | 部署上线 shuweicao.org | ⬜ |
| 2 | 上架 GPT 成品号（同时开 USDT） | ⬜ |
| 3 | 国外支付：USDT → Stripe | ⬜ |
| 4 | 国内备案（新域名 + 国内服务器 + 企业主体） | ⬜ 需营业执照 |
| 5 | 国内支付：支付宝官方 | ⬜ |

## 现在就能并行做的事

- [ ] Mac 装 Docker Desktop，按 [00-local-setup](docs/00-local-setup.md) 本地跑起来
- [ ] Cloudflare 添加站点，Spaceship 改 NS（DNS 生效需要时间）
- [ ] 提交 Stripe 账户审核
- [ ] 定 GPT 成品号的价格、货源、质保规则（[业务 spec 第 4 节](docs/01-business-spec.md)）

## 目录

```
docs/           业务 / 技术 / 部署文档
stack/          应用栈（本地和线上共用）：docker-compose.yml、init.sh、backup.sh、upgrade.sh
stack/theme/    白色 + 暖黄主题（样式、首页文案、预览页）
stack/gateway/  在页面中插入主题的 Nginx 配置
server/         线上服务器脚本：初始化、部署、Nginx、Cloudflare IP
```

`stack/.env`、`stack/config/config.yml`、`stack/data/` 含密钥和数据，已在 `.gitignore` 中排除。
