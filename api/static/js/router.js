// Space Router — navigable zones, lifecycle, hash routing
(function() {
  'use strict';

  const SPACES = {};
  let currentId = null;
  let currentDestroy = null;
  let container = null;
  let wallpaperEl = null;

  const WALLPAPERS = {
    consciousness: "url('img/Dashboard.png') center/cover no-repeat",
    chat: "url('img/Conversations.png') center/cover no-repeat",
    memory: "url('img/Memory.png') center/cover no-repeat",
    graph: "url('img/Knowledge%20Graph.png') center/cover no-repeat",
    reasoning: "url('img/Brain%20Activity.png') center/cover no-repeat",
    agency: "url('img/Goals.png') center/cover no-repeat",
    voice: "url('img/Voice%20Center.png') center/cover no-repeat",
    system: "url('img/System%20Monitor.png') center/cover no-repeat",
    tasks: "url('img/Scheduler.png') center/cover no-repeat",
    permissions: "url('img/Settings.png') center/cover no-repeat",
    inspector: "url('img/Event%20Log.png') center/cover no-repeat",
  };

  const GLOBAL_INTERVALS = [];

  const ROUTER = {
    register(id, config) { SPACES[id] = config; },

    has(id) { return !!SPACES[id]; },
    getCurrent() { return currentId; },

    addInterval(iv) { GLOBAL_INTERVALS.push(iv); },

    navigateTo(id, opts) {
      if (id === currentId) return;
      const space = SPACES[id];
      if (!space) { console.warn('Unknown space:', id); return; }

      if (currentDestroy) {
        try { currentDestroy(); } catch (e) { console.warn('destroy error:', currentId, e); }
        currentDestroy = null;
      }
      currentId = id;

      if (wallpaperEl) {
        wallpaperEl.style.background = WALLPAPERS[id] || 'linear-gradient(135deg, #0a0c14 0%, #131620 30%, #1a1e2e 60%, #0f111a 100%)';
      }

      const hash = '#space=' + id;
      const replace = opts && opts.replace;
      if (replace) history.replaceState(null, '', '/desktop' + hash);
      else history.pushState(null, '', '/desktop' + hash);

      container.innerHTML =
        '<div class="space-header">' +
          '<h1><span class="space-header-icon">' + (space.icon || '◈') + '</span> ' + space.label + '</h1>' +
          (space.subtitle ? '<div class="space-header-sub">' + space.subtitle + '</div>' : '') +
        '</div>' +
        '<div id="' + id + '-content" class="space-body"></div>';

      currentDestroy = space.destroy || null;
      if (space.init) { try { space.init(); } catch (e) { console.warn('init error:', id, e); } }

      document.querySelectorAll('.sidebar-item').forEach(function(el) {
        el.classList.toggle('active', el.dataset.space === id);
      });
      document.querySelectorAll('.taskbar-app').forEach(function(el) {
        el.classList.toggle('active', el.dataset.space === id);
      });

      container.classList.remove('space-enter');
      void container.offsetWidth;
      container.classList.add('space-enter');
    },

    init: function() {
      container = document.getElementById('space-content');
      wallpaperEl = document.getElementById('wallpaper');

      var match = location.hash.match(/space=(\w+)/);
      if (match && SPACES[match[1]]) {
        ROUTER.navigateTo(match[1], { replace: true });
      }

      window.addEventListener('popstate', function() {
        var m = location.hash.match(/space=(\w+)/);
        if (m && SPACES[m[1]]) ROUTER.navigateTo(m[1], { replace: true });
      });
    },
  };

  window.MaiRouter = ROUTER;
})();
