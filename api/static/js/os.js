// Mai OS — Shell (clock, taskbar, start menu, status, sidebar, SSE bus, reconnection)
(() => {
  'use strict';

  const APP_LIST = [
    { id: 'presence', label: 'Presence', icon: '◈', page: '/', isPresence: true },
    { id: 'consciousness', label: 'Consciousness', icon: '◈' },
    { id: 'chat', label: 'Conversations', icon: '💬' },
    { id: 'memory', label: 'Memory', icon: '🧠' },
    { id: 'graph', label: 'Knowledge Graph', icon: '🕸' },
    { id: 'reasoning', label: 'Reasoning', icon: '⚡' },
    { id: 'agency', label: 'Agency', icon: '💭' },
    { id: 'voice', label: 'Voice Center', icon: '🎤' },
    { id: 'tasks', label: 'Tasks', icon: '✓' },
    { id: 'permissions', label: 'Permissions', icon: '🔒' },
    { id: 'inspector', label: 'Event Inspector', icon: '🔭' },
    { id: 'system', label: 'System', icon: '⚙' },
  ];

  var _sse = null;
  var _sseRetries = 0;
  var _sseMaxRetries = 10;
  var _connected = false;

  // ── Reconnection overlay ──
  function showOfflineOverlay(show) {
    var overlay = document.getElementById('daemon-offline-overlay');
    if (!overlay) {
      if (!show) return;
      overlay = document.createElement('div');
      overlay.id = 'daemon-offline-overlay';
      overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9999;color:#fff;font-family:sans-serif;';
      overlay.innerHTML = '<div style="font-size:48px;margin-bottom:16px;">🔌</div><div style="font-size:24px;margin-bottom:8px;">Daemon Offline</div><div style="font-size:14px;opacity:0.7;">Reconnecting...</div>';
      document.body.appendChild(overlay);
    }
    overlay.style.display = show ? 'flex' : 'none';
  }

  // ── Connection status indicator ──
  function setConnectionState(state) {
    _connected = state === 'connected';
    var indicators = document.querySelectorAll('.connection-indicator');
    indicators.forEach(function(el) {
      el.className = 'connection-indicator ' + state;
    });
    // Notify other modules
    var evt = new CustomEvent('mai:connection', { detail: { state: state } });
    document.dispatchEvent(evt);
  }

  function clockTick() {
    var now = new Date();
    var el = document.getElementById('taskbar-clock');
    if (el) el.textContent = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0');
  }

  function toggleStartMenu() {
    var el = document.getElementById('start-menu');
    if (el) el.classList.toggle('open');
  }

  function closeStartMenu() {
    var el = document.getElementById('start-menu');
    if (el) el.classList.remove('open');
  }

  function renderTaskbar() {
    var container = document.getElementById('taskbar-apps');
    if (!container) return;
    container.innerHTML = '';
  }

  function renderStartMenu() {
    var list = document.getElementById('start-menu-list');
    if (!list) return;
    list.innerHTML = '';
    APP_LIST.forEach(function(app) {
      var btn = document.createElement('button');
      btn.className = 'start-menu-item';
      btn.innerHTML = '<span>' + app.label + '</span>';
      btn.addEventListener('click', function() {
        closeStartMenu();
        if (app.isPresence) { location.href = '/'; return; }
        if (window.MaiRouter) window.MaiRouter.navigateTo(app.id);
      });
      list.appendChild(btn);
    });
  }

  function renderSidebar() {
    var container = document.getElementById('sidebar-list');
    if (!container) return;
    container.innerHTML = '';
    APP_LIST.forEach(function(app) {
      var btn = document.createElement('button');
      btn.className = 'sidebar-item' + (app.isPresence ? ' sidebar-presence' : '');
      btn.dataset.space = app.id;
      btn.title = app.label;
      btn.innerHTML = '<span class="sidebar-icon">' + app.icon + '</span><span class="sidebar-label">' + app.label + '</span>';
      btn.addEventListener('click', function() {
        if (app.isPresence) { location.href = '/'; return; }
        if (window.MaiRouter) window.MaiRouter.navigateTo(app.id);
      });
      container.appendChild(btn);
    });
  }

  // ── Status bar updaters ──
  function setStatusOnline(online) {
    var dot = document.getElementById('status-dot');
    var txt = document.getElementById('status-text');
    if (!dot || !txt) return;
    if (online) { dot.className = 'status-dot online'; txt.textContent = 'Mai \u25cf Online'; }
    else { dot.className = 'status-dot offline'; txt.textContent = 'Offline'; }
  }

  function updateStatusEmotion(emotionData) {
    var el = document.getElementById('status-emotion');
    if (!el || !emotionData) return;
    el.textContent = emotionData.emotion || emotionData.name || '\u2014';
  }

  function updateStatusVoice(state) {
    var el = document.getElementById('status-voice');
    if (el) el.textContent = '\uD83C\uDFA4 ' + (state || '\u2014');
  }

  function updateStatusMemory(count) {
    var el = document.getElementById('status-memory');
    if (el) el.textContent = '\uD83E\uDDE0 ' + (count || 0);
  }

  // ── SSE bus with exponential backoff reconnection ──
  function connectSSE() {
    if (_sse) { _sse.close(); _sse = null; }
    _sse = new EventSource('/api/stream');
    _sse.onmessage = function(e) {
      try {
        var msg = JSON.parse(e.data);
        var topic = msg.topic;
        var data = msg.data || {};
        if (topic === 'state.emotion.changed') {
          updateStatusEmotion({ emotion: data.dominant });
        }
        if (topic === 'state.voice.listening') {
          updateStatusVoice('listening');
        }
        if (topic === 'state.voice.speaking') {
          updateStatusVoice('speaking');
        }
        if (topic === 'state.voice.idle') {
          updateStatusVoice('idle');
        }
        if (topic === 'state.voice.wake') {
          updateStatusVoice('wake');
        }
      } catch(err) {}
    };
    _sse.onopen = function() {
      _sseRetries = 0;
      setStatusOnline(true);
      setConnectionState('connected');
      showOfflineOverlay(false);
    };
    _sse.onerror = function() {
      _sse.close();
      _sse = null;
      setStatusOnline(false);
      setConnectionState('disconnected');
      if (_sseRetries < _sseMaxRetries) {
        _sseRetries++;
        var delay = Math.min(1000 * Math.pow(2, _sseRetries), 30000);
        showOfflineOverlay(true);
        setTimeout(connectSSE, delay);
      } else {
        showOfflineOverlay(true);
        document.getElementById('daemon-offline-overlay').innerHTML = '<div style="font-size:48px;margin-bottom:16px;">\uD83D\uDD0C</div><div style="font-size:24px;margin-bottom:8px;">Connection Lost</div><div style="font-size:14px;opacity:0.7;">Click to retry</div>';
        document.getElementById('daemon-offline-overlay').onclick = function() {
          _sseRetries = 0;
          connectSSE();
        };
      }
    };
  }

  // ── Health poll (keeps reconnection alive when SSE is down) ──
  function fallbackHealthCheck() {
    fetch('/api/health')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        setStatusOnline(!!d.ready);
        if (d.ready && !_sse) connectSSE();
      })
      .catch(function() {
        setStatusOnline(false);
      });
  }

  // ── One-shot initial fetches ──
  function initialStatusLoad() {
    fetch('/api/consciousness')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d && d.emotion) updateStatusEmotion(d.emotion);
      })
      .catch(function() {});
    fetch('/api/voice/status')
      .then(function(r) { return r.json(); })
      .then(function(d) { updateStatusVoice(d.state); })
      .catch(function() {});
    fetch('/api/memory/stats')
      .then(function(r) { return r.json(); })
      .then(function(d) { updateStatusMemory(d.vector_count || 0); })
      .catch(function() {});
  }

  document.addEventListener('DOMContentLoaded', function() {
    clockTick();
    setInterval(clockTick, 1000);
    renderStartMenu();
    renderTaskbar();
    renderSidebar();

    initialStatusLoad();
    connectSSE();
    fallbackHealthCheck();
    setInterval(fallbackHealthCheck, 30000);

    document.getElementById('start-btn').addEventListener('click', toggleStartMenu);
    document.addEventListener('click', function(e) {
      if (!e.target.closest('#start-menu') && !e.target.closest('#start-btn')) closeStartMenu();
    });

    var taskbar = document.getElementById('taskbar');
    if (taskbar && !document.getElementById('taskbar-search-btn')) {
      var searchBtn = document.createElement('button');
      searchBtn.id = 'taskbar-search-btn';
      searchBtn.className = 'taskbar-search-btn';
      searchBtn.title = 'Search (Ctrl+K)';
      searchBtn.innerHTML = '\u2315';
      searchBtn.addEventListener('click', function() {
        if (window.MaiSearch) window.MaiSearch.open();
      });
      taskbar.insertBefore(searchBtn, document.getElementById('taskbar-clock'));
    }

    if (window.MaiRouter) window.MaiRouter.init();
  });
})();
