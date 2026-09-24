// Space — Memory
(function(){'use strict'
var _intervals = []
var _id = 'memory'
var TYPE_COLORS = {semantic:'var(--accent)',episodic:'var(--accent-secondary)',procedural:'var(--warning)',autobiographical:'var(--accent-highlight)',conversation:'var(--text-muted)'}

function timeGroup(ts){
  if(!ts) return 'Unknown'
  var d = new Date(ts * 1000), n = new Date()
  var sameDay = function(a,b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate() }
  if(sameDay(d,n)) return 'Today'
  var y = new Date(n); y.setDate(y.getDate() - 1)
  if(sameDay(d,y)) return 'Yesterday'
  var wk = new Date(n); wk.setDate(wk.getDate() - n.getDay())
  if(d >= wk) return 'This Week'
  if(d.getMonth() === n.getMonth() && d.getFullYear() === n.getFullYear()) return 'This Month'
  return 'Older'
}

function renderStats(el, data){
  if(!data || !data.hierarchy){ el.innerHTML = '<div class="no-data"><span>Memory system unavailable</span></div>'; return }
  var h = data.hierarchy
  var html = '<div class="memory-grid">'
  var types = ['semantic','episodic','procedural','autobiographical']
  types.forEach(function(t){
    html += '<div class="memory-card"><div class="count" style="color:' + TYPE_COLORS[t] + '">' + (h[t] || 0) + '</div><div class="label">' + t + '</div></div>'
  })
  html += '</div><div class="memory-total"><span class="total-label">Total</span><span class="total-count">' + (h.total || 0) + '</span></div>'
  if(data.vector_count !== undefined) html += '<div class="memory-total" style="margin-top:-4px"><span class="total-label">Vector Store</span><span class="total-count" style="color:var(--accent)">' + data.vector_count + '</span></div>'
  el.innerHTML = html
}

function renderGrouped(el, data){
  if(!data || !data.timeline || !data.timeline.length){ el.innerHTML = '<div class="no-data"><span>No memories yet</span></div>'; return }
  var groups = {}
  data.timeline.forEach(function(item){
    var g = timeGroup(item.timestamp)
    if(!groups[g]) groups[g] = []
    groups[g].push(item)
  })
  var order = ['Today','Yesterday','This Week','This Month','Older','Unknown']
  var html = ''
  order.forEach(function(g){
    if(!groups[g]) return
    html += '<div class="memory-section-label">' + g + '</div>'
    groups[g].forEach(function(item){
      var type = item.type || 'conversation', ts = item.timestamp ? new Date(item.timestamp * 1000).toLocaleString() : ''
      var text = item.content || '(empty)', source = item.source || (item.metadata && item.metadata.speaker) || ''
      var tags = item.tags || (item.metadata && item.metadata.tags) || [], tagStr = tags.length ? tags.slice(0,3).join(', ') : ''
      var imp = item.importance || (item.metadata && item.metadata.importance)
      html += '<div class="memory-card-item">' +
        '<div class="mci-header"><span class="timeline-dot ' + type + '" style="flex-shrink:0"></span><div class="mci-text">' + text + '</div></div>' +
        '<div class="mci-meta">' + type + (source ? ' · ' + source : '') + (ts ? ' · ' + ts : '') + (imp ? ' · <span style="color:var(--warning)">importance ' + (typeof imp === 'number' ? imp.toFixed(2) : imp) + '</span>' : '') + '</div>' +
        (tagStr ? '<div class="mci-tags">' + tagStr.split(', ').map(function(t){ return '<span class="mci-tag">' + t + '</span>' }).join('') + '</div>' : '') +
      '</div>'
    })
  })
  el.innerHTML = html
}

function renderSearchResults(el, data){
  if(!data || !data.results || !data.results.length){ el.innerHTML = '<div class="no-data"><span>No results found</span></div>'; return }
  var html = ''
  data.results.forEach(function(r){
    var text = r.text || r.content || '(empty)'
    var sim = r.similarity !== undefined ? (r.similarity * 100).toFixed(0) + '%' : ''
    var imp = r.importance
    html += '<div class="memory-card-item">' +
      '<div class="mci-header"><span class="timeline-dot conversation" style="flex-shrink:0"></span><div class="mci-text">' + text + '</div></div>' +
      '<div class="mci-meta">similarity ' + sim + (imp ? ' · <span style="color:var(--warning)">importance ' + (typeof imp === 'number' ? imp.toFixed(2) : imp) + '</span>' : '') + '</div>' +
    '</div>'
  })
  el.innerHTML = html
}

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML =
    '<div id="memory-stats" class="space-body-section"></div>' +
    '<div class="memory-search" style="display:flex;gap:8px;margin-bottom:16px">' +
      '<input id="memory-search" type="text" class="memory-search-input" placeholder="Search memories..." style="flex:1;padding:10px 14px;border-radius:10px;border:1px solid var(--glass-border);background:rgba(0,0,0,0.3);color:var(--text-primary);font-size:13px;outline:none">' +
      '<button id="memory-search-btn" class="memory-search-btn" style="padding:10px 18px;border-radius:10px;border:none;background:var(--accent);color:#fff;font-size:13px;cursor:pointer">Search</button>' +
    '</div>' +
    '<div id="memory-timeline" class="space-body-section"></div>'

  var se = document.getElementById('memory-stats'), te = document.getElementById('memory-timeline')
  var si = document.getElementById('memory-search'), sb = document.getElementById('memory-search-btn')

  try{ var r = await fetch('/api/memory/stats'); if(r.ok) renderStats(se, await r.json()) } catch(e){}

  async function loadTimeline(){
    try{ var r = await fetch('/api/memory/timeline?limit=80'); if(r.ok) renderGrouped(te, await r.json()) } catch(e){}
  }
  loadTimeline()

  async function doSearch(){
    var q = si.value.trim(); if(!q){ loadTimeline(); return }
    try{ var r = await fetch('/api/memory?query=' + encodeURIComponent(q) + '&top_k=20'); if(r.ok) renderSearchResults(te, await r.json()) } catch(e){}
  }
  sb.addEventListener('click', doSearch)
  si.addEventListener('keydown', function(e){ if(e.key === 'Enter') doSearch() })
}

function _destroy(){
  _intervals.forEach(function(iv) { clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Memory', subtitle: 'Semantic, episodic & procedural memory', icon: '🧠', init: _init, destroy: _destroy })
})()
