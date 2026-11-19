# 竞品拆解：天策AI（tiancexai.com）是怎么做的

> 2026-11-19 · 只看公开页面：HTML、加载的前端文件、未登录状态下的接口请求。未登录、未下单、未访问任何受保护内容。

## 结论

**天策 = 官方 Dujiao-Next（vault 模板）+ 一层"外挂"的自定义 JS/CSS + 一个自己写的小接口。** 他们没有自研商城，也很可能没有 fork 前台源码重新编译，而是在官方编译好的前台上面"贴"了一层东西。

## 证据

| 观察到的 | 说明 |
| --- | --- |
| 接口 `/api/v1/public/config`、`/public/products`、`/public/categories`、`/public/posts`、`/public/affiliate/click` | Dujiao-Next 的标准公开接口 |
| 前端文件 `VaultLayout-*.js`、`Home`、`Products`、`ProductDetail`、`Cart`、`Checkout`、`Payment`、`GuestOrderDetail`、`OnchainTransactionConfirm` | 和 Dujiao-Next 仓库 `frontend/user/src/templates/vault` 及 `views/` 下的文件一一对应 |
| Vue 3.5 + vue-i18n + Vite 打包的带哈希文件名 | 与官方前台技术栈一致 |
| 商品图在 `/uploads/product/2026/10/...` | Dujiao-Next 的上传目录结构 |
| 额外加载约 17 个 `tiance-*.js` / `tiance-*.css`：首页 v3、商品详情 v4、等级对比、运营卡片、下单验证码、推广兑换、团队提现、充值入口、深色主题等，带 `?v=日期` 版本号 | 自定义层，直接插在 index.html 里 |
| 一段 import map，把官方的 `GuestOrderDetail-xxx.js` 等文件**替换成** `…-portal-20261117.js` | 用"替换编译产物"的方式改官方页面，而不是改源码重新编译 |
| `/tc-stats/tiers` 接口（不是 `/api/v1` 下的） | 自己另写的小服务，用于合伙人等级 / 累计消费展示 |
| `cdn-cgi/challenge-platform`、`cloudflareinsights` | 前面是 Cloudflare，开了人机校验和访问统计 |
| `data-telegram-mini-app` | 支持在 Telegram 小程序里打开 |
| 付款方式：支付宝、USDT（BSC / ARB 链） | Dujiao-Next 内置的支付能力 |

## 修正我们之前的判断

查看 Dujiao-Next 当前仓库（最新版 v1.5.1）后发现，它已经**自带**以下前台模块，之前 spec 里写「需要二次开发」是错的：

| 模块 | 仓库里的页面 | 对应天策功能 |
| --- | --- | --- |
| 推广返佣 | `views/personal/AffiliatePanel.vue` | 推广一起赚钱 |
| 钱包 / 余额 | `WalletPanel.vue` | 余额、提现 |
| 礼品卡（卡密充值） | `GiftCardPanel.vue` | 卡密兑换 |
| 开放 API | `ApiPanel.vue` | API 自动充值 |
| 分销商 / 分站 | `views/reseller/`（申请、控制台、域名、站点配置、订单、财务、提现） | 分站搭建 |

天策真正自己做的部分主要是：**首页和商品页的视觉重做**、**按累计消费自动升级的合伙人等级展示**、以及一些运营小工具。

## 两个开发方向对比

### 方向一：天策式「外挂层」—— 不动官方代码，在编译好的页面上叠加自定义 JS / CSS

| 优点 | 缺点 |
| --- | --- |
| 官方版本直接用，升级时自定义层基本独立 | 依赖官方页面结构和 class 名，官方一升级改了页面就可能失效 |
| 上手快：一个 JS 或 CSS 文件就能上线一个改动 | 用 import map 替换编译文件的做法最脆弱：每次升级文件名哈希都变，要重做 |
| 不需要搭构建流水线 | 页面先显示原版再被脚本改，可能闪一下；脚本越多首屏越慢 |
| 不涉及修改源码的许可证问题 | 代码散落在十几个文件里，难测试、难交接 |
| | 只能改展示；涉及价格、权限、结算的逻辑必须另写后端（所以天策另起了 `/tc-stats` 服务） |

### 方向二：fork 源码 —— 在 Dujiao-Next 的 Vue 前台（必要时 Go 后端）里正规修改，自己构建镜像

| 优点 | 缺点 |
| --- | --- |
| 改得彻底干净：直接写 Vue 组件，有类型检查，可测试 | 每次官方更新都要合并，改得越多冲突越多 |
| 前后端都能改：等级价、自动升级可以做成真正的后端逻辑 | 要搭构建和发布流程（GitHub Actions 打镜像） |
| 没有闪烁、性能好 | 需要会 Vue（以及 Go）的开发者 |
| 可以用官方的模板机制（`templates/`）新增一套自己的模板，减少和上游冲突 | 仓库许可证需确认（文档写 MIT、仓库标 GPL-3.0），fork 后对外服务可能有开源义务 |

## 建议

1. **第一步不写代码**：用官方 vault 模板 + 后台配置（logo、配色、公告、商品图、文案）上线，并先试用自带的推广返佣、钱包、分销商功能，确认够不够用。
2. **只改外观时**：参考天策，用少量自定义 CSS 叠加即可，成本最低。
3. **要做等级价、自动升级这类涉及钱的逻辑时**：走方向二，在源码里新增一套自己的模板并改后端，不要用前端脚本硬改。
4. 布局可以参考，但视觉、文案、品牌用自己的，不复制天策的页面和素材。
