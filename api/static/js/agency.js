// Space — Agency
(function(){'use strict'
var _intervals = []
var _id = 'agency'

async function loadGoals(){
  var el = document.getElementById(_id + '-goals')
  try{
    var r = await fetch('/api/goals'); if(!r.ok) throw new Error('HTTP ' + r.status)
    var d = await r.json()
    if(d.error){ el.innerHTML = '<div class="no-data"><span>' + d.error + '</span></div>'; return }
    var goals = d.goals || [], stats = d.stats || {}
    var active = goals.filter(function(g){ return g.status === 'active' })
    var other = goals.filter(function(g){ return g.status !== 'active' })
    var html = ''
    if(active.length){
      var g = active[0], p = g.progress || 0, sub = g.subtasks || [], done = sub.filter(function(s){ return s.completed }).length
      html += '<div class="goal-hero" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:18px 20px;margin-bottom:12px">' +
        '<div class="goal-hero-label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">Current Goal</div>' +
        '<div class="goal-hero-title" style="font-size:18px;font-weight:600;color:var(--text-primary)">' + g.description + '</div>' +
        '<div class="goal-progress-bar" style="height:6px;background:var(--glass-strong);border-radius:3px;overflow:hidden;margin:8px 0"><div class="goal-progress-fill" style="height:100%;width:' + Math.round(p*100) + '%;background:var(--accent-highlight);border-radius:3px;transition:width 0.5s ease"></div></div>' +
        '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted)">' +
          '<span>' + Math.round(p*100) + '%</span>' +
          '<span>' + done + '/' + sub.length + ' tasks · ' + (g.turn_count || 0) + ' turns</span>' +
        '</div>' +
        (sub.length ? '<div class="goal-subtasks" style="margin-top:8px">' + sub.map(function(s){ return '<div class="goal-subtask" style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:12px;color:var(--text-secondary)' + (s.completed ? ';opacity:0.5' : '') + '"><input type="checkbox"' + (s.completed ? ' checked' : '') + ' disabled style="accent-color:var(--success)"><span>' + s.description + '</span></div>' }).join('') + '</div>' : '') +
        '<div class="goal-hero-meta" style="font-size:11px;color:var(--text-muted);margin-top:8px;padding-top:8px;border-top:1px solid var(--glass-border)">Priority: ' + (g.priority || 'normal') + ' · Created ' + (g.created_at ? new Date(g.created_at).toLocaleDateString() : '—') + '</div>' +
      '</div>'
    } else {
      html += '<div class="goal-hero" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:18px 20px;margin-bottom:12px"><div class="goal-hero-label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em">Current Goal</div><div class="goal-hero-title" style="font-size:16px;color:var(--text-muted);margin-top:4px">No active goals</div></div>'
    }
    html += '<div class="stat-row" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">' +
      '<span class="stat-chip" style="padding:4px 12px;border-radius:8px;font-size:11px;background:var(--glass);border:1px solid var(--glass-border);color:var(--text-muted)">Active <strong>' + (stats.active||0) + '</strong></span>' +
      '<span class="stat-chip">Completed <strong>' + (stats.completed||0) + '</strong></span>' +
      '<span class="stat-chip">Pending <strong>' + (stats.pending||0) + '</strong></span>' +
      '<span class="stat-chip">Total <strong>' + (stats.total||0) + '</strong></span>' +
      (stats.avg_progress !== undefined ? '<span class="stat-chip">Avg Progress <strong>' + Math.round(stats.avg_progress*100) + '%</strong></span>' : '') +
    '</div>'
    if(other.length){
      html += '<div class="memory-section-label" style="font-size:12px;color:var(--text-muted);margin-bottom:8px;font-weight:600">All Goals</div>'
      other.forEach(function(g){
        var p = g.progress || 0, c = p >= 1 ? 'var(--success)' : 'var(--accent)'
        html += '<div class="goal-card" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:10px;padding:12px 16px;margin-bottom:8px">' +
          '<div class="goal-card-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><span class="goal-card-title" style="font-size:13px;font-weight:500">' + g.description + '</span><span><span class="goal-card-priority ' + g.priority + '" style="font-size:10px;padding:2px 8px;border-radius:4px;background:var(--glass-strong);margin-right:4px">' + g.priority + '</span> <span class="goal-card-status ' + g.status + '" style="font-size:10px;padding:2px 8px;border-radius:4px">' + g.status + '</span></span></div>' +
          '<div class="goal-progress-bar" style="height:4px;background:var(--glass-strong);border-radius:2px;overflow:hidden"><div class="goal-progress-fill" style="height:100%;width:' + Math.round(p*100) + '%;background:' + c + ';border-radius:2px"></div></div>' +
          '<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:4px"><span>' + Math.round(p*100) + '%</span><span>' + (g.subtasks||[]).filter(function(s){ return s.completed }).length + '/' + (g.subtasks||[]).length + ' tasks</span></div>' +
        '</div>'
      })
    }
    el.innerHTML = html
  } catch(e){ el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>' }
}

async function loadWorld(){
  var el = document.getElementById(_id + '-world')
  try{
    var r = await fetch('/api/world/entities'); if(!r.ok) throw new Error('HTTP ' + r.status)
    var d = await r.json()
    if(d.error){ el.innerHTML = '<div class="no-data"><span>' + d.error + '</span></div>'; return }
    var entities = d.entities || [], cats = d.categories || {}, stats = d.stats || {}
    var html = '<div class="stat-row" style="display:flex;gap:8px;margin-bottom:12px"><span class="stat-chip">Entities <strong>' + entities.length + '</strong></span></div>'
    var ce = Object.entries(cats)
    if(ce.length){ html += '<div class="category-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px;margin-bottom:16px">' + ce.map(function(kv){ return '<div class="category-chip" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:10px;padding:12px;text-align:center"><div class="count" style="font-size:20px;font-weight:700;color:var(--accent)">' + kv[1] + '</div><div class="name" style="font-size:10px;color:var(--text-muted);margin-top:2px;text-transform:capitalize">' + kv[0] + '</div></div>' }).join('') + '</div>' }
    if(entities.length){
      html += '<table class="entity-table" style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="color:var(--text-muted);border-bottom:1px solid var(--glass-border)"><th style="text-align:left;padding:6px 8px">Name</th><th style="text-align:left;padding:6px 8px">Category</th><th style="text-align:left;padding:6px 8px">Relations</th></tr></thead><tbody>' + entities.slice(0,80).map(function(e){ return '<tr style="border-bottom:1px solid rgba(255,255,255,0.03)"><td style="padding:6px 8px;color:var(--text-primary)">' + e.name + '</td><td style="padding:6px 8px;color:var(--text-secondary)">' + e.category + '</td><td style="padding:6px 8px;color:var(--text-muted)">' + (e.relations ? Object.keys(e.relations).join(', ') : '—') + '</td></tr>' }).join('') + '</tbody></table>'
    } else { html += '<div class="no-data"><span>No entities yet</span></div>' }
    el.innerHTML = html
  } catch(e){ el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>' }
}

async function loadTools(){
  var el = document.getElementById(_id + '-tools')
  try{
    var r = await fetch('/api/tools'); if(!r.ok) throw new Error('HTTP ' + r.status)
    var d = await r.json()
    if(d.error){ el.innerHTML = '<div class="no-data"><span>' + d.error + '</span></div>'; return }
    var tools = d.tools || [], stats = d.stats || {}
    var total = stats.total_tools || tools.length
    var html = '<div class="stat-row" style="display:flex;gap:8px;margin-bottom:12px"><span class="stat-chip">Tools <strong>' + total + '</strong></span><span class="stat-chip">Total Calls <strong>' + (stats.total_calls || 0) + '</strong></span></div>'
    if(tools.length){
      html += '<div class="tool-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px">' + tools.map(function(t){ return '<div class="tool-card" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:10px;padding:12px 14px"><div class="tool-card-name" style="font-size:13px;font-weight:500;color:var(--text-primary);margin-bottom:4px">' + t.name + '</div><div class="tool-card-desc" style="font-size:11px;color:var(--text-secondary);margin-bottom:4px">' + t.description + '</div><div class="tool-card-category" style="font-size:10px;color:var(--text-muted)">' + t.category + '</div></div>' }).join('') + '</div>'
    } else { html += '<div class="no-data"><span>No tools registered</span></div>' }
    el.innerHTML = html
  } catch(e){ el.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>' }
}

function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML =
    '<div id="' + _id + '-goals" class="space-body-section" style="margin-bottom:16px"></div>' +
    '<h2 style="font-size:16px;font-weight:600;margin-bottom:12px">World Model</h2>' +
    '<div id="' + _id + '-world" class="space-body-section" style="margin-bottom:16px"></div>' +
    '<h2 style="font-size:16px;font-weight:600;margin-bottom:12px">Tools</h2>' +
    '<div id="' + _id + '-tools" class="space-body-section"></div>'
  loadGoals(); loadWorld(); loadTools()
  _intervals.push(setInterval(loadGoals, 5000))
  _intervals.push(setInterval(loadWorld, 10000))
}

function _destroy(){
  _intervals.forEach(function(iv){ clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Agency', subtitle: 'Goals, world model & tool registry', icon: '💭', init: _init, destroy: _destroy })
})()
