(() => {
  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const state = {
    apps: [],
    filtered: [],
    query: '',
    tag: 'all',
    sort: 'recent',
    generatedAt: '',
  };

  const sorters = {
    recent:    (a, b) => (b.published_at || '').localeCompare(a.published_at || ''),
    name:      (a, b) => (a.label || '').localeCompare(b.label || '', undefined, { sensitivity: 'base' }),
    downloads: (a, b) => (b.download_count || 0) - (a.download_count || 0),
    stars:     (a, b) => (b.stars || 0) - (a.stars || 0),
  };

  const fmt = {
    count(n) {
      if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
      if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'k';
      return String(n);
    },
    size(bytes) {
      if (!bytes) return '—';
      return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    },
    date(iso) {
      if (!iso) return '—';
      try {
        const d = new Date(iso);
        const now = Date.now();
        const diff = (now - d.getTime()) / 1000;
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        if (diff < 86400 * 30) return Math.floor(diff / 86400) + 'd ago';
        return d.toLocaleDateString();
      } catch { return '—'; }
    },
    human(iso) {
      if (!iso) return '—';
      try { return new Date(iso).toLocaleString(); } catch { return '—'; }
    }
  };

  function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function iconSrc(app) {
    if (app.icon_url) return app.icon_url;
    const owner = (app.repo || '').split('/')[0];
    return owner ? `https://github.com/${owner}.png?size=128` : '';
  }

  function iconInitial(app) {
    return (app.label || '?').trim().charAt(0).toUpperCase();
  }

  function loadIndex() {
    return fetch('index.json', { cache: 'no-cache' })
      .then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });
  }

  function applyFilters() {
    const q = state.query.trim().toLowerCase();
    let list = state.apps;

    if (state.tag !== 'all') {
      list = list.filter(a => {
        if (state.tag === '__gpl')     return (a.license || '').toUpperCase().includes('GPL');
        if (state.tag === '__recent')  return true;
        return (a.topics || []).some(t => t.toLowerCase() === state.tag)
            || (a.license || '').toLowerCase() === state.tag;
      });
    }

    if (q) {
      list = list.filter(a =>
        (a.label || '').toLowerCase().includes(q) ||
        (a.package || '').toLowerCase().includes(q) ||
        (a.description || '').toLowerCase().includes(q) ||
        (a.repo || '').toLowerCase().includes(q) ||
        (a.topics || []).some(t => t.toLowerCase().includes(q))
      );
    }

    list = [...list].sort(sorters[state.sort] || sorters.recent);
    state.filtered = list;
  }

  function pickTags() {
    const counts = new Map();
    for (const a of state.apps) {
      for (const t of (a.topics || [])) {
        const key = t.toLowerCase();
        if (key.length < 3 || key.length > 24) continue;
        counts.set(key, (counts.get(key) || 0) + 1);
      }
    }
    const top = [...counts.entries()]
      .filter(([, n]) => n >= 4)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([k]) => k);
    return top;
  }

  function renderChips() {
    const container = $('#chips');
    if (!container) return;
    const tags = pickTags();
    const all = [{ key: 'all', label: 'All' }, ...tags.map(t => ({ key: t, label: t }))];
    container.innerHTML = all.map(t =>
      `<span class="chip${t.key === state.tag ? ' active' : ''}" data-tag="${esc(t.key)}">${esc(t.label)}</span>`
    ).join('');
    $$('.chip', container).forEach(el => {
      el.addEventListener('click', () => {
        state.tag = el.dataset.tag;
        writeHash();
        render();
      });
    });
  }

  function renderStats() {
    const el = $('#stats');
    if (!el) return;
    const n = state.apps.length;
    const totalBytes = state.apps.reduce((s, a) => s + (a.apk_size || 0), 0);
    const withDownloads = state.apps.reduce((s, a) => s + (a.download_count || 0), 0);
    const recentCutoff = Date.now() - 7 * 86400 * 1000;
    const recent = state.apps.filter(a => a.published_at && new Date(a.published_at).getTime() > recentCutoff).length;

    el.innerHTML = `
      <span><b>${n}</b> apps</span>
      <span><b>${recent}</b> updated this week</span>
      <span><b>${(totalBytes / 1024 / 1024 / 1024).toFixed(1)}</b> GB total</span>
      <span><b>${fmt.count(withDownloads)}</b> downloads tracked</span>
      <span>updated ${esc(fmt.human(state.generatedAt))}</span>
    `;
  }

  function renderCards() {
    const container = $('#apps');
    if (!container) return;

    if (state.filtered.length === 0) {
      container.innerHTML = `<div class="empty">No apps match “${esc(state.query)}”.</div>`;
      return;
    }

    const html = state.filtered.map(a => {
      const src = iconSrc(a);
      const fallback = `onerror="this.style.display='none';this.parentNode.textContent='${esc(iconInitial(a))}'"`;
      const icon = src
        ? `<img src="${esc(src)}" alt="" loading="lazy" ${fallback}>`
        : esc(iconInitial(a));
      const meta = [
        a.versionName ? `v${esc(a.versionName)}` : null,
        a.apk_size ? esc(fmt.size(a.apk_size)) : null,
        a.stars ? `★ ${a.stars}` : null,
        a.download_count ? `↓ ${fmt.count(a.download_count)}` : null,
        a.license ? esc(a.license) : null,
      ].filter(Boolean).join('<span class="sep">·</span>');

      return `
        <div class="card" data-package="${esc(a.package)}">
          <div class="icon">${icon}</div>
          <div class="body">
            <h3>${esc(a.label || a.package)}</h3>
            <p class="pkg">${esc(a.package)}</p>
            <p class="desc">${esc(a.description || 'No description.')}</p>
            <div class="meta">${meta}</div>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = html;
    $$('.card', container).forEach(el => {
      el.addEventListener('click', () => {
        location.hash = '#/app/' + encodeURIComponent(el.dataset.package);
      });
    });
  }

  function renderDetail(pkg) {
    const app = state.apps.find(a => a.package === pkg);
    const container = $('#apps');
    const header = $('#header-top');
    const controls = $('#controls');

    if (!app) {
      container.innerHTML = `<div class="empty">App not found: ${esc(pkg)}</div>`;
      return;
    }

    if (header) header.style.display = 'none';
    if (controls) controls.style.display = 'none';
    const chips = $('#chips'); if (chips) chips.style.display = 'none';

    const src = iconSrc(app);
    const fallback = `onerror="this.style.display='none';this.parentNode.textContent='${esc(iconInitial(app))}'"`;
    const icon = src
      ? `<img src="${esc(src)}" alt="" ${fallback}>`
      : esc(iconInitial(app));

    const rows = [
      ['Package', `<code>${esc(app.package)}</code>`],
      ['Version', `${esc(app.versionName || '—')} (${esc(app.versionCode || '—')})`],
      ['Released', esc(fmt.human(app.published_at))],
      ['APK size', esc(fmt.size(app.apk_size))],
      ['Min SDK', esc(app.minSdk || '—')],
      ['Target SDK', esc(app.targetSdk || '—')],
      ['License', esc(app.license || '—')],
      ['Stars', app.stars ? esc(String(app.stars)) : '—'],
      ['Downloads', app.download_count ? esc(fmt.count(app.download_count)) : '—'],
      ['Source', `<a href="${esc(app.homepage || '#')}">${esc(app.repo)}</a>`],
      ['SHA-256', `<code>${esc((app.signature_sha256 || '').slice(0, 32))}…</code>`],
    ];

    if ((app.topics || []).length) {
      rows.push(['Topics', (app.topics || []).map(t => `<span class="chip" style="cursor:default">${esc(t)}</span>`).join(' ')]);
    }

    container.innerHTML = `
      <div class="detail">
        <a class="back" href="#/">&larr; All apps</a>
        <div class="detail-head">
          <div class="icon-lg">${icon}</div>
          <div class="info">
            <h2>${esc(app.label || app.package)}</h2>
            <div class="pkg">${esc(app.package)}</div>
            <div class="desc">${esc(app.description || 'No description.')}</div>
          </div>
        </div>
        <div class="actions">
          <a class="btn" href="${esc(app.apk_url)}">Download APK</a>
          <a class="btn btn-ghost" href="${esc(app.release_url)}">Release notes</a>
          <a class="btn btn-ghost" href="${esc(app.homepage || '#')}">Source code</a>
        </div>
        <div class="install-note">
          Download the APK and open it on your phone. You may need to allow installation from unknown sources.
        </div>
        <table class="meta-table">
          ${rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}
        </table>
      </div>
    `;
  }

  function render() {
    const hash = location.hash || '#/';
    const detailMatch = hash.match(/^#\/app\/(.+)$/);

    const header = $('#header-top');
    const controls = $('#controls');
    const chips = $('#chips');

    if (detailMatch) {
      renderDetail(decodeURIComponent(detailMatch[1]));
      return;
    }

    if (header) header.style.display = '';
    if (controls) controls.style.display = '';
    if (chips) chips.style.display = '';

    applyFilters();
    renderStats();
    renderCards();
  }

  function writeHash() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    if (state.tag !== 'all') params.set('tag', state.tag);
    if (state.sort !== 'recent') params.set('sort', state.sort);
    const qs = params.toString();
    const newHash = '#/' + (qs ? '?' + qs : '');
    if (location.hash !== newHash) {
      history.replaceState(null, '', newHash);
    }
  }

  function readHash() {
    const hash = location.hash || '#/';
    const qIdx = hash.indexOf('?');
    if (qIdx === -1) return;
    const params = new URLSearchParams(hash.slice(qIdx + 1));
    state.query = params.get('q') || '';
    state.tag = params.get('tag') || 'all';
    state.sort = params.get('sort') || 'recent';
    const input = $('#search');
    if (input) input.value = state.query;
    const sel = $('#sort');
    if (sel) sel.value = state.sort;
  }

  function wireControls() {
    const input = $('#search');
    const sel = $('#sort');
    if (input) {
      let t = null;
      input.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(() => {
          state.query = input.value;
          writeHash();
          render();
        }, 150);
      });
    }
    if (sel) {
      sel.addEventListener('change', () => {
        state.sort = sel.value;
        writeHash();
        render();
      });
    }
  }

  function init() {
    loadIndex()
      .then(data => {
        state.apps = data.apps || [];
        state.generatedAt = data.generated_at || '';
        readHash();
        renderChips();
        wireControls();
        const sel = $('#sort'); if (sel) sel.value = state.sort;
        render();
      })
      .catch(err => {
        const c = $('#apps');
        if (c) c.innerHTML = `<div class="empty">Could not load index.json: ${esc(err.message)}</div>`;
      });
  }

  window.addEventListener('hashchange', () => {
    readHash();
    renderChips();
    const sel = $('#sort'); if (sel) sel.value = state.sort;
    render();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
