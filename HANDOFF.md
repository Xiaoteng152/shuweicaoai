# 交接文档：shuweicao 发卡站

> 更新于 2026-11-19 · 给接手的 agent / 开发者。先读本文，再按需读 `docs/`。

## 1. 项目一句话

基于开源 **Dujiao-Next**（v1.5.1，Go + Vue 3）做一个 AI 账号自动发卡站，第一个商品是 **GPT 成品号**。部署方式：Docker Compose，跑在 DigitalOcean，前面是 Cloudflare；外观用"天策式外挂主题"（白色 + 暖黄），不改官方代码。

- 仓库：https://github.com/Xiaoteng152/shuweicaoai （私有，main 分支）
- 用户本地文件夹：`/Users/tengg/Desktop/my-project/shuweicao`（Mac，内容与仓库一致）
- 域名：`shuweicao.org`（Spaceship 注册，2027-09-03 到期，自动续费开）
- 服务器：DigitalOcean Droplet，SFO3，当前 512 MB（建议升 1 GB），IP 137.184.x.x
- 用户沟通语言：中文；偏好简单直接、少术语

## 2. 业务路线（用户确定的顺序）

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 技术准备：Mac 本地用 Docker 跑通 | ⬜ 未开始（用户还没装 Docker / 没跑过） |
| 1 | 部署上线 shuweicao.org | ⬜ |
| 2 | 上架 GPT 成品号 | ⬜ 价格 / 货源 / 质保未定 |
| 3 | 国外支付：USDT（BEpusdt）→ Stripe | ⬜ Stripe 未申请 |
| 4 | 国内备案 | ⬜ 需营业执照；**shuweicao.org 不能备案**（.org 未获工信部批复 + 境外注册商），需新 .com/.cn + 国内服务器 |
| 5 | 国内支付：支付宝官方 | ⬜ 需营业执照 + 企业备案域名；备选易支付 |

建议（已写进 spec）：阶段 2 上架时同时开 USDT，否则无法收款。

## 3. 已完成

- **文档**（`docs/`）：业务 spec、技术 spec、本地准备、部署指南（买什么 / 去哪接入 / 10 步上线）、竞品天策拆解
- **应用栈**（`stack/`）：`docker-compose.yml`（gateway + dujiao-next + redis + bepusdt）、`init.sh`、`backup.sh`、`upgrade.sh`、`.env.example`
- **服务器脚本**（`server/`）：初始化（swap / Docker / ufw / SSH 加固）、部署 stack、启用 Nginx + Cloudflare 源站证书、同步 Cloudflare IP
- **主题**（`stack/theme/` + `stack/gateway/`）：白色 + 暖黄，亮 / 暗两套；首页注入标题区、查单卡片、付款方式、"怎么购买"、售后联系；`preview.html` 静态预览已截图验证
- **竞品调研**：确认天策 = Dujiao-Next vault 模板 + 约 17 个外挂 JS/CSS + 自建 `/tc-stats` 接口

## 4. 未验证 / 已知风险（接手请优先关注）

| 项 | 说明 |
| --- | --- |
| 所有脚本没在真机跑过 | 只做了 `bash -n` 语法检查和 compose YAML 解析；`init.sh` 用假模板跑通过 |
| `config.yml` 字段名 | 只确认了 `app.secret_key`、`jwt.secret`、`user_jwt.secret`、`web.admin_path`、`bootstrap.default_admin_*`、SQLite 路径 `/app/db/dujiao.db`、Redis 主机名 `redis`。`server.mode`、`trusted_proxies`、`cors`、`email` 的确切键名以官方 `config.yml.example` 为准 |
| 主题只在静态预览里验证 | 依据官方 `frontend/user/src/templates/vault/styles/vault.css` 的变量名（`--bg`、`--red` 主色、`--gold` 等，作用域 `.vault-scope` / `body.vault-tokens`）和 `VaultLayout.vue` 结构（`.vault-scope > main` 第一个子元素是页面根）。需在真实商城里确认，且后台须把前台模板切到 **vault** |
| gateway `sub_filter` 注入 | 依赖响应未压缩（已设 `Accept-Encoding ""`）；`${THEME_VERSION}` 靠 nginx 官方镜像 envsubst 替换 |
| 容器权限 | `data/` 目录若报 permission denied，按文档 `chmod` 处理；镜像内用户 uid 未确认 |
| Apple 芯片 | `dujiaonext/dujiao-next` 是否有 arm64 镜像未确认；无则 `DOCKER_DEFAULT_PLATFORM=linux/amd64` |
| BEpusdt | 用 `v03413/bepusdt` 镜像、数据卷 `/var/lib/bepusdt`、容器端口 8080 映射到 8090；首次配置走它的 Web 向导，细节未实测 |
| Stripe | 转售账号类业务可能被判禁止行业；文档已提示 USDT 为主通道 |
| 许可证 | Dujiao-Next 文档写 MIT、仓库标 GPL-3.0，二次开发前需确认 |

