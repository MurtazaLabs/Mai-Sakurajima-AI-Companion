// Space — Graph
(function(){'use strict'
var _intervals = []
var _id = 'graph'
var simulation = null
var svgEl = null

var COLORS = {
  cognitive:'#9D7BFF', entity:'#4FA7FF', memory:'#67E8F9', thought:'#3DDC97',
  rule:'#FFC857', emotion:'#FF5D73', belief:'#B794FF',
  'goal:active':'#FF8A65', 'goal:completed':'#3DDC97', 'goal:failed':'#FF5D73'
}
var DEFAULT_COLOR = '#70798C'
var LABELS = {
  belief:'Belief', emotion:'Emotion', memory:'Memory', thought:'Thought', rule:'Rule',
  'goal:active':'Active Goal', 'goal:completed':'Completed Goal', 'goal:failed':'Failed Goal',
  entity:'Entity', person:'Person', place:'Place', project:'Project', technology:'Technology',
  event:'Event', skill:'Skill', media:'Media', organization:'Organization',
  relationship:'Relationship', interest:'Interest', character:'Character'
}

function nodeColor(t){ return COLORS[t] || DEFAULT_COLOR }

function renderGraph(container, data){
  var nodes = (data.nodes || []).map(function(n,i){ return Object.assign({}, n, {index:i}) })
  var edges = (data.edges || []).map(function(e){
    return {
      source: typeof e.source === 'object' ? e.source.id : e.source,
      target: typeof e.target === 'object' ? e.target.id : e.target,
      relation: e.relation || '',
      weight: e.weight || 1
    }
  })

  if(!nodes.length){
    container.innerHTML = '<div class="no-data"><span>No graph data available yet</span></div>'
    return
  }

  var uniqueTypes = new Set(nodes.map(function(n){ return n.type }))

  var statsEl = document.getElementById(_id + '-stats')
  var typeBreakdown = data.type_breakdown || {}
  var tbHtml = Object.entries(typeBreakdown).sort(function(a,b){ return b[1]-a[1] }).slice(0,5).map(function(kv){ return kv[0] + ':' + kv[1] }).join(' · ')
  if(statsEl) statsEl.innerHTML = nodes.length + ' nodes · ' + edges.length + ' edges · ' + uniqueTypes.size + ' types' + (tbHtml ? ' <span style="opacity:0.5">|</span> ' + tbHtml : '')

  var legendEl = document.getElementById(_id + '-legend')
  if(legendEl){
    var ordered = ['cognitive','entity','memory','thought','rule','emotion']
    var shown = new Set()
    var lhtml = ''
    ordered.forEach(function(g){
      if(uniqueTypes.has(g) && !shown.has(g)){ shown.add(g); lhtml += '<span class="legend-dot" style="background:' + nodeColor(g) + '"></span>' + g + ' ' }
    })
    uniqueTypes.forEach(function(t){
      if(!shown.has(t) && LABELS[t]){ shown.add(t); lhtml += '<span class="legend-dot" style="background:' + nodeColor(t) + '"></span>' + LABELS[t] + ' ' }
    })
    legendEl.innerHTML = lhtml
  }

  var rect = container.getBoundingClientRect()
  var W = rect.width, H = Math.max(rect.height, 400)

  svgEl = d3.select(container).append('svg')
    .attr('width', W).attr('height', H)
    .style('background', 'transparent')
    .style('display', 'block')

  var defs = svgEl.append('defs')
  defs.append('marker').attr('id', 'arrow').attr('viewBox', '0 -5 10 10')
    .attr('refX', 20).attr('refY', 0).attr('markerWidth', 6).attr('markerHeight', 6)
    .attr('orient', 'auto').append('path')
    .attr('d', 'M0,-5L10,0L0,5').attr('fill', 'rgba(255,255,255,0.12)')

  var g = svgEl.append('g')

  var link = g.append('g').selectAll('line').data(edges).join('line')
    .attr('stroke', 'rgba(255,255,255,0.12)')
    .attr('stroke-width', function(d){ return Math.max(0.5, Math.min(3, (d.weight || 1) * 1.5)) })
    .attr('marker-end', 'url(#arrow)')

  var nodeGroup = g.append('g').selectAll('g').data(nodes).join('g').style('cursor', 'pointer')

  nodeGroup.append('circle')
    .attr('r', function(d){ return d.group === 'cognitive' ? 8 : 6 })
    .attr('fill', function(d){ return nodeColor(d.type) })
    .attr('stroke', 'rgba(255,255,255,0.2)')
    .attr('stroke-width', 1)

  nodeGroup.append('text')
    .text(function(d){
      var name = d.name || d.id || ''
      return name.length > 25 ? name.substring(0,22) + '...' : name
    })
    .attr('dx', 14).attr('dy', 4)
    .attr('fill', 'var(--text-secondary,#B7BECF)')
    .attr('font-size', '11px')
    .attr('font-family', 'system-ui,sans-serif')
    .attr('pointer-events', 'none')

  nodeGroup.append('title').text(function(d){ return d.name || d.id || '' })

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(function(d){ return d.id }).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide(function(d){ return d.group === 'cognitive' ? 14 : 10 }))
    .on('tick', function(){
      link.attr('x1', function(d){ return d.source.x }).attr('y1', function(d){ return d.source.y })
        .attr('x2', function(d){ return d.target.x }).attr('y2', function(d){ return d.target.y })
      nodeGroup.attr('transform', function(d){ return 'translate(' + d.x + ',' + d.y + ')' })
    })

  var drag = d3.drag()
    .on('start', function(event, d){
      if(!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x; d.fy = d.y
    })
    .on('drag', function(event, d){ d.fx = event.x; d.fy = event.y })
    .on('end', function(event, d){
      if(!event.active) simulation.alphaTarget(0)
      d.fx = null; d.fy = null
    })
  nodeGroup.call(drag)

  var tooltip = document.getElementById(_id + '-tooltip')
  nodeGroup.on('mouseenter', function(event, d){
    var meta = d.metadata || {}
    var detail = ''
    if(meta.confidence) detail += 'Confidence: ' + (meta.confidence * 100).toFixed(0) + '%'
    if(meta.status) detail += (detail ? ' · ' : '') + 'Status: ' + meta.status
    if(meta.description) detail += (detail ? ' · ' : '') + meta.description
    if(meta.text) detail += (detail ? ' · ' : '') + meta.text.substring(0,60)
    if(meta.conclusion) detail += (detail ? ' · ' : '') + meta.conclusion.substring(0,60)
    if(meta.emotion_type) detail += (detail ? ' · ' : '') + 'Emotion: ' + meta.emotion_type
    if(meta.predicate) detail += (detail ? ' · ' : '') + 'rel: ' + meta.predicate
    if(meta.intensity !== undefined) detail += (detail ? ' · ' : '') + 'intensity: ' + meta.intensity.toFixed(2)
    tooltip.innerHTML = '<div class="tt-label">' + (LABELS[d.type] || d.type) + '</div><div class="tt-name">' + (d.name || d.id) + '</div>' + (detail ? '<div class="tt-detail">' + detail + '</div>' : '')
    tooltip.className = 'graph-tooltip visible'
    var cr = container.getBoundingClientRect()
    var tx = event.clientX - cr.left + 12, ty = event.clientY - cr.top - 10
    if(tx + 200 > cr.width) tx = cr.width - 210
    if(ty < 0) ty = 10
    tooltip.style.left = tx + 'px'; tooltip.style.top = ty + 'px'
  }).on('mouseleave', function(){ tooltip.className = 'graph-tooltip' })

  var searchEl = document.getElementById(_id + '-search')
  if(searchEl){
    searchEl.addEventListener('input', function(){
      var q = this.value.toLowerCase().trim()
      nodeGroup.each(function(d){
        var el = d3.select(this)
        var match = !q || (d.name || '').toLowerCase().includes(q) || (d.id || '').toLowerCase().includes(q)
        el.select('circle').attr('fill', match ? nodeColor(d.type) : '#333355')
          .attr('r', match ? (d.group === 'cognitive' ? 8 : 6) : 2)
        el.select('text').attr('opacity', match ? 1 : 0.15)
      })
      link.attr('opacity', q ? 0.05 : 1)
    })
  }
}

function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML =
    '<div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">' +
      '<input id="' + _id + '-search" type="text" class="memory-search-input" placeholder="Filter nodes..." style="flex:1;padding:10px 14px;border-radius:10px;border:1px solid var(--glass-border);background:rgba(0,0,0,0.3);color:var(--text-primary);font-size:13px;outline:none">' +
      '<div id="' + _id + '-stats" style="font-size:12px;color:var(--text-muted);white-space:nowrap">—</div>' +
      '<button id="' + _id + '-prune" class="graph-prune-btn" title="Remove auto-generated belief-loop nodes" style="padding:6px 12px;border:1px solid rgba(255,93,115,0.3);border-radius:8px;background:rgba(255,93,115,0.08);color:var(--danger);font-size:11px;cursor:pointer;transition:all 150ms ease">Prune</button>' +
    '</div>' +
    '<div id="' + _id + '-legend" class="graph-legend" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;font-size:11px;color:var(--text-muted)"></div>' +
    '<div id="' + _id + '-container" class="graph-container" style="position:relative;min-height:500px;border-radius:14px;border:1px solid var(--glass-border);overflow:hidden;background:rgba(0,0,0,0.2)">' +
      '<div id="' + _id + '-loading" class="no-data"><span>Loading graph...</span></div>' +
      '<div id="' + _id + '-tooltip" class="graph-tooltip"></div>' +
    '</div>'

  function loadData(){
    var container = document.getElementById(_id + '-container')
    if(!container) return
    var loadingEl = document.getElementById(_id + '-loading')
    fetch('/api/graph')
      .then(function(r){
        if(!r.ok) throw new Error('HTTP ' + r.status)
        return r.json()
      })
      .then(function(data){ renderGraph(container, data) })
      .catch(function(e){
        if(loadingEl) loadingEl.innerHTML = '<span>Cannot load graph</span><span style="font-size:11px;color:var(--danger)">' + e.message + '</span>'
      })
  }

  function loadD3(){
    if(typeof d3 !== 'undefined'){ loadData(); return }
    var s = document.createElement('script')
    s.src = 'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js'
    s.onload = loadData
    s.onerror = function(){
      // Fallback: try unpkg if jsdelivr fails
      s.src = 'https://unpkg.com/d3@7/dist/d3.min.js'
      s.onerror = function(){
        var loadingEl = document.getElementById(_id + '-loading')
        if(loadingEl) loadingEl.innerHTML = '<span>Cannot load graph</span><span style="font-size:11px;color:var(--danger)">d3 library failed to load (try refreshing)</span>'
      }
    }
    document.head.appendChild(s)
  }

  loadD3()

  var pruneBtn = document.getElementById(_id + '-prune')
  if(pruneBtn){
    pruneBtn.addEventListener('click', function(){
      var orig = this.textContent
      this.textContent = 'Pruning...'
      this.disabled = true
      var btn = this
      fetch('/api/graph/prune', {method:'POST'})
        .then(function(r){ return r.json() })
        .then(function(resp){
          loadData()
          btn.textContent = 'Removed ' + (resp.removed || 0)
          setTimeout(function(){ btn.textContent = orig; btn.disabled = false }, 2000)
        })
        .catch(function(){
          btn.textContent = 'Error'
          setTimeout(function(){ btn.textContent = orig; btn.disabled = false }, 2000)
        })
    })
  }
}

function _destroy(){
  _intervals.forEach(function(iv) { clearInterval(iv) })
  _intervals.length = 0
  if(simulation){ simulation.stop(); simulation = null }
  svgEl = null
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Knowledge Graph', subtitle: 'Visual knowledge network', icon: '🕸', init: _init, destroy: _destroy })
})()
