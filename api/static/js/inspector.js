// Space — Event Inspector (Event Fabric telemetry)
(function(){'use strict'
var _id = 'inspector'
var _intervals = []
var _tab = 'timeline'
var _corrFilter = ''
var _retriesOnly = false

function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] }) }
function fmtTime(ts){ if(!ts) return '—'; return new Date(ts * 1000).toLocaleTimeString() }
function fmtMs(v){ if(v == null) return '—'; return Number(v).toFixed(1) + 'ms' }

function badge(o){
  var cls = o === 'SUCCESS' ? 'insp-ok' : (o === 'FAILED' ? 'insp-bad' : 'insp-warn')
  return '<span class="insp-badge ' + cls + '">' + esc(o || '—') + '</span>'
}
function prioCls(p){ return p === 'CRITICAL' ? 'insp-bad' : (p === 'HIGH' ? 'insp-warn' : '') }
function metaChips(m){
  if(!m || typeof m !== 'object') return ''
  var keys = Object.keys(m).slice(0, 6)
  if(!keys.length) return ''
  return '<div class="insp-meta">' + keys.map(function(k){
    var v = typeof m[k] === 'object' ? JSON.stringify(m[k]) : String(m[k])
    return '<span class="insp-meta-chip">' + esc(k) + '=' + esc(v) + '</span>'
  }).join('') + '</div>'
}
var SAFE_KEYS = ['id','timestamp','type','version','source','target','priority','correlation_id','causation_id','outcome','error','attempt','subscribers','handler_times_ms','handler_failures','queue_delay_ms','execution_ms','metadata','depth']
function pickSafe(r){
  if(!r || typeof r !== 'object') return {}
  var o = {}
  SAFE_KEYS.forEach(function(k){ if(r[k] !== undefined) o[k] = r[k] })
  return o
}

async function api(path, options){
  try { var r = await fetch(path, options || {}); if(!r.ok) return null; return await r.json() } catch(e){ return null }
}

// ── Status strip ──────────────────────────────────────────────
function renderStrip(el, s){
  if(!s || !s.capture_count){
    el.innerHTML = '<div class="no-data"><span>Event Inspector unavailable — start Mai first</span></div>'
    return
  }
  var cls = s.status === 'error' ? 'insp-bad' : (s.status === 'warn' ? 'insp-warn' : 'insp-ok')
  var w60 = s.windows && s.windows['60'] ? s.windows['60'] : {}
  var w3600 = s.windows && s.windows['3600'] ? s.windows['3600'] : {}
  var html =
    '<div class="insp-strip">' +
      '<div class="insp-strip-cell"><span class="insp-badge ' + cls + '">' + esc(s.status) + '</span></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">Buffered</div><div class="insp-strip-val">' + s.buffered + ' / ' + s.capacity + '</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">Captured</div><div class="insp-strip-val">' + s.capture_count + '</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">1m</div><div class="insp-strip-val">' + (w60.messages || 0) + ' msgs' + (w60.failures ? ' <span class="insp-bad">' + w60.failures + '✗</span>' : '') + '</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">1h</div><div class="insp-strip-val">' + (w3600.messages || 0) + ' msgs</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">Fail 5m</div><div class="insp-strip-val">' + (s.failure_rate_5m * 100).toFixed(1) + '%</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">Dead 5m</div><div class="insp-strip-val">' + (s.dead_letters_5m || 0) + '</div></div>' +
      '<div class="insp-strip-cell"><div class="insp-strip-label">Dropped</div><div class="insp-strip-val">' + (s.overflow || 0) + '</div></div>' +
      '<button id="insp-export" class="insp-btn">Export JSONL</button>' +
    '</div>'
  if((s.warnings || []).length) html += '<div class="insp-warnings">' + s.warnings.map(function(w){ return '<div class="insp-warn">⚠ ' + esc(w) + '</div>' }).join('') + '</div>'
  if((s.issues || []).length) html += '<div class="insp-warnings">' + s.issues.map(function(w){ return '<div class="insp-bad">⛔ ' + esc(w) + '</div>' }).join('') + '</div>'
  el.innerHTML = html
  var btn = document.getElementById('insp-export')
  if(btn) btn.addEventListener('click', async function(){
    var r = await api('/api/inspector/export', { method: 'POST' })
    if(r && r.path) btn.textContent = 'Exported ' + r.count + ' → ' + r.path.split('/').pop()
  })
}

