# 技术准备：在 Mac 上跑起整套系统

> 目的：不花钱、不买服务器，先在本机把商城、后台、发货流程摸熟，确认 Dujiao-Next 满足需求。线上服务器用的是同一份 `stack/`，本地跑通，线上基本就不会出意外。

预计用时：30–60 分钟。

## 1. 装 Docker Desktop

1. 打开 https://www.docker.com/products/docker-desktop/ ，下载 Mac 版（Apple 芯片选 Apple Silicon，Intel 芯片选 Intel）
2. 安装后打开 Docker Desktop，等左下角显示 Engine running
3. 打开「终端」验证：

```bash
docker --version
docker compose version
```

## 2. 初始化

```bash
cd ~/Desktop/my-project/shuweicao/stack
chmod +x *.sh
./init.sh
```

`init.sh` 会：生成 `.env`（随机 Redis 密码）、建 `data/` 目录、下载官方 `config.yml` 模板，并打印**需要修改的配置项和已生成好的密钥**。把这段输出复制保存下来。

## 3. 改配置

```bash
open -e config/config.yml      # 用文本编辑打开，也可以用 VS Code
```

按 `init.sh` 打印的清单修改：三个密钥、`web.admin_path`、数据库路径 `/app/db/dujiao.db`、Redis（host 填 `redis`，密码填 `.env` 里的 `REDIS_PASSWORD`）。本地测试可以先不配邮件。

## 4. 启动

```bash
docker compose up -d
docker compose ps                                       # 四个容器都应为 running
docker compose logs dujiao-next | grep -i password      # 首次随机管理员密码（只显示一次）
curl http://localhost:8080/health                       # 健康检查
```

- 前台：http://localhost:8080
- 后台：http://localhost:8080 + 你设置的 `admin_path`
- USDT 收银台（BEpusdt）：http://localhost:8090 ，安全入口路径见 `docker compose logs bepusdt`

**Apple 芯片报错 `no matching manifest for linux/arm64`**：镜像没有 ARM 版本，执行下面一行再 `docker compose up -d`（会用 Rosetta 模拟，稍慢但可用）：

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

**容器反复重启**：`docker compose logs --tail 100 dujiao-next` 看报错，多数是 config.yml 里的数据库路径或 Redis 配置不对；如果是 `permission denied`，执行 `chmod -R 777 data/db data/uploads data/logs` 后重启。

## 5. 本地要验证的事（技术准备的验收标准）

- [ ] 登录后台，改管理员密码，开启 TOTP 两步验证
- [ ] 熟悉后台：站点设置、商品分类、商品、卡密库存、订单、支付渠道
- [ ] 建一个测试商品「GPT 成品号（测试）」，导入 3 条假卡密，格式 `test1@example.com----pass1----2FA----备注`
- [ ] 前台用游客身份下单，确认订单页、查单流程
- [ ] 在后台把一笔订单手动标记为已付款，确认会自动发出一条卡密、库存减 1
- [ ] 卡密卖完后，商品自动显示缺货
- [ ] 后台把前台模板切换为 **vault**，刷新首页，确认已是白色 + 暖黄主题，首页顶部出现标题区、底部出现「怎么购买」
- [ ] 改 `theme/sw-config.js` 里的文案 → `.env` 的 `THEME_VERSION` 加 1 → `docker compose up -d gateway` → 刷新看到新文案
- [ ] 点右上角切换深色模式，确认深色下也是暖色调
- [ ] （可选）Stripe 测试模式：用 Stripe 的 test key 建渠道。本地收不到 webhook，需装 Stripe CLI 转发：`stripe listen --forward-to localhost:8080/<后台显示的 webhook 路径>`
- [ ] 跑一次备份：`./backup.sh`（Mac 需先 `brew install gnupg`），确认 `backups/` 下生成了加密文件

## 6. 常用命令

| 操作 | 命令 |
| --- | --- |
| 启动 / 停止 | `docker compose up -d` / `docker compose down` |
| 看日志 | `docker compose logs -f dujiao-next` |
| 改配置后重启 | `docker compose restart dujiao-next` |
| 清空重来（删除所有本地数据） | `docker compose down && rm -rf data && ./init.sh` |
| 换版本 | `./upgrade.sh v1.5.1` |
