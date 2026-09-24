// Global Search (Cmd+K) — search memory, entities, topics
(function() {
  'use strict';

  var overlay = null;
  var debounceTimer = null;

  function open() {
    if (!overlay) build();
    overlay.classList.add('open');
    var input = document.getElementById('gsearch-input');
    if (input) { input.value = ''; input.focus(); }
    document.getElementById('gsearch-results').innerHTML = '';
    document.getElementById('gsearch-hint').textContent = 'Type to search memories, entities & topics';
  }

  function close() {
    if (overlay) overlay.classList.remove('open');
  }

  function isOpen() {
    return overlay && overlay.classList.contains('open');
  }

  function build() {
    overlay = document.createElement('div');
    overlay.id = 'gsearch-overlay';
    overlay.className = 'gsearch-overlay';
    overlay.innerHTML =
      '<div class="gsearch-modal">' +
        '<div class="gsearch-header">' +
          '<span class="gsearch-icon">⌕</span>' +
          '<input id="gsearch-input" class="gsearch-input" type="text" placeholder="Search memories, entities, topics..." autocomplete="off" spellcheck="false">' +
          '<button class="gsearch-close" id="gsearch-close" title="Close (Esc)">✕</button>' +
        '</div>' +
        '<div id="gsearch-hint" class="gsearch-hint">Type to search</div>' +
        '<div id="gsearch-results" class="gsearch-results"></div>' +
      '</div>';

    document.body.appendChild(overlay);

    document.getElementById('gsearch-close').addEventListener('click', close);
    document.getElementById('gsearch-input').addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, 200);
    });
    document.getElementById('gsearch-input').addEventListener('keydown', function(e) {
      if (e.key === 'Escape') close();
      if (e.key === 'Enter') {
        var first = document.querySelector('.gsearch-result-item');
        if (first) first.click();
      }
    });

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) close();
    });
  }

  function highlight(text, query) {
    if (!query) return text;
    var escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    var parts = text.split(new RegExp('(' + escaped + ')', 'gi'));
    return parts.map(function(p) {
      return p.toLowerCase() === query.toLowerCase()
        ? '<strong>' + p + '</strong>'
        : p;
    }).join('');
  }

  function truncate(text, len) {
    if (!text || text.length <= len) return text || '';
    return text.substring(0, len) + '…';
  }

  async function doSearch() {
    var input = document.getElementById('gsearch-input');
    var resultsEl = document.getElementById('gsearch-results');
    var hintEl = document.getElementById('gsearch-hint');
    var q = (input.value || '').trim();

    if (!q || q.length < 2) {
      resultsEl.innerHTML = '';
      hintEl.textContent = q ? 'Type at least 2 characters' : 'Type to search memories, entities & topics';
      return;
    }

    hintEl.textContent = 'Searching…';
    resultsEl.innerHTML = '';

    try {
      var results = [];

      // Search memory
      try {
        var memRes = await fetch('/api/memory?query=' + encodeURIComponent(q) + '&top_k=10');
        if (memRes.ok) {
          var memData = await memRes.json();
          var memResults = memData.results || [];
          memResults.forEach(function(r) {
            var text = r.text || r.content || '';
            if (text) results.push({ type: 'memory', label: 'Memory', text: truncate(text, 120), id: r.id, icon: '🧠' });
          });
        }
      } catch(e) {}

      // Search graph (client-side filter)
      try {
        var graphRes = await fetch('/api/graph');
        if (graphRes.ok) {
          var graphData = await graphRes.json();
          var nodes = graphData.nodes || [];
          var ql = q.toLowerCase();
          nodes.forEach(function(n) {
            var name = n.name || n.id || '';
            if (name.toLowerCase().includes(ql)) {
              results.push({ type: 'graph', label: n.type || 'entity', text: truncate(name, 120), id: n.id, icon: '●' });
            }
          });
        }
      } catch(e) {}

      if (results.length === 0) {
        hintEl.textContent = 'No results found for "' + q + '"';
        return;
      }

      hintEl.textContent = results.length + ' result' + (results.length > 1 ? 's' : '') + ' for "' + q + '"';

      // Sort: memories first, then by relevance
      results.sort(function(a, b) {
        if (a.type !== b.type) return a.type === 'memory' ? -1 : 1;
        return 0;
      });

      // Group by type
      var groups = {};
      results.forEach(function(r) {
        if (!groups[r.type]) groups[r.type] = [];
        groups[r.type].push(r);
      });

      var html = '';
      var groupOrder = ['memory', 'graph'];
      groupOrder.forEach(function(g) {
        if (!groups[g]) return;
        var label = g === 'memory' ? 'Memories' : 'Entities';
        html += '<div class="gsearch-group-label">' + label + ' <span class="gsearch-group-count">' + groups[g].length + '</span></div>';
        groups[g].forEach(function(r) {
          html += '<button class="gsearch-result-item" data-type="' + r.type + '" data-id="' + (r.id || '') + '">' +
            '<span class="gsearch-result-icon">' + r.icon + '</span>' +
            '<span class="gsearch-result-text">' + highlight(r.text, q) + '</span>' +
            '<span class="gsearch-result-label">' + r.label + '</span>' +
          '</button>';
        });
      });

      resultsEl.innerHTML = html;

      resultsEl.querySelectorAll('.gsearch-result-item').forEach(function(el) {
        el.addEventListener('click', function() {
          var type = this.dataset.type;
          close();
          if (type === 'memory' && window.MaiRouter) {
            window.MaiRouter.navigateTo('memory');
          } else if (type === 'graph' && window.MaiRouter) {
            window.MaiRouter.navigateTo('graph');
          }
        });
      });

    } catch(e) {
      hintEl.textContent = 'Search error';
    }
  }

  // Register keyboard shortcut
  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      if (isOpen()) close();
      else open();
    }
    if (e.key === 'Escape' && isOpen()) close();
  });

  window.MaiSearch = { open: open, close: close, isOpen: isOpen };
})();
