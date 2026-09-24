// Space — System (health, components, plugins, config)
(function(){'use strict'
var _intervals = []
var _id = 'system'

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML = '<div class="no-data"><span>Loading...</span></div>'
  try{
    var results = await Promise.all([
      fetch('/api/system/health').then(function(r){ return r.json() }),
      fetch('/api/system/plugins').then(function(r){ return r.json() }),
      fetch('/api/system/about').then(function(r){ return r.json() }),
      fetch('/api/config').then(function(r){ return r.json() }),
      fetch('/api/system/orchestrator').then(function(r){ return r.json() }),
    ])
    var health = results[0], plugins = results[1], about = results[2], config = results[3], orch = results[4]
    var h = health || {}, s = h.summary || {}, comps = h.components || {}
    var pl = plugins || {}, pdata = pl.plugins || {}, hooks = pl.hooks || {}
    var ab = about || {}, rt = ab.runtime || {}
    var html = ''

    // Section: Health
    html += '<div class="sys-section"><div class="sys-section-title">Health</div><div class="sys-health-strip">'
    var healthItems = [
      {label:'OK', count:s.ok||0, cls:'ok'},
      {label:'Warn', count:s.warn||0, cls:'warn'},
      {label:'Error', count:s.error||0, cls:'error'},
      {label:'Stalled', count:s.stalled||0, cls:'stalled'},
    ]
    healthItems.forEach(function(hi){
      var c = hi.cls === 'ok' ? 'var(--success)' : hi.cls === 'warn' ? 'var(--warning)' : hi.cls === 'error' ? 'var(--danger)' : 'var(--text-muted)'
      html += '<div class="sys-hpill"><span class="sys-hcount" style="color:' + c + '">' + hi.count + '</span><span class="sys-hlabel">' + hi.label + '</span></div>'
    })
    html += '</div><div class="sys-sub">' + (s.total || 0) + ' registered components</div></div>'

    // Section: Orchestrator
    var o = orch || {}
    if(o.state){
      var stateColor = o.state === 'running' ? 'var(--success)' : o.state === 'error' ? 'var(--danger)' : o.state === 'initializing' || o.state === 'starting' ? 'var(--warning)' : 'var(--text-muted)'
      var wd = o.watchdog || {}, jr = o.journal || {}
      html += '<div class="sys-section"><div class="sys-section-title">Orchestrator</div>'
      html += '<div class="sys-health-strip">'
      html += '<div class="sys-hpill"><span class="sys-hcount" style="color:' + stateColor + '">' + o.state + '</span><span class="sys-hlabel">state</span></div>'
      html += '<div class="sys-hpill"><span class="sys-hcount">' + (o.crash_count || 0) + '</span><span class="sys-hlabel">crashes</span></div>'
      html += '<div class="sys-hpill"><span class="sys-hcount">' + (o.recovery_count || 0) + '</span><span class="sys-hlabel">recoveries</span></div>'
      html += '<div class="sys-hpill"><span class="sys-hcount">' + (o.transitions || 0) + '</span><span class="sys-hlabel">transitions</span></div>'
      html += '<div class="sys-hpill"><span class="sys-hcount" style="color:' + (wd.running ? 'var(--success)' : 'var(--danger)') + '">' + (wd.running ? 'on' : 'off') + '</span><span class="sys-hlabel">watchdog</span></div>'
      html += '</div><div class="sys-sub">watchdog interval ' + (wd.interval !== undefined ? wd.interval + 's' : '—') + ' · journal ' + (jr.enabled ? (jr.path || 'on') : 'off') + ' (' + (jr.entries || 0) + ' events)</div>'
      html += '</div>'
    }

    // Orchestrator — restartable services
    var svcs = (o.services || []).filter(function(s){ return s.restart_policy !== 'never' })
    if(svcs.length){
      html += '<div class="sys-section"><div class="sys-section-title">Supervised Services <span style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;color:var(--text-muted)">— restart on failure</span></div><div class="sys-runtime-list">'
      svcs.forEach(function(s){
        var c = s.healthy ? 'var(--success)' : 'var(--danger)'
        html += '<div class="sys-rrow"><span class="sys-rkey">' + s.name + '</span>' +
          '<span class="sys-rval"><span class="sys-badge-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:' + c + ';margin-right:5px;vertical-align:middle"></span>' +
          s.state + ' · ' + s.restarts + '/' + s.max_restarts + ' restarts' + (s.last_error ? ' · <span style="color:var(--danger);font-family:var(--font-mono);font-size:10px">' + s.last_error + '</span>' : '') + '</span></div>'
      })
      html += '</div></div>'
    }

    // Components
    var compKeys = Object.entries(comps)
    if(compKeys.length){
      html += '<div class="sys-section"><div class="sys-section-title">Components</div><div class="sys-badge-row">'
      compKeys.forEach(function(kv){
        var name = kv[0], comp = kv[1]
        var c = 'var(--text-muted)'
        if(comp.status === 'ok') c = 'var(--success)'
        else if(comp.status === 'warn') c = 'var(--warning)'
        else if(comp.status === 'error') c = 'var(--danger)'
        html += '<span class="sys-badge" style="border-color:' + c + '30;color:' + c + '"><span class="sys-badge-dot" style="background:' + c + '"></span>' + name + '</span>'
      })
      html += '</div></div>'
    }

    // Section: Plugins with load/unload
    var pcount = Object.keys(pdata).length
    html += '<div class="sys-section"><div class="sys-section-title">Plugins</div>'
    if(pcount){
      html += '<div class="sys-badge-row" id="sys-plugin-list">'
      Object.entries(pdata).forEach(function(kv){
        var m = kv[0], plg = kv[1]
        var loaded = plg.initialized
        html += '<span class="sys-plugin-card" data-plugin="' + m + '" data-loaded="' + loaded + '" style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:6px;font-size:11px;margin:2px;background:rgba(18,21,28,0.6);border:1px solid ' + (loaded ? 'rgba(61,220,151,0.2)' : 'rgba(255,200,87,0.2)') + ';color:' + (loaded ? 'var(--success)' : 'var(--warning)') + '">' +
          '<span class="sys-badge-dot" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:' + (loaded ? 'var(--success)' : 'var(--warning)') + ';margin-right:4px;vertical-align:middle"></span>' +
          (plg.name || m) +
          '<button class="sys-plugin-toggle" style="padding:2px 6px;border:none;border-radius:4px;font-size:10px;cursor:pointer;background:rgba(255,255,255,0.1);color:inherit">' + (loaded ? 'Unload' : 'Load') + '</button>' +
        '</span>'
      })
      html += '</div>'
    } else {
      html += '<div class="sys-empty">No plugins loaded</div>'
    }
    html += '</div>'

    // Hooks
    var hcount = Object.keys(hooks).length
    if(hcount){
      html += '<div class="sys-section"><div class="sys-section-title">Hooks</div><div class="sys-badge-row">'
      Object.entries(hooks).forEach(function(kv){
        html += '<span class="sys-badge">' + kv[0] + ' (' + kv[1].length + ')</span>'
      })
      html += '</div></div>'
    }

    // Runtime
    var rkeys = Object.entries(rt)
    if(rkeys.length){
      html += '<div class="sys-section"><div class="sys-section-title">Runtime</div><div class="sys-runtime-list">'
      rkeys.forEach(function(kv){
        var k = kv[0], v = kv[1]
        var val = typeof v === 'boolean' ? (v ? 'Yes' : 'No') : (v !== null && v !== undefined ? v : '—')
        if(typeof v === 'number' && v.toFixed) val = v.toFixed(2)
        html += '<div class="sys-rrow"><span class="sys-rkey">' + k.replace(/_/g, ' ') + '</span><span class="sys-rval">' + val + '</span></div>'
      })
      html += '</div></div>'
    }

    // Section: Configuration
    var cfgKeys = Object.entries(config)
    if(cfgKeys.length){
      html += '<div class="sys-section"><div class="sys-section-title">Configuration <span style="font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;color:var(--text-muted)">— click to edit safe settings</span></div><div class="sys-runtime-list" id="sys-config-list">'
      cfgKeys.forEach(function(kv){
        var k = kv[0], v = kv[1]
        if(!v || typeof v !== 'object') return
        var val = v.value !== undefined ? v.value : v.default
        var meta = v.meta || {}
        var cat = meta.category || 'other'
        var label = meta.label || k
        var type = meta.type || 'text'
        html += '<div class="sys-config-row" data-key="' + k + '" data-type="' + type + '" data-meta=\'' + JSON.stringify(meta).replace(/'/g, '&#39;') + '\'>' +
          '<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.03)">' +
            '<span class="sys-rkey" style="cursor:pointer" title="' + k + '">' + label + '</span>' +
            '<span class="sys-config-val" style="color:var(--accent);font-family:var(--font-mono);font-size:11px;cursor:pointer">' + val + '</span>' +
          '</div>' +
        '</div>'
      })
      html += '</div><div style="margin-top:8px;font-size:11px;color:var(--text-muted);text-align:center">Click a value to edit · changes persist across restarts</div></div>'
    }

    // About
    html += '<div class="sys-section"><div class="sys-section-title">About</div><div class="sys-runtime-list">'
    html += '<div class="sys-rrow"><span class="sys-rkey">Name</span><span class="sys-rval">' + (ab.name || 'Mai') + '</span></div>'
    html += '<div class="sys-rrow"><span class="sys-rkey">Personality</span><span class="sys-rval">' + (ab.personality || '—') + '</span></div>'
    html += '<div class="sys-rrow"><span class="sys-rkey">Version</span><span class="sys-rval">2.0.0</span></div>'
    html += '</div></div>'

    el.innerHTML = html

    // Wire plugin toggles
    el.querySelectorAll('.sys-plugin-toggle').forEach(function(btn){
      btn.addEventListener('click', function(e){
        e.stopPropagation()
        var card = this.closest('.sys-plugin-card')
        var name = card.dataset.plugin
        var loaded = card.dataset.loaded === 'true'
        var endpoint = loaded ? ('/api/system/plugins/' + name + '/unload') : ('/api/system/plugins/' + name + '/load')
        fetch(endpoint, {method:'POST'}).then(function(r){ return r.json() }).then(function(){
          setTimeout(function(){ _init() }, 300)
        }).catch(function(){})
      })
    })

    // Wire config value clicks
    el.querySelectorAll('.sys-config-val').forEach(function(el){
      el.addEventListener('click', function(){
        var row = this.closest('.sys-config-row')
        var key = row.dataset.key
        var type = row.dataset.type
        var current = this.textContent

        if(type === 'bool'){
          var newVal = current === 'true' ? false : true
          updateConfig(key, newVal, this)
          return
        }
        if(type === 'select'){
          var meta = JSON.parse(row.dataset.meta || '{}')
          var options = meta.options || []
          var input = document.createElement('select')
          input.className = 'sys-config-edit'
          input.style.cssText = 'background:rgba(0,0,0,0.4);border:1px solid var(--glass-border);border-radius:6px;color:var(--accent);font-family:var(--font-mono);font-size:11px;padding:2px 6px;outline:none'
          options.forEach(function(o){
            var opt = document.createElement('option')
            opt.value = o
            opt.textContent = o
            if(o === current) opt.selected = true
            input.appendChild(opt)
          })
          this.replaceWith(input)
          input.focus()
          input.addEventListener('change', function(){ updateConfig(key, input.value, input) })
          input.addEventListener('blur', function(){})
          return
        }

        var input = document.createElement('input')
        input.type = type === 'float' ? 'number' : (type === 'int' ? 'number' : 'text')
        input.className = 'sys-config-edit'
        input.value = current
        if(meta.step) input.step = meta.step
        if(meta.min !== undefined) input.min = meta.min
        if(meta.max !== undefined) input.max = meta.max
        input.style.cssText = 'background:rgba(0,0,0,0.4);border:1px solid var(--glass-border);border-radius:6px;color:var(--accent);font-family:var(--font-mono);font-size:11px;padding:2px 6px;width:120px;outline:none'
        this.replaceWith(input)
        input.focus()
        input.select()

        function save(){
          var v = input.value
          if(type === 'int') v = parseInt(v, 10)
          else if(type === 'float') v = parseFloat(v)
          updateConfig(key, v, input)
        }

        input.addEventListener('blur', save)
        input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); input.blur() } })
      })
    })

    function updateConfig(key, value, el){
      var body = {}
      body[key] = value
      fetch('/api/config/update', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
        .then(function(r){ return r.json() })
        .then(function(){
          var parent = el.closest ? el.closest('.sys-config-row') : null
          if(parent){
            var valSpan = parent.querySelector('.sys-config-val')
            if(valSpan){
              valSpan.textContent = value
              el.replaceWith ? el.replaceWith(valSpan) : null
            }
          }
        })
        .catch(function(){})
    }

  } catch(e){
    el.innerHTML = '<div class="no-data"><span>Error: ' + e.message + '</span></div>'
  }
  _intervals.push(setInterval(function(){ _init() }, 15000))
}

function _destroy(){
  _intervals.forEach(function(iv){ clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'System', subtitle: 'Health, plugins & configuration', icon: '⚙', init: _init, destroy: _destroy })
})()