// ── Timeline ──────────────────────────────────────────────────
function renderTimeline(el, data){
  if(!data || !data.records || !data.records.length){ el.innerHTML = '<div class="no-data"><span>No messages yet</span></div>'; return }
  var html = '<div class="insp-table-wrap"><table class="insp-table"><thead><tr>' +
    '<th>Time</th><th>Type</th><th>Source</th><th>Priority</th><th>Outcome</th><th>Attempt</th><th>Exec</th><th>Correlation</th>' +
    '</tr></thead><tbody>'
  data.records.forEach(function(r){
    r = pickSafe(r)
    html += '<tr>' +
      '<td>' + fmtTime(r.timestamp) + '</td>' +
      '<td class="insp-mono">' + esc(r.type) + metaChips(r.metadata) + '</td>' +
      '<td>' + esc(r.source || '—') + '</td>' +
      '<td><span class="insp-badge ' + prioCls(r.priority) + '">' + esc(r.priority) + '</span></td>' +
      '<td>' + badge(r.outcome) + '</td>' +
      '<td>' + (r.attempt > 1 ? '<span class="insp-warn">' + r.attempt + '</span>' : r.attempt) + '</td>' +
      '<td>' + fmtMs(r.execution_ms) + '</td>' +
      (r.correlation_id ? '<td><a href="#" class="insp-link" data-corr="' + esc(r.correlation_id) + '">' + esc(r.correlation_id).replace('conversation_','c_') + '</a></td>' : '<td>—</td>') +
    '</tr>'
  })
  html += '</tbody></table></div>'
  el.innerHTML = html
  el.querySelectorAll('.insp-link').forEach(function(a){
    a.addEventListener('click', function(ev){
      ev.preventDefault()
      _corrFilter = a.dataset.corr
      switchTab('trace')
    })
  })
}

// ── Trace ─────────────────────────────────────────────────────
function renderTrace(el, data){
  if(!data || !data.count){
    el.innerHTML = '<div class="no-data"><span>' + (data && data.error ? esc(data.error) : 'No records for this correlation') + '</span></div>'
    return
  }
  var html = '<div class="insp-trace-head">Trace <span class="insp-mono">' + esc(data.correlation_id) + '</span> — ' + data.count + ' messages</div><div class="insp-trace">'
  data.nodes.forEach(function(n){
    n = pickSafe(n)
    var pad = n.depth * 22
    var sub = (n.subscribers || []).join(', ')
    html += '<div class="insp-trace-row" style="padding-left:' + pad + 'px">' +
      '<span class="insp-trace-conn">' + (n.depth ? '└─ ' : '● ') + '</span>' +
      '<span class="insp-mono">' + esc(n.type) + '</span> ' +
      (n.attempt > 1 ? '<span class="insp-badge insp-warn">attempt ' + n.attempt + '</span> ' : '') +
      badge(n.outcome) + ' ' +
      '<span class="insp-muted">' + fmtMs(n.execution_ms) + '</span>' +
      metaChips(n.metadata) +
      (n.error ? ' <span class="insp-bad">' + esc(n.error).slice(0, 80) + '</span>' : '') +
      (sub ? '<div class="insp-muted" style="padding-left:22px">↳ ' + esc(sub) + '</div>' : '') +
    '</div>'
  })
  html += '</div>'
  el.innerHTML = html
}

