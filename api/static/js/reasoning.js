// Space — Reasoning
(function() {
  'use strict';
  var _intervals = [];
  var _id = 'reasoning';

  async function loadThoughts() {
    var el = document.getElementById(_id + '-thoughts');
    try {
      var res = await fetch('/api/reasoning/thoughts?limit=30');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var d = await res.json();
      if (d.error) { el.innerHTML = '<div class="no-data"><span>' + d.error + '</span></div>'; return; }

      var thoughts = d.thoughts || [];
      var count = d.count || 0;
      var html = '';

      html += '<div class="stat-row"><span class="stat-chip">Total Thoughts <strong>' + count + '</strong></span></div>';

      if (!thoughts.length) {
        html += '<div class="no-data"><span>No thoughts recorded yet</span></div>';
        el.innerHTML = html;
        return;
      }

      thoughts.slice().reverse().forEach(function(t) {
        var ts = t.timestamp ? new Date(t.timestamp * 1000).toLocaleString() : '';
        var steps = t.reasoning_steps || [];
        var confidence = t.confidence !== undefined ? Math.round(t.confidence * 100) + '%' : '—';

        html += '<div class="thought-entry">';
        html += '<div class="query">' + t.query + '</div>';
        if (t.conclusion) html += '<div class="conclusion">' + t.conclusion + '</div>';
        if (steps.length) {
          html += '<div class="steps">';
          steps.forEach(function(s) { html += '<div>• ' + s + '</div>'; });
          html += '</div>';
        }
        html += '<div class="meta">Confidence ' + confidence + (ts ? ' · ' + ts : '') + '</div>';
        html += '</div>';
      });

      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>';
    }
  }

  async function loadReflection() {
    var el = document.getElementById(_id + '-reflection');
    try {
      var res = await fetch('/api/reasoning/reflect');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var d = await res.json();
      if (d.error) { el.innerHTML = '<div class="no-data"><span>' + d.error + '</span></div>'; return; }

      var r = d.reflection;
      if (!r) { el.innerHTML = '<div class="no-data"><span>No reflection available</span></div>'; return; }

      var ts = r.timestamp ? new Date(r.timestamp * 1000).toLocaleString() : '';
      var patterns = r.patterns || [];
      var topics = r.topics || [];

      var html = '<div class="reflection-card" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:18px 20px">';
      html += '<div class="period" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em">' + (r.period || 'daily') + ' reflection' + (ts ? ' · ' + ts : '') + '</div>';
      html += '<div class="summary" style="font-size:14px;color:var(--text-primary);margin-top:8px;line-height:1.5">' + (r.summary || '') + '</div>';
      if (patterns.length) {
        html += '<div class="patterns" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px">';
        patterns.forEach(function(p) { html += '<span class="pattern-chip" style="padding:3px 10px;border-radius:6px;font-size:11px;background:rgba(79,167,255,0.1);color:var(--accent)">' + p + '</span>'; });
        html += '</div>';
      }
      if (topics.length) {
        html += '<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">Topics: ' + topics.join(', ') + '</div>';
      }
      html += '</div>';
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>';
    }
  }

  async function loadReflectionHistory() {
    var el = document.getElementById(_id + '-history');
    try {
      var res = await fetch('/api/reasoning/reflect/history');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var d = await res.json();
      var history = d.history || [];
      if (!history.length) {
        el.innerHTML = '<div class="no-data"><span>No past reflections</span></div>';
        return;
      }
      var html = '';
      history.slice().reverse().forEach(function(r) {
        var ts = r.timestamp ? new Date(r.timestamp * 1000).toLocaleString() : '';
        html += '<div class="thought-entry">';
        html += '<div class="meta">' + (r.period || 'daily') + ' · ' + ts + '</div>';
        html += '<div style="font-size:12px;color:var(--text-primary);margin-top:4px">' + (r.summary || '') + '</div>';
        if (r.patterns && r.patterns.length) {
          html += '<div class="patterns" style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px">';
          r.patterns.forEach(function(p) { html += '<span class="pattern-chip" style="padding:3px 10px;border-radius:6px;font-size:11px;background:rgba(79,167,255,0.1);color:var(--accent)">' + p + '</span>'; });
          html += '</div>';
        }
        html += '</div>';
      });
      el.innerHTML = html;
    } catch (e) {
      el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>';
    }
  }

  function _init() {
    var el = document.getElementById(_id + '-content');
    if (!el) return;
    el.innerHTML =
      '<div id="' + _id + '-reflection" class="space-body-section" style="margin-bottom:16px"></div>' +
      '<div style="display:flex;gap:8px;margin-bottom:16px">' +
        '<h2 style="font-size:16px;font-weight:600;flex:1">Latest Reflection</h2>' +
        '<button id="reflect-refresh" class="memory-search-btn" style="padding:6px 14px;border-radius:8px;border:none;background:var(--glass);color:var(--text-secondary);font-size:12px;cursor:pointer">↻ Refresh</button>' +
      '</div>' +
      '<div id="' + _id + '-history" class="space-body-section" style="margin-bottom:16px"></div>' +
      '<h2 style="font-size:16px;font-weight:600;margin-bottom:12px">Recent Thoughts</h2>' +
      '<div id="' + _id + '-thoughts" class="space-body-section"></div>'

    loadThoughts();
    loadReflection();
    loadReflectionHistory();

    document.getElementById('reflect-refresh').addEventListener('click', loadReflection);
    _intervals.push(setInterval(loadThoughts, 8000));
  }

  function _destroy() {
    _intervals.forEach(function(iv) { clearInterval(iv); });
    _intervals.length = 0;
  }

  window.MaiSpaces = window.MaiSpaces || {};
  window.MaiSpaces[_id] = { init: _init, destroy: _destroy };
  if (window.MaiRouter) window.MaiRouter.register(_id, { label: 'Reasoning', subtitle: 'Thoughts, reflections & learning', icon: '⚡', init: _init, destroy: _destroy });
})();
