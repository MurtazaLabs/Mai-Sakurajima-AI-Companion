// Space — Permissions (security settings, whitelists, blocked commands)
(function(){'use strict'
var _intervals = []
var _id = 'permissions'

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML = '<div class="no-data"><span>Loading...</span></div>'
  try{
    var res = await fetch('/api/permissions').then(function(r){ return r.json() })
    var d = res || {}
    var html = ''

    // Permission mode card
    html += '<div class="sys-section"><div class="sys-section-title">Execution Mode</div>'
    html += '<div class="sys-health-strip">'
    var modeColors = {safe:'var(--success)', advanced:'var(--warning)', admin:'var(--danger)'}
    var mc = modeColors[d.mode] || 'var(--text-muted)'
    html += '<div class="sys-hpill"><span class="sys-hcount" style="color:' + mc + '">' + (d.mode||'unknown') + '</span><span class="sys-hlabel">current mode</span></div>'
    html += '<div class="sys-hpill"><span class="sys-hcount" style="color:var(--text-muted)">' + (d.cooldown||0) + 's</span><span class="sys-hlabel">cooldown</span></div>'
    html += '<div class="sys-hpill"><span class="sys-hcount" style="color:var(--text-muted)">' + ((d.min_confidence||0)*100) + '%</span><span class="sys-hlabel">min confidence</span></div>'
    html += '<div class="sys-hpill"><span class="sys-hcount" style="color:var(--text-muted)">' + (d.tool_count||0) + '</span><span class="sys-hlabel">tools</span></div>'
    html += '</div>'
    html += '<div style="display:flex;gap:8px;margin-top:10px">'
    var modes = ['safe','advanced','admin']
    modes.forEach(function(m){
      var active = m === d.mode
      var c = modeColors[m] || 'var(--text-muted)'
      html += '<button class="perm-mode-btn" data-mode="' + m + '" style="flex:1;padding:8px 12px;border:1px solid ' + (active ? c + '60' : 'rgba(255,255,255,0.08)') + ';border-radius:8px;background:' + (active ? c + '15' : 'rgba(18,21,28,0.6)') + ';color:' + (active ? c : 'var(--text-muted)') + ';cursor:pointer;font-size:12px;font-weight:' + (active ? '600' : '400') + ';text-transform:capitalize">' + m + '</button>'
    })
    html += '</div></div>'

    // Allowed action types
    if(d.allowed_action_types && d.allowed_action_types.length){
      html += '<div class="sys-section"><div class="sys-section-title">Allowed Action Types</div><div class="sys-badge-row">'
      d.allowed_action_types.forEach(function(t){
        html += '<span class="sys-badge" style="color:var(--success);border-color:rgba(61,220,151,0.2)">' + t + '</span>'
      })
      html += '</div></div>'
    }

    // App whitelist
    if(d.allowed_apps && d.allowed_apps.length){
      html += '<div class="sys-section"><div class="sys-section-title">App Whitelist <span style="font-weight:400;text-transform:none;font-size:11px;color:var(--text-muted)">(' + d.allowed_apps.length + ' apps)</span></div><div class="sys-badge-row">'
      d.allowed_apps.forEach(function(a){
        html += '<span class="sys-badge" style="color:var(--accent);border-color:rgba(100,200,255,0.15)">' + a + '</span>'
      })
      html += '</div></div>'
    }

    // Blocked commands
    if(d.blocked_commands && d.blocked_commands.length){
      html += '<div class="sys-section"><div class="sys-section-title">Blocked Commands <span style="font-weight:400;text-transform:none;font-size:11px;color:var(--text-muted)">(' + d.blocked_commands.length + ' patterns)</span></div><div class="sys-badge-row">'
      d.blocked_commands.forEach(function(c){
        html += '<span class="sys-badge" style="color:var(--danger);border-color:rgba(255,87,87,0.2)">' + c + '</span>'
      })
      html += '</div></div>'
    }

    // Destructive hotkeys
    if(d.destructive_hotkeys && d.destructive_hotkeys.length){
      html += '<div class="sys-section"><div class="sys-section-title">Blocked Hotkeys</div><div class="sys-badge-row">'
      d.destructive_hotkeys.forEach(function(k){
        html += '<span class="sys-badge" style="color:var(--warning);border-color:rgba(255,200,87,0.2)">' + k + '</span>'
      })
      html += '</div></div>'
    }

    // API security
    html += '<div class="sys-section"><div class="sys-section-title">API Security</div><div class="sys-runtime-list">'
    html += '<div class="sys-rrow"><span class="sys-rkey">Authentication</span><span class="sys-rval" style="color:' + (d.auth_required?'var(--success)':'var(--text-muted)') + '">' + (d.auth_required?'Required':'Disabled') + '</span></div>'
    html += '<div class="sys-rrow"><span class="sys-rkey">Rate Limit</span><span class="sys-rval">' + (d.rate_limit_per_minute||'unlimited') + ' req/min</span></div>'
    html += '</div></div>'

    el.innerHTML = html

    // Wire mode buttons
    el.querySelectorAll('.perm-mode-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        var mode = this.dataset.mode
        fetch('/api/permissions/mode', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode:mode})})
          .then(function(r){ return r.json() })
          .then(function(d){
            if(d.mode) setTimeout(function(){ _init() }, 300)
          })
          .catch(function(){})
      })
    })
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
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Permissions', subtitle: 'Security settings & whitelists', icon: '🔒', init: _init, destroy: _destroy })
})()