// ── Subscribers ───────────────────────────────────────────────
function renderSubscriberGraph(el, subs){
  var typeCount = {}
  subs.forEach(function(s){ var t = s.types || {}; Object.keys(t).forEach(function(k){ typeCount[k] = (typeCount[k] || 0) + t[k] }) })
  var types = Object.keys(typeCount).sort(function(a, b){ return typeCount[b] - typeCount[a] }).slice(0, 10)
  var handlers = subs.slice(0, 10)
  if(!types.length || !handlers.length) return
  var maxC = 1
  var links = []
  handlers.forEach(function(s, i){
    var t = s.types || {}
    Object.keys(t).forEach(function(k){
      var j = types.indexOf(k)
      if(j >= 0){ maxC = Math.max(maxC, t[k]); links.push({ i: i, j: j, c: t[k] }) }
    })
  })
  if(!links.length) return
  var rowH = 26, pad = 22, w = 520
  var h = Math.max(handlers.length, types.length) * rowH + 12
  var hw = 190, tw = 170
  var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" class="insp-graph" role="img" aria-label="subscriber-event graph">'
  links.forEach(function(l){
    var x1 = hw, x2 = w - tw
    var y1 = pad + l.i * rowH + rowH / 2
    var y2 = pad + l.j * rowH + rowH / 2
    var f = l.c / maxC
    svg += '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" ' +
      'stroke="#7aa2f7" stroke-width="' + (1 + 3 * f).toFixed(2) + '" stroke-opacity="' + (0.15 + 0.55 * f).toFixed(2) + '"/>'
  })
  handlers.forEach(function(s, i){
    var y = pad + i * rowH + rowH / 2
    var label = s.name.length > 26 ? s.name.slice(0, 25) + '…' : s.name
    svg += '<text x="' + (hw - 8) + '" y="' + y + '" text-anchor="end" class="insp-graph-text">' + esc(label) + '</text>'
  })
  types.forEach(function(t, j){
    var y = pad + j * rowH + rowH / 2
    svg += '<text x="' + (w - tw + 8) + '" y="' + y + '" class="insp-graph-text">' + esc(t) + '</text>'
  })
  svg += '</svg>'
  el.innerHTML = svg
}

function renderSubscribers(el, data){
  if(!data || !data.subscribers || !data.subscribers.length){ el.innerHTML = '<div class="no-data"><span>No subscriber activity yet</span></div>'; return }
  var html = '<div class="insp-graph-wrap"></div><div class="insp-table-wrap"><table class="insp-table"><thead><tr>' +
    '<th>Handler</th><th>Messages</th><th>Failures</th><th>p50</th><th>p95</th><th>Last</th></tr></thead><tbody>'
  data.subscribers.forEach(function(s){
    html += '<tr><td class="insp-mono">' + esc(s.name) + '</td><td>' + s.count + '</td>' +
      '<td>' + (s.failures ? '<span class="insp-bad">' + s.failures + '</span>' : '0') + '</td>' +
      '<td>' + fmtMs(s.p50) + '</td><td>' + fmtMs(s.p95) + '</td><td>' + fmtTime(s.last_time) + '</td></tr>'
  })
  html += '</tbody></table></div>'
  el.innerHTML = html
  renderSubscriberGraph(el.querySelector('.insp-graph-wrap'), data.subscribers)
}

// ── Queues ────────────────────────────────────────────────────
function renderQueues(el, data){
  if(!data || !data.queues || !Object.keys(data.queues).length){ el.innerHTML = '<div class="no-data"><span>No queue data</span></div>'; return }
  var order = ['CRITICAL','HIGH','NORMAL','LOW','BACKGROUND']
  var html = '<div class="insp-queues">'
  order.forEach(function(name){
    var q = data.queues[name]
    if(!q) return
    var pct = Math.min(100, Math.round((q.occupancy / q.max_queue) * 100))
    var cls = pct > 80 ? 'insp-q-high' : (pct > 40 ? 'insp-q-mid' : '')
    html += '<div class="insp-q-row"><div class="insp-q-label">' + name + '</div>' +
      '<div class="insp-q-bar"><div class="insp-q-fill ' + cls + '" style="width:' + pct + '%"></div></div>' +
      '<div class="insp-q-num">' + q.occupancy + '/' + q.max_queue +
      (q.oldest_wait_ms > 0 ? ' <span class="insp-muted">oldest ' + fmtMs(q.oldest_wait_ms) + '</span>' : '') +
      (q.dropped ? ' <span class="insp-bad">' + q.dropped + ' dropped</span>' : '') + '</div></div>'
  })
  html += '</div>'
  el.innerHTML = html
}

