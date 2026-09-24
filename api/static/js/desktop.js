// Desktop — Dashboard content for the main space
(() => {
  'use strict';

  const APP_LIST = [
    { id: 'consciousness', label: 'Consciousness', icon: '◈' },
    { id: 'chat', label: 'Conversations', icon: '💬' },
    { id: 'memory', label: 'Memory', icon: '🧠' },
    { id: 'graph', label: 'Knowledge Graph', icon: '🕸' },
    { id: 'reasoning', label: 'Reasoning', icon: '⚡' },
    { id: 'agency', label: 'Agency', icon: '💭' },
    { id: 'voice', label: 'Voice Center', icon: '🎤' },
    { id: 'tasks', label: 'Tasks', icon: '✓' },
    { id: 'permissions', label: 'Permissions', icon: '🔒' },
    { id: 'system', label: 'System', icon: '⚙' },
  ];

  function renderQuickLaunch() {
    var container = document.getElementById('desktop-launch');
    if (!container) return;
    container.innerHTML = APP_LIST.map(function(app) {
      return '<button class="desk-launch-item" data-space="' + app.id + '">' +
        '<span class="desk-launch-icon">' + app.icon + '</span>' +
        '<span class="desk-launch-label">' + app.label + '</span>' +
      '</button>';
    }).join('');
    container.querySelectorAll('.desk-launch-item').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var id = this.dataset.space;
        if (window.MaiRouter) window.MaiRouter.navigateTo(id);
      });
    });
  }

  function updateDashboard() {
    fetch('/api/consciousness')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d) return;
        var emo = d.emotion || {};
        var cog = d.cognitive || {};
        var goals = d.goals || {};

        // Emotion card
        var emoEl = document.getElementById('desk-val-emotion');
        if (emoEl) emoEl.textContent = emo.emotion || emo.name || 'neutral';

        // Thought card
        var thoughts = cog.recent_thoughts || [];
        var thoughtEl = document.getElementById('desk-thought-text');
        if (thoughtEl) {
          thoughtEl.textContent = thoughts.length > 0
            ? (typeof thoughts[0] === 'string' ? thoughts[0] : (thoughts[0].content || thoughts[0].text || 'No active thought'))
            : 'No active thought';
        }

        // Goals card
        var goalEl = document.getElementById('desk-val-goals');
        var activeGoals = (goals.active || goals.goals || []);
        if (goalEl) goalEl.textContent = activeGoals.length > 0 ? activeGoals.length + ' active' : '0';

        // Greeting
        var greetEl = document.getElementById('desktop-greeting');
        if (greetEl) {
          var h = new Date().getHours();
          if (h < 6) greetEl.textContent = 'Still awake?';
          else if (h < 12) greetEl.textContent = 'Good morning';
          else if (h < 17) greetEl.textContent = 'Good afternoon';
          else if (h < 21) greetEl.textContent = 'Good evening';
          else greetEl.textContent = 'Good night';
        }

        // Status dot
        var dot = document.getElementById('desktop-status-dot');
        if (dot) { dot.className = 'status-dot online'; }
      })
      .catch(function() {
        var dot = document.getElementById('desktop-status-dot');
        if (dot) dot.className = 'status-dot offline';
      });

    fetch('/api/voice/status')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var el = document.getElementById('desk-val-voice');
        if (el) el.textContent = d.state || '—';
      })
      .catch(function() {});

    fetch('/api/memory/stats')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var el = document.getElementById('desk-val-memory');
        if (el) el.textContent = (d.vector_count || 0) + ' items';
      })
      .catch(function() {});

    fetch('/api/health')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var sub = document.getElementById('desktop-subtitle');
        if (sub) sub.textContent = d.ready ? 'AI Companion · Online' : 'AI Companion · Booting...';
      })
      .catch(function() {
        var sub = document.getElementById('desktop-subtitle');
        if (sub) sub.textContent = 'AI Companion · Offline';
      });
  }

  document.addEventListener('DOMContentLoaded', function() {
    renderQuickLaunch();
    updateDashboard();
    setInterval(updateDashboard, 15000);
  });
})();
