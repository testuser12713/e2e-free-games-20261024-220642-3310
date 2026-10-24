/* Mockup behaviour for the deals page: live filter/sort without reload, state in the URL,
   "Jetzt aktualisieren" demo run. Plain DOM, no dependencies. In the product these are
   useDealFilters (URL <-> filters), FilterBar and StatusBar. */
(function () {
  var form = document.querySelector('[data-filter-form]');
  var grid = document.querySelector('[data-deal-grid]');
  var DEFAULT_SORT = 'first_seen:desc';

  function el(name) { return form && form.elements.namedItem(name); }

  /* ---- URL <-> form ---- */
  function readUrl() {
    if (!form) return;
    var p = new URLSearchParams(location.search);
    var sort = p.get('sort') || 'first_seen';
    var order = p.get('order');
    if (sort.indexOf(':') > -1) { var parts = sort.split(':'); sort = parts[0]; order = parts[1]; }
    el('q').value = p.get('q') || '';
    el('platform').value = p.get('platform') || 'all';
    el('store').value = p.get('store') || '';
    el('min').value = p.get('min_price') || '';
    el('max').value = p.get('max_price') || '';
    var sortValue = sort + ':' + (order || (sort === 'title' || sort === 'ends_at' ? 'asc' : 'desc'));
    el('sort').value = sortValue;
    if (el('sort').value !== sortValue) el('sort').value = DEFAULT_SORT;
  }
  function writeUrl() {
    var p = new URLSearchParams();
    var s = el('sort').value.split(':');
    if (el('q').value.trim()) p.set('q', el('q').value.trim());
    if (el('platform').value !== 'all') p.set('platform', el('platform').value);
    if (el('store').value) p.set('store', el('store').value);
    if (el('min').value) p.set('min_price', el('min').value);
    if (el('max').value) p.set('max_price', el('max').value);
    if (el('sort').value !== DEFAULT_SORT) { p.set('sort', s[0]); p.set('order', s[1]); }
    var qs = p.toString();
    try { history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '')); } catch (e) { /* sandboxed frame */ }
  }
  function isDefault() {
    return !el('q').value.trim() && el('platform').value === 'all' && !el('store').value &&
      !el('min').value && !el('max').value && el('sort').value === DEFAULT_SORT;
  }

  /* ---- filter + sort the rendered cards ---- */
  function apply() {
    var q = el('q').value.trim().toLowerCase();
    var platform = el('platform').value;
    var store = el('store').value;
    var min = parseFloat(el('min').value);
    var max = parseFloat(el('max').value);
    var s = el('sort').value.split(':');
    var key = s[0], dir = s[1] === 'asc' ? 1 : -1;
    var cards = [].slice.call(grid.children);

    cards.forEach(function (li) {
      var d = li.dataset;
      var price = parseFloat(d.price);
      var ok = (!q || d.title.toLowerCase().indexOf(q) > -1) &&
        (platform === 'all' || d.platform === platform) &&
        (!store || d.store === store) &&
        (isNaN(min) || price >= min) && (isNaN(max) || price <= max);
      li.hidden = !ok;
    });

    function val(li) {
      if (key === 'title') return li.dataset.title.toLowerCase();
      if (key === 'original_price') return parseFloat(li.dataset.price);
      if (key === 'ends_at') return li.dataset.ends || '';
      return li.dataset.first;
    }
    cards.sort(function (a, b) {
      var va = val(a), vb = val(b);
      if (key === 'ends_at') { /* deals without a known end go last */
        if (!va && !vb) return 0; if (!va) return 1; if (!vb) return -1;
      }
      return va < vb ? -dir : va > vb ? dir : 0;
    }).forEach(function (li) { grid.appendChild(li); });

    var n = cards.filter(function (li) { return !li.hidden; }).length;
    var count = document.querySelector('[data-result-count]');
    if (count) count.textContent = n + (n === 1 ? ' Spiel' : ' Spiele');
    var empty = document.querySelector('[data-empty-filtered]');
    if (empty) empty.hidden = n !== 0;
    grid.hidden = n === 0;
    var bar = form.querySelector('[data-reset]');
    if (bar) bar.disabled = isDefault();
    writeUrl();
  }

  if (form && grid) {
    readUrl();
    form.addEventListener('input', apply);
    form.addEventListener('change', apply);
    form.addEventListener('submit', function (e) { e.preventDefault(); apply(); });
    [].forEach.call(document.querySelectorAll('[data-reset]'), function (b) {
      b.addEventListener('click', function () {
        el('q').value = ''; el('platform').value = 'all'; el('store').value = '';
        el('min').value = ''; el('max').value = ''; el('sort').value = DEFAULT_SORT;
        apply();
      });
    });
    apply();
  } else if (form) {
    /* Screens without a rendered list hand the filters over to the deals page. */
    if (location.search) readUrl();
    form.addEventListener('change', function () { form.submit(); });
  }

  /* ---- manual refresh (POST /api/refresh, then status polling) ---- */
  var btn = document.querySelector('[data-refresh]');
  if (btn && !btn.disabled) {
    var label = btn.querySelector('[data-refresh-label]');
    var progress = document.querySelector('[data-progress]');
    var live = document.querySelector('[data-status-live]');
    var updated = document.querySelector('[data-updated]');
    var idle = label.textContent;
    btn.addEventListener('click', function () {
      btn.disabled = true; btn.classList.add('is-loading'); btn.setAttribute('aria-busy', 'true');
      label.textContent = 'Aktualisiere \u2026';
      if (progress) progress.hidden = false;
      if (live) live.innerHTML = '';
      setTimeout(function () {
        btn.disabled = false; btn.classList.remove('is-loading'); btn.removeAttribute('aria-busy');
        label.textContent = idle;
        if (progress) progress.hidden = true;
        if (updated) updated.textContent = 'gerade eben';
        if (live) {
          live.innerHTML = '<div class="notice notice--success"><svg class="icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="10" r="8"/><path d="m6.5 10.5 2.5 2.5 4.5-5"/></svg><p><span class="notice__title">Aktualisierung abgeschlossen.</span> Alle 5 Quellen wurden abgefragt, die Liste ist auf dem neuesten Stand.</p></div>';
        }
      }, 2600);
    });
  }
})();
