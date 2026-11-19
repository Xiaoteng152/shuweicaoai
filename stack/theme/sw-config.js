/* =========================================================================
   首页文案和链接配置 —— 平时只改这个文件
   改完后把 .env 里的 THEME_VERSION 加 1，再 docker compose up -d gateway，
   让浏览器拿到新文件。
   ========================================================================= */
window.SW_THEME_CONFIG = {
  // 顶部大标题区
  badge: '自动发货 · 订单可查 · 售后保障',
  title: 'GPT 成品号，',
  titleEmphasis: '付款即发货',
  subtitle: '支持 USDT 和银行卡付款。付款成功后，订单页立即显示账号，同时发到你的邮箱。',
  primaryButton: { text: '立即选购', href: '/products' },
  secondaryButton: { text: '游客查单', href: '/guest/orders' },
  tags: ['自动发货', '质保可换', '自助查单'],

  // 右侧卡片
  guestCard: {
    title: '没注册也能查单',
    text: '输入下单时填写的邮箱和订单号，就能看到账号信息和发货状态。',
    linkText: '去查单 →',
    href: '/guest/orders'
  },
  payCard: {
    title: '付款方式',
    methods: [
      { name: 'USDT · TRC20' },
      { name: 'Visa / Mastercard' },
      { name: '支付宝 · 即将开通', soon: true }
    ]
  },

  // 下方：怎么购买
  stepsTitle: '怎么购买',
  steps: [
    { title: '选商品', text: '选好商品，填写接收邮箱' },
    { title: '付款', text: 'USDT 或银行卡，付款即确认' },
    { title: '自动发货', text: '订单页显示账号，邮件同步发送' }
  ],

  // 售后联系（href 留空的项目不显示链接）
  support: [
    { icon: 'TG', title: 'Telegram 客服', text: '@your_tg_id', href: 'https://t.me/your_tg_id' },
    { icon: '@', title: '售后邮箱', text: 'support@shuweicao.org', href: 'mailto:support@shuweicao.org' },
    { icon: '?', title: '售后规则', text: '质保期内不可用包换', href: '/notice' }
  ]
};
