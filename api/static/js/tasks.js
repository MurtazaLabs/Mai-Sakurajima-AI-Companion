// Space — Tasks (goals, subtasks, procedural memory)
(function(){'use strict'
var _intervals = []
var _id = 'tasks'

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  el.innerHTML = '<div class="no-data"><span>Loading...</span></div>'
  try{
    var [goalsRes, procRes] = await Promise.all([
      fetch('/api/tasks').then(function(r){ return r.json() }),
      fetch('/api/tasks/procedural').then(function(r){ return r.json() }),
    ])
    var data = goalsRes || {}, proc = procRes || {}
    var goals = data.goals || [], active = data.active || [], stats = data.stats || {}
    var rules = proc.rules || [], pstats = proc.stats || {}
    var html = ''

    // Stats bar
    html += '<div class="sys-section"><div class="sys-section-title">Overview</div><div class="sys-health-strip">'
    var sItems = [
      {label:'Active', count:stats.active||0, cls:'ok'},
      {label:'Completed', count:stats.completed||0, cls:'ok'},
      {label:'Pending', count:stats.pending||0, cls:'warn'},
      {label:'Avg Progress', count:((stats.avg_progress||0)*100).toFixed(0)+'%', cls:'ok'},
    ]
    sItems.forEach(function(si){
      var c = si.cls === 'ok' ? 'var(--success)' : 'var(--warning)'
      html += '<div class="sys-hpill"><span class="sys-hcount" style="color:' + c + '">' + si.count + '</span><span class="sys-hlabel">' + si.label + '</span></div>'
    })
    html += '</div></div>'

    // Create goal button
    html += '<div class="sys-section"><div class="sys-section-title">Goals</div>'
    html += '<div style="margin-bottom:12px"><button id="tasks-create-btn" class="sys-plugin-toggle" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;cursor:pointer;background:rgba(61,220,151,0.15);color:var(--success)">+ New Goal</button></div>'

    if(goals.length){
      goals.forEach(function(g){
        var pct = Math.round((g.progress||0)*100)
        var statusColor = g.status === 'completed' ? 'var(--success)' : g.status === 'active' ? 'var(--accent)' : g.status === 'cancelled' ? 'var(--danger)' : 'var(--text-muted)'
        var priColor = g.priority === 'high' ? 'var(--danger)' : g.priority === 'low' ? 'var(--text-muted)' : 'var(--warning)'
        html += '<div class="sys-config-row" style="margin-bottom:8px;padding:10px 12px;background:rgba(18,21,28,0.6);border-radius:8px;border:1px solid rgba(255,255,255,0.04)">'
        html += '<div style="display:flex;justify-content:space-between;align-items:center">'
        html += '<div><strong style="color:' + statusColor + '">' + g.description + '</strong>'
        html += ' <span style="font-size:10px;color:' + priColor + ';margin-left:8px">' + g.priority + '</span>'
        html += ' <span style="font-size:10px;color:var(--text-muted)">[' + g.status + ']</span></div>'
        html += '<div style="display:flex;gap:4px;align-items:center">'
        html += '<span style="font-size:11px;color:var(--text-muted);min-width:36px;text-align:right">' + pct + '%</span>'
        if(g.status === 'active' || g.status === 'pending'){
          html += '<button class="task-act-btn" data-gid="' + g.id + '" data-action="complete" style="padding:2px 8px;border:none;border-radius:4px;font-size:10px;cursor:pointer;background:rgba(61,220,151,0.15);color:var(--success)" title="Complete">✓</button>'
          html += '<button class="task-act-btn" data-gid="' + g.id + '" data-action="cancel" style="padding:2px 8px;border:none;border-radius:4px;font-size:10px;cursor:pointer;background:rgba(255,87,87,0.15);color:var(--danger)" title="Cancel">✕</button>'
        }
        if(g.status === 'pending'){
          html += '<button class="task-act-btn" data-gid="' + g.id + '" data-action="activate" style="padding:2px 8px;border:none;border-radius:4px;font-size:10px;cursor:pointer;background:rgba(100,200,255,0.15);color:var(--accent)" title="Activate">▶</button>'
        }
        html += '</div></div>'

        // Subtasks
        if(g.subtasks && g.subtasks.length){
          html += '<div style="margin-top:8px;padding-left:16px;border-left:2px solid rgba(255,255,255,0.06)">'
          g.subtasks.forEach(function(st){
            var done = st.completed
            html += '<div style="display:flex;align-items:center;gap:6px;padding:2px 0;font-size:11px">'
            html += '<input type="checkbox" class="st-checkbox" data-gid="' + g.id + '" data-sid="' + st.id + '"' + (done?' checked':'') + (done?' disabled':'') + ' style="accent-color:var(--success);cursor:pointer">'
            html += '<span style="color:' + (done?'var(--success)':'var(--text)') + ';' + (done?'text-decoration:line-through':'') + '">' + (st.description||'') + '</span>'
            html += '</div>'
          })
          html += '</div>'
        }

        // Add subtask inline
        if(g.status === 'active'){
          html += '<div style="margin-top:6px;display:flex;gap:4px">'
          html += '<input class="st-input" data-gid="' + g.id + '" placeholder="Add subtask..." style="flex:1;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08);border-radius:4px;padding:3px 8px;font-size:11px;color:var(--text);outline:none">'
          html += '<button class="st-add-btn" data-gid="' + g.id + '" style="padding:2px 10px;border:none;border-radius:4px;font-size:10px;cursor:pointer;background:rgba(61,220,151,0.15);color:var(--success)">+</button>'
          html += '</div>'
        }

        html += '<div style="margin-top:4px;font-size:9px;color:var(--text-muted)">'
        if(g.turn_count !== undefined) html += 'turns: ' + g.turn_count
        html += '</div>'
        html += '</div>'
      })
    } else {
      html += '<div class="sys-empty">No goals yet. Create one to get started.</div>'
    }
    html += '</div>'

    // Procedural memory
    if(rules.length){
      html += '<div class="sys-section"><div class="sys-section-title">Procedural Memory <span style="font-weight:400;text-transform:none;font-size:11px;color:var(--text-muted)">(' + (pstats.total||0) + ' rules, avg confidence ' + ((pstats.avg_confidence||0)*100).toFixed(0) + '%)</span></div>'
      html += '<div class="sys-runtime-list">'
      rules.slice(0,20).forEach(function(r){
        var confPct = Math.round((r.confidence||0)*100)
        html += '<div class="sys-rrow"><span class="sys-rkey" title="' + (r.context||'') + '">' + r.rule + '</span><span class="sys-rval">' + confPct + '% · ' + (r.apply_count||0) + ' uses</span></div>'
      })
      if(rules.length > 20) html += '<div class="sys-rrow"><span class="sys-rkey" style="color:var(--text-muted)">+' + (rules.length-20) + ' more</span></div>'
      html += '</div></div>'
    }

    el.innerHTML = html

    // Wire goal actions
    el.querySelectorAll('.task-act-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        var gid = this.dataset.gid, action = this.dataset.action
        fetch('/api/tasks/' + gid + '/' + action, {method:'POST'}).then(function(){ _init() }).catch(function(){})
      })
    })

    // Wire subtask checkboxes
    el.querySelectorAll('.st-checkbox').forEach(function(cb){
      cb.addEventListener('change', function(){
        if(this.checked){
          var gid = this.dataset.gid, sid = this.dataset.sid
          fetch('/api/tasks/' + gid + '/subtasks/' + sid + '/complete', {method:'POST'}).then(function(){ _init() }).catch(function(){})
        }
      })
    })

    // Wire subtask add
    el.querySelectorAll('.st-add-btn').forEach(function(btn){
      btn.addEventListener('click', function(){
        var gid = this.dataset.gid
        var input = this.parentElement.querySelector('.st-input')
        if(!input || !input.value.trim()) return
        fetch('/api/tasks/' + gid + '/subtasks', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:input.value.trim()})})
          .then(function(){ _init() }).catch(function(){})
      })
    })
    el.querySelectorAll('.st-input').forEach(function(inp){
      inp.addEventListener('keydown', function(e){
        if(e.key === 'Enter'){
          var gid = this.dataset.gid
          if(!this.value.trim()) return
          fetch('/api/tasks/' + gid + '/subtasks', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:this.value.trim()})})
            .then(function(){ _init() }).catch(function(){})
        }
      })
    })

    // Wire create goal
    var createBtn = document.getElementById('tasks-create-btn')
    if(createBtn){
      createBtn.addEventListener('click', function(){
        var desc = prompt('New goal description:')
        if(!desc || !desc.trim()) return
        var prio = prompt('Priority (high/normal/low):', 'normal') || 'normal'
        if(!['high','normal','low'].includes(prio)) prio = 'normal'
        fetch('/api/tasks/create', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:desc.trim(), priority:prio})})
          .then(function(){ _init() }).catch(function(){})
      })
    }

  } catch(e){
    el.innerHTML = '<div class="no-data"><span>Error: ' + e.message + '</span></div>'
  }
  _intervals.push(setInterval(function(){ _init() }, 10000))
}

function _destroy(){
  _intervals.forEach(function(iv){ clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Tasks', subtitle: 'Goals, subtasks & procedural memory', icon: '✓', init: _init, destroy: _destroy })
})()
