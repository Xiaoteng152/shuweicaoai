/* =========================================================================
   shuweicao 首页区块注入
   - 只在 vault 模板（页面里有 .vault-scope）且当前是首页 "/" 时生效
   - 在首页最上方插入：标题区 + 查单卡片 + 付款方式
   - 在首页最下方插入：怎么购买 + 售后联系
   - 离开首页时自动移除；回到首页自动加回（单页应用路由切换）
   - 文案全部来自 sw-config.js；所有文字用 textContent 写入，不拼 HTML
   ========================================================================= */
(function () {
  'use strict';

  var TOP_ID = 'sw-home-top';
  var BOTTOM_ID = 'sw-home-bottom';

  function cfg() {
    return window.SW_THEME_CONFIG || {};
  }

  function isHome() {
    if (window.SW_THEME_FORCE_HOME) return true; // 仅 preview.html 使用
    return location.pathname === '/' || location.pathname === '';
  }

  // vault 布局：<div class="vault-scope"><header/><main><slot/></main><footer/></div>
  // 首页根节点 = main 的第一个子元素
  function homeRoot() {
    var main = document.querySelector('.vault-scope > main');
    return main ? main.firstElementChild : null;
  }

  // ---------- 小工具：安全地建 DOM ----------
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'class') el.className = attrs[k];
        else if (k === 'text') el.textContent = attrs[k];
        else el.setAttribute(k, attrs[k]);
      });
    }
    (children || []).forEach(function (c) {
      if (c == null) return;
      el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return el;
  }

  function isInternal(href) {
    return typeof href === 'string' && href.charAt(0) === '/' && href.charAt(1) !== '/';
  }

  // 站内链接走前端路由，不整页刷新：pushState + popstate（vue-router 会响应）
  function link(href, cls, children) {
    var a = h('a', { href: href || '#', class: cls || '' }, children);
    if (/^https?:\/\//.test(href || '')) {
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener noreferrer');
    }
    if (isInternal(href)) {
      a.addEventListener('click', function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        history.pushState({}, '', href);
        window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
        window.scrollTo(0, 0);
      });
    }
    return a;
  }

  // ---------- 上方：标题区 ----------
  function buildTop() {
    var c = cfg();
    var title = h('h1', null, [c.title || '', c.titleEmphasis ? h('em', { text: c.titleEmphasis }) : null]);

    var actions = h('div', { class: 'sw-actions' }, [
      c.primaryButton ? link(c.primaryButton.href, 'sw-btn sw-btn-primary', [c.primaryButton.text]) : null,
      c.secondaryButton ? link(c.secondaryButton.href, 'sw-btn sw-btn-ghost', [c.secondaryButton.text]) : null
    ]);

    var tags = h('div', { class: 'sw-tags' }, (c.tags || []).map(function (t) {
      return h('span', { class: 'sw-tag', text: t });
    }));

    var left = h('div', { style: 'position:relative;z-index:1' }, [
      c.badge ? h('span', { class: 'sw-badge', text: c.badge }) : null,
      title,
      c.subtitle ? h('p', { class: 'sw-hero-sub', text: c.subtitle }) : null,
      actions,
      tags
    ]);

    var side = h('div', { class: 'sw-side' }, []);
    if (c.guestCard) {
      side.appendChild(h('div', { class: 'sw-card' }, [
        h('h3', null, [c.guestCard.title || '', link(c.guestCard.href, 'sw-link', [c.guestCard.linkText || '→'])]),
        h('p', { text: c.guestCard.text || '' })
      ]));
    }
    if (c.payCard) {
      side.appendChild(h('div', { class: 'sw-card' }, [
        h('h3', { text: c.payCard.title || '' }),
        h('div', { class: 'sw-pay' }, (c.payCard.methods || []).map(function (m) {
          return h('span', { class: m.soon ? 'sw-soon' : '', text: m.name });
        }))
      ]));
    }

    return h('section', { id: TOP_ID, class: 'sw-hero' }, [
      h('div', { class: 'sw-wrap' }, [h('div', { class: 'sw-hero-card' }, [left, side])])
    ]);
  }

  // ---------- 下方：怎么购买 + 售后 ----------
  function buildBottom() {
    var c = cfg();
    var steps = h('div', { class: 'sw-steps' }, (c.steps || []).map(function (s, i) {
      return h('div', { class: 'sw-step' }, [
        h('div', { class: 'sw-step-num', text: String(i + 1) }),
        h('div', null, [h('b', { text: s.title }), h('span', { text: s.text })])
      ]);
    }));

    var support = h('div', { class: 'sw-support' }, (c.support || []).map(function (s) {
      var inner = [h('i', { text: s.icon || '' }), h('span', { class: 'sw-support-text' }, [h('b', { text: s.title }), h('small', { text: s.text })])];
      return s.href ? link(s.href, '', inner) : h('div', null, inner);
    }));

    return h('section', { id: BOTTOM_ID, class: 'sw-bottom' }, [
      h('div', { class: 'sw-wrap' }, [
        c.stepsTitle ? h('h2', { class: 'sw-section-title', text: c.stepsTitle }) : null,
        steps,
        support
      ])
    ]);
  }

  // ---------- 同步：该在就加，不该在就删 ----------
  function remove(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  function sync() {
    if (!document.querySelector('.vault-scope')) return; // 不是 vault 模板（例如后台），什么都不做
    var root = homeRoot();
    if (isHome() && root) {
      var top = document.getElementById(TOP_ID);
      if (!top || top.parentNode !== root) {
        remove(TOP_ID);
        root.insertBefore(buildTop(), root.firstChild);
      }
      var bottom = document.getElementById(BOTTOM_ID);
      if (!bottom || bottom.parentNode !== root) {
        remove(BOTTOM_ID);
        root.appendChild(buildBottom());
      }
    } else {
      remove(TOP_ID);
      remove(BOTTOM_ID);
    }
  }

  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      try { sync(); } catch (e) { if (window.console) console.warn('[sw-home]', e); }
    });
  }

  function start() {
    schedule();
    new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
    window.addEventListener('popstate', schedule);
    ['pushState', 'replaceState'].forEach(function (fn) {
      var orig = history[fn];
      history[fn] = function () {
        var r = orig.apply(this, arguments);
        schedule();
        return r;
      };
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
