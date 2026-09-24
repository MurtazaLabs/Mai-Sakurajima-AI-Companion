// Notification Center — SSE-powered activity indicator + panel
(function() {
  'use strict';

  var notifications = [];
  var unread = 0;
  var panel = null;
  var bellBtn = null;
  var badgeEl = null;
  var sse = null;

  var EVENT_ICONS = {
    'state.emotion.changed': '▽',
    'state.voice.listening': '🎤', 'state.voice.speaking': '🎤', 'state.voice.idle': '🎤', 'state.voice.wake': '🎤',
    'state.memory.updated': '🧠',
    'state.reasoning.busy': '⚡', 'state.reasoning.complete': '⚡', 'state.reasoning.reflection': '⚡',
    'state.dreaming.started': '💭', 'state.dreaming.finished': '💭',
    'state.knowledge.updated': '🕸', 'state.belief.updated': '🕸',
    'state.goal.updated': '◎',
    'state.agent.completed': '⚙',
  };

  var EVENT_LABELS = {
    'state.emotion.changed': 'Mood shift',
    'state.voice.listening': 'Listening', 'state.voice.speaking': 'Speaking', 'state.voice.idle': 'Voice idle', 'state.voice.wake': 'Wake word',
    'state.memory.updated': 'Memory updated',
    'state.reasoning.busy': 'Reasoning', 'state.reasoning.complete': 'Reasoning complete', 'state.reasoning.reflection': 'New reflection',
    'state.dreaming.started': 'Dream started', 'state.dreaming.finished': 'Dream complete',
    'state.knowledge.updated': 'Graph updated', 'state.belief.updated': 'Belief updated',
    'state.goal.updated': 'Goal updated',
    'state.agent.completed': 'Agent task',
  };

  function timeAgo(ts) {
    var sec = Math.floor((Date.now() - ts) / 1000);
    if (sec < 60) return 'just now';
    var min = Math.floor(sec / 60);
    if (min < 60) return min + 'm ago';
    var hr = Math.floor(min / 60);
    return hr + 'h ago';
  }

  function build() {
    // Bell button on taskbar
    var taskbar = document.getElementById('taskbar');
    if (!taskbar || document.getElementById('notif-btn')) return;

    bellBtn = document.createElement('button');
    bellBtn.id = 'notif-btn';
    bellBtn.className = 'notif-btn';
    bellBtn.title = 'Notifications';
    bellBtn.innerHTML = '<span class="notif-bell">🔔</span><span id="notif-badge" class="notif-badge" style="display:none">0</span>';

    badgeEl = document.getElementById('notif-badge');
    // Can't get it by ID since it's not in DOM yet — reference via querySelector later

    // Insert before clock
    var clock = document.getElementById('taskbar-clock');
    if (clock) taskbar.insertBefore(bellBtn, clock);
    else taskbar.appendChild(bellBtn);

    bellBtn.addEventListener('click', togglePanel);

    // Build panel
    panel = document.createElement('div');
    panel.id = 'notif-panel';
    panel.className = 'notif-panel';
    panel.innerHTML =
      '<div class="notif-panel-header">' +
        '<span class="notif-panel-title">Notifications</span>' +
        '<button class="notif-panel-clear" id="notif-clear">Clear</button>' +
      '</div>' +
      '<div id="notif-list" class="notif-list"><div class="notif-empty">No notifications yet</div></div>';
    document.body.appendChild(panel);

    document.getElementById('notif-clear').addEventListener('click', function() {
      notifications = [];
      unread = 0;
      updateBadge();
      renderPanel();
    });

    // Close panel on click outside
    document.addEventListener('click', function(e) {
      if (panel && panel.classList.contains('open') &&
          !panel.contains(e.target) && e.target !== bellBtn && !bellBtn.contains(e.target)) {
        closePanel();
      }
    });
  }

  function togglePanel() {
    if (!panel) return;
    if (panel.classList.contains('open')) closePanel();
    else openPanel();
  }

  function openPanel() {
    if (!panel) return;
    panel.classList.add('open');
    unread = 0;
    updateBadge();
    renderPanel();
  }

  function closePanel() {
    if (panel) panel.classList.remove('open');
  }

  function renderPanel() {
    var list = document.getElementById('notif-list');
    if (!list) return;
    if (notifications.length === 0) {
      list.innerHTML = '<div class="notif-empty">No notifications yet</div>';
      return;
    }
    var html = '';
    notifications.slice(0, 30).forEach(function(n) {
      html += '<div class="notif-item">' +
        '<span class="notif-icon">' + (EVENT_ICONS[n.topic] || '○') + '</span>' +
        '<div class="notif-content">' +
          '<div class="notif-title">' + (EVENT_LABELS[n.topic] || n.topic) + '</div>' +
          (n.label ? '<div class="notif-detail">' + n.label + '</div>' : '') +
          '<div class="notif-time">' + timeAgo(n.time) + '</div>' +
        '</div>' +
      '</div>';
    });
    list.innerHTML = html;
  }

  function updateBadge() {
    var b = bellBtn ? bellBtn.querySelector('.notif-badge') : null;
    if (!b) return;
    if (unread > 0) {
      b.style.display = 'flex';
      b.textContent = unread > 99 ? '99+' : unread;
    } else {
      b.style.display = 'none';
    }
  }

  function addNotification(topic, data) {
    var d = data || {};
    var label = '';
    switch (topic) {
      case 'state.emotion.changed': label = d.dominant || ''; break;
      case 'state.goal.updated': label = d.description || d.id || ''; break;
      case 'state.voice.speaking': label = (d.text || '').substring(0, 60); break;
      case 'state.voice.wake': label = (d.wake_word || d.text || '').substring(0, 60); break;
      default: label = '';
    }

    notifications.unshift({ topic: topic, data: d, label: label, time: Date.now() });
    if (notifications.length > 100) notifications.length = 100;
    unread++;
    updateBadge();

    if (panel && !panel.classList.contains('open')) {
      renderPanel();
    }
  }

  function connect() {
    if (sse) sse.close();
    sse = new EventSource('/api/stream');
    sse.onmessage = function(e) {
      try {
        var msg = JSON.parse(e.data);
        addNotification(msg.topic, msg.data);
      } catch(err) {}
    };
    sse.onerror = function() {};
  }

  // Init after DOM
  document.addEventListener('DOMContentLoaded', function() {
    // Wait a beat for taskbar to render
    setTimeout(function() {
      build();
      connect();
    }, 500);
  });

  window.MaiNotifications = { add: addNotification };

})();