## 5. 访问与工具现状（重要，省得再踩坑）

- **GitHub MCP 插件**（Claude Github MCP Connector）：已安装到 `shuweicaoai`（仅此仓库），**可读写文本文件**（`push_files` / `create_or_update_file`）。**不能新建仓库**（403），**不能传二进制**（图片会损坏）
- **claude.ai 的 GitHub 账号关联未生效**：`add_repo` / `list_repos` 仍报 "no GitHub account linked"，所以无法 git clone。用户已在 GitHub 装了 Claude App（当前是 All repositories，建议改成仅 shuweicaoai），但 claude.ai 侧关联未完成
- **云端容器里的 `gh` 凭据失效**（GH_TOKEN invalid），Bash 无外网
- **用户 Mac 的 device_bash 隔离环境**：访问不了 GitHub（代理 403），且文件夹挂载失败；可用 `device_list_dir / device_stage_files / device_commit_files` 读写 `/Users/tengg/Desktop/my-project/shuweicao`
- **内置浏览器**：已登录用户的 GitHub
- Claude in Chrome 扩展：未连接

## 6. 待办（按优先级）

1. **补传两张图片**：`docs/architecture.png`、`docs/theme-preview.png`（在用户 Mac 文件夹里有，仓库里没有）。方法：用户在 Mac 终端执行
   ```bash
   cd ~/Desktop/my-project/shuweicao
   git init -b main && git remote add origin https://github.com/Xiaoteng152/shuweicaoai.git
   git fetch origin && git reset origin/main
   git add docs/architecture.png docs/theme-preview.png
   git commit -m "docs: add images" && git push -u origin main
   ```
   （需先 `gh auth login` + `gh auth setup-git`），或网页 Upload files
2. **阶段 0**：带用户在 Mac 装 Docker Desktop，按 `docs/00-local-setup.md` 跑起来，修正脚本 / 配置里发现的问题（尤其 config.yml 键名、主题实际效果）
3. **用户待拍板**：GPT 成品号的名称 / 价格 / 货源 / 质保；有无营业执照；Stripe 主体；售后 TG 和邮箱（`stack/theme/sw-config.js` 里现在是占位 `@your_tg_id`、`support@shuweicao.org`）
4. **阶段 1 准备**（用户操作）：Droplet 升 1 GB；Cloudflare 添加站点 + Spaceship 改 NS + 3 条 A 记录；生成源站证书；提交 Stripe 申请
5. 完成 claude.ai ↔ GitHub 关联（之后可直接 git clone 整体开发）

## 7. 已作废的东西（不要再用）

- 用户 Windows 电脑 `C:\Users\TengG\Desktop\shuweicao\deploy\`：旧的"单二进制 + systemd"方案
- claude.ai 上的在线文档《shuweicao.org 发卡站技术方案 Spec》：同样是旧方案，以仓库 `docs/` 为准

## 8. 关键参考

- Dujiao-Next：https://github.com/dujiao-next/dujiao-next （前台源码在 `frontend/user/src/`，vault 模板在 `templates/vault/`）
- Docker 部署文档：https://dujiao-next.com/deploy/docker-compose （镜像 `dujiaonext/dujiao-next:${TAG}`，挂载 `/app/config.yml`、`/app/db`、`/app/uploads`、`/app/logs`，健康检查 `/health`，首次管理员密码可由 `DJ_DEFAULT_ADMIN_PASSWORD` 留空自动生成并打印到日志）
- 竞品：https://tiancexai.com/ （拆解见 `docs/04-tiance-teardown.md`）
