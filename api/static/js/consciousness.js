// Space — Consciousness
(function() {
  'use strict';
  var _intervals = [];
  var _id = 'consciousness';

  function render(data) {
    var el = document.getElementById(_id + '-content');
    if (!el) return;
    if (!data || !data.ready) {
      el.innerHTML = '<div class="no-data"><span>System offline</span></div>';
      return;
    }

    var emotion = data.emotion || {};
    var cog = data.cognitive || {};
    var personality = data.personality || {};
    var goals = data.goals || {};
    var speaker = data.speaker || {};
    var activeGoals = goals.active || [];
    var workingMem = (cog.working_memory || []).slice(-5);
    var recentThoughts = (cog.recent_thoughts || []).slice(-5);
    var personalityTraits = Object.entries(personality).slice(0, 5);
    var emoName = emotion.emotion || emotion.name || 'Neutral';
    var emoValence = emotion.valence !== undefined ? emotion.valence.toFixed(2) : '—';
    var emoArousal = emotion.arousal !== undefined ? emotion.arousal.toFixed(2) : '—';
    var confidence = cog.confidence || 0;

    var html = '';

    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">';

    html += '<div><div class="cog-section-label">Emotion</div>';
    html += '<div class="cog-emotion-display"><span class="cog-emotion-name">' + emoName + '</span>';
    html += '<span class="cog-emotion-valence">Valence ' + emoValence + ' · Arousal ' + emoArousal + '</span></div></div>';

    html += '<div><div class="cog-section-label">Speaker</div>';
    html += '<div class="cog-row"><span class="cog-label">Name</span><span class="cog-value">' + (speaker.name || 'Unknown') + '</span></div></div>';

    html += '</div>';

    html += '<div style="margin-top:16px"><div class="cog-section-label">Cognitive State</div>';
    html += '<div class="cog-topic">' + (cog.current_topic || 'No active topic') + '</div>';
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">';
    if (cog.attention_focus) {
      html += '<div class="cog-row"><span class="cog-label">Focus</span><span class="cog-value">' + cog.attention_focus + '</span></div>';
    }
    if (cog.current_goal) {
      html += '<div class="cog-row"><span class="cog-label">Current Goal</span><span class="cog-value">' + cog.current_goal + '</span></div>';
    }
    html += '</div>';
    html += '<div style="margin-top:8px"><div class="cog-section-label">Confidence</div>';
    html += '<div class="confidence-bar"><div class="confidence-fill" style="width:' + Math.round(confidence * 100) + '%"></div></div>';
    html += '<span style="font-size:11px;color:var(--text-muted)">' + Math.round(confidence * 100) + '%</span></div>';

    if (workingMem.length) {
      html += '<div style="margin-top:16px"><div class="cog-section-label">Working Memory (last ' + workingMem.length + ')</div>';
      workingMem.forEach(function(m) {
        var t = typeof m === 'string' ? m : (m.content || m.text || JSON.stringify(m));
        html += '<div class="cog-memory-item">' + t + '</div>';
      });
      html += '</div>';
    }

    if (recentThoughts.length) {
      html += '<div style="margin-top:16px"><div class="cog-section-label">Recent Thoughts</div>';
      recentThoughts.forEach(function(t) {
        var text = typeof t === 'string' ? t : (t.content || t.text || JSON.stringify(t));
        html += '<div class="cog-thought">' + text + '</div>';
      });
      html += '</div>';
    }

    if (personalityTraits.length) {
      html += '<div style="margin-top:16px"><div class="cog-section-label">Personality</div>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">';
      personalityTraits.forEach(function(kv) {
        html += '<div class="cog-row"><span class="cog-label">' + kv[0] + '</span><span class="cog-value">' + (typeof kv[1] === 'number' ? kv[1].toFixed(2) : kv[1]) + '</span></div>';
      });
      html += '</div></div>';
    }

    if (activeGoals.length) {
      html += '<div style="margin-top:16px"><div class="cog-section-label">Active Goals (' + activeGoals.length + ')</div>';
      activeGoals.slice(0, 8).forEach(function(g) {
        html += '<div class="goal-item"><span class="goal-name">' + (g.name || g.id || 'Goal') + '</span><span class="goal-progress">' + (g.progress !== undefined ? Math.round(g.progress * 100) + '%' : '—') + '</span></div>';
      });
      html += '</div>';
    }

    el.innerHTML = html;
  }

  async function poll() {
    try {
      var res = await fetch('/api/consciousness');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      render(await res.json());
    } catch (e) {
      var el = document.getElementById(_id + '-content');
      if (el) el.innerHTML = '<div class="no-data"><span>Cannot reach Mai</span><span style="font-size:11px">' + e.message + '</span></div>';
    }
  }

  function _init() {
    poll();
    _intervals.push(setInterval(poll, 3000));
  }

  function _destroy() {
    _intervals.forEach(function(iv) { clearInterval(iv); });
    _intervals.length = 0;
  }

  window.MaiSpaces = window.MaiSpaces || {};
  window.MaiSpaces[_id] = { init: _init, destroy: _destroy };
  if (window.MaiRouter) window.MaiRouter.register(_id, { label: 'Consciousness', subtitle: 'Real-time cognitive state', icon: '◈', init: _init, destroy: _destroy });
})();