// ── Latency ───────────────────────────────────────────────────
function renderLatency(el, data){
  if(!data || !data.latency || !data.latency.length){ el.innerHTML = '<div class="no-data"><span>No latency data yet</span></div>'; return }
  var html = '<div class="insp-table-wrap"><table class="insp-table"><thead><tr>' +
    '<th>Event Type</th><th>Count</th><th>p50</th><th>p95</th><th>p99</th></tr></thead><tbody>'
  data.latency.forEach(function(l){
    html += '<tr><td class="insp-mono">' + esc(l.type) + '</td><td>' + l.count + '</td>' +
      '<td>' + fmtMs(l.p50) + '</td><td>' + fmtMs(l.p95) + '</td><td>' + fmtMs(l.p99) + '</td></tr>'
  })
  html += '</tbody></table></div>'
  el.innerHTML = html
}

// ── Tabs + refresh ────────────────────────────────────────────
var TAB_DEFS = [
  { id: 'timeline', label: 'Timeline' },
  { id: 'trace', label: 'Trace' },
  { id: 'subscribers', label: 'Subscribers' },
  { id: 'queues', label: 'Queues' },
  { id: 'latency', label: 'Latency' },
]

function switchTab(id){ _tab = id; syncFilters(); refreshTab() }

function buildTabs(container){
  var html = '<div class="insp-tabs">'
  TAB_DEFS.forEach(function(t){
    html += '<button class="insp-tab" data-tab="' + t.id + '">' + t.label + '</button>'
  })
  html += '</div>' +
    '<div class="insp-filters" id="insp-filters">' +
      '<label class="insp-check"><input type="checkbox" id="insp-retries" ' + (_retriesOnly ? 'checked' : '') + '/> Retries only (attempt &gt; 1)</label>' +
    '</div>' +
    '<div id="insp-body" class="insp-body"></div>'
  container.innerHTML = html
  container.querySelectorAll('.insp-tab').forEach(function(btn){
    btn.addEventListener('click', function(){ switchTab(btn.dataset.tab) })
  })
  var retryBox = document.getElementById('insp-retries')
  if(retryBox) retryBox.addEventListener('change', function(){
    _retriesOnly = retryBox.checked
    if(_tab === 'timeline') refreshTab()
  })
  if(_corrFilter) document.querySelector('.insp-tab[data-tab="trace"]').textContent = 'Trace: ' + _corrFilter.replace('conversation_','c_')
  document.querySelectorAll('.insp-tab').forEach(function(b){ b.classList.toggle('active', b.dataset.tab === _tab) })
  syncFilters()
}

function syncFilters(){
  var bar = document.getElementById('insp-filters')
  if(!bar) return
  bar.style.display = _tab === 'timeline' ? '' : 'none'
}

async function refreshTab(){
  var body = document.getElementById('insp-body')
  if(!body) return
  var data = null
  if(_tab === 'timeline') data = await api('/api/inspector/records?limit=150' + (_retriesOnly ? '&retries=1' : ''))
  else if(_tab === 'trace') data = await api('/api/inspector/trace/' + encodeURIComponent(_corrFilter || ''))
  else if(_tab === 'subscribers') data = await api('/api/inspector/subscribers')
  else if(_tab === 'queues') data = await api('/api/inspector/queues')
  else if(_tab === 'latency') data = await api('/api/inspector/latency')
  if(!data && _tab !== 'trace'){ body.innerHTML = '<div class="no-data"><span>Inspector offline</span></div>'; return }
  if(_tab === 'timeline') renderTimeline(body, data)
  else if(_tab === 'trace') renderTrace(body, data)
  else if(_tab === 'subscribers') renderSubscribers(body, data)
  else if(_tab === 'queues') renderQueues(body, data)
  else if(_tab === 'latency') renderLatency(body, data)
}

async function refreshStrip(){
  var el = document.getElementById('insp-strip')
  if(!el) return
  var s = await api('/api/inspector/summary')
  renderStrip(el, s)
}

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML =
    '<div id="insp-strip" class="space-body-section"></div>' +
    '<div id="insp-tabs-wrap" class="space-body-section"></div>'

  buildTabs(document.getElementById('insp-tabs-wrap'))
  refreshStrip()
  refreshTab()
  _intervals.push(setInterval(refreshStrip, 1000))
  _intervals.push(setInterval(refreshTab, 2000))
}

function _destroy(){
  _intervals.forEach(function(iv) { clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Event Inspector', subtitle: 'Event fabric telemetry & traces', icon: '🔭', init: _init, destroy: _destroy })
})()
