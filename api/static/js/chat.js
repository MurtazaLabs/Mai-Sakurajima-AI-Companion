// Space — Chat (messages, voice, multi-session)
(function(){'use strict'
var _id = 'chat'
var _intervals = []
var _currentSession = null
var _sessions = []
var STORAGE_KEY = 'mai_chat_sessions'

function _escapeHtml(s){
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function _loadSessions(){
  try{
    var raw = localStorage.getItem(STORAGE_KEY)
    _sessions = raw ? JSON.parse(raw) : []
  }catch(e){ _sessions = [] }
  if(!_sessions.length){
    _sessions = [{id:'default', label:'Main', messages:[], created:Date.now()}]
    _saveSessions()
  }
}

function _saveSessions(){
  try{ localStorage.setItem(STORAGE_KEY, JSON.stringify(_sessions)) }catch(e){}
}

function _findSession(id){
  for(var i=0;i<_sessions.length;i++) if(_sessions[i].id === id) return _sessions[i]
  return null
}

function _switchSession(id){
  var s = _findSession(id)
  if(!s) return
  _currentSession = id
  _renderMessages(s.messages)
  _updateSessionUI()
}

function _renderMessages(msgs){
  var container = document.getElementById('chat-messages')
  if(!container) return
  if(!msgs || !msgs.length){
    container.innerHTML = '<div class="chat-empty"><span style="color:var(--text-muted)">No messages yet</span></div>'
    return
  }
  var html = ''
  msgs.forEach(function(m){
    var isUser = m.role === 'user'
    var avatarClass = isUser ? 'user-avatar' : 'mai-avatar'
    var avatarText = isUser ? 'You' : 'M'
    html += '<div class="chat-msg ' + (isUser ? 'user' : 'mai') + '">' +
      '<div class="chat-msg-avatar ' + avatarClass + '">' + avatarText + '</div>' +
      '<div class="chat-msg-content"><div class="chat-msg-bubble">' + _escapeHtml(m.content) + '</div></div></div>'
  })
  container.innerHTML = html
  container.scrollTop = container.scrollHeight
}

function _updateSessionUI(){
  // Update active state in session list
  var list = document.getElementById('chat-session-list')
  if(!list) return
  list.querySelectorAll('.chat-session-item').forEach(function(el){
    el.classList.toggle('active', el.dataset.id === _currentSession)
  })
}

function _newSession(){
  var id = 'sess_' + Date.now()
  _sessions.push({id:id, label:'Session ' + (_sessions.length + 1), messages:[], created:Date.now()})
  _saveSessions()
  _switchSession(id)
  _renderSessionList()
}

function _deleteSession(id){
  if(_sessions.length <= 1) return
  _sessions = _sessions.filter(function(s){ return s.id !== id })
  _saveSessions()
  if(_currentSession === id) _switchSession(_sessions[_sessions.length - 1].id)
  _renderSessionList()
}

function _renameSession(id, label){
  var s = _findSession(id)
  if(!s) return
  s.label = label
  _saveSessions()
  _renderSessionList()
}

function _renderSessionList(){
  var list = document.getElementById('chat-session-list')
  if(!list) return
  var html = ''
  _sessions.forEach(function(s){
    html += '<div class="chat-session-item' + (s.id === _currentSession ? ' active' : '') + '" data-id="' + _escapeHtml(s.id) + '">' +
      '<span class="chat-session-label">' + _escapeHtml(s.label) + '</span>' +
      '<div class="chat-session-actions">' +
        '<button class="chat-session-rename" title="Rename">✎</button>' +
        '<button class="chat-session-delete" title="Delete">✕</button>' +
      '</div></div>'
  })
  list.innerHTML = html

  // Wire events — click + keyboard
  list.querySelectorAll('.chat-session-item').forEach(function(el){
    el.setAttribute('role', 'button')
    el.setAttribute('tabindex', '0')
    el.addEventListener('click', function(e){
      if(e.target.closest('.chat-session-actions')) return
      _switchSession(el.dataset.id)
    })
    el.addEventListener('keydown', function(e){
      if(e.key === 'Enter' || e.key === ' '){
        e.preventDefault()
        if(e.target.closest('.chat-session-actions')) return
        _switchSession(el.dataset.id)
      }
    })
  })
  list.querySelectorAll('.chat-session-rename').forEach(function(btn){
    btn.addEventListener('click', function(e){
      e.stopPropagation()
      var el = this.closest('.chat-session-item')
      var id = el.dataset.id
      var s = _findSession(id)
      if(!s) return
      var label = prompt('Session name:', s.label)
      if(label && label.trim()) _renameSession(id, label.trim())
    })
    btn.addEventListener('keydown', function(e){
      if(e.key === 'Enter' || e.key === ' '){
        e.preventDefault(); e.stopPropagation(); this.click()
      }
    })
  })
  list.querySelectorAll('.chat-session-delete').forEach(function(btn){
    btn.addEventListener('click', function(e){
      e.stopPropagation()
      var el = this.closest('.chat-session-item')
      _deleteSession(el.dataset.id)
    })
    btn.addEventListener('keydown', function(e){
      if(e.key === 'Enter' || e.key === ' '){
        e.preventDefault(); e.stopPropagation(); this.click()
      }
    })
  })
}

async function _init(){
  var el = document.getElementById(_id + '-content')
  if(!el) return
  _loadSessions()
  if(!_currentSession) _currentSession = _sessions[_sessions.length - 1].id

  el.innerHTML = '<div class="chat-sessions-panel" id="chat-sessions-panel">' +
    '<div class="chat-sessions-header"><button class="chat-sessions-toggle" id="chat-sessions-toggle" title="Collapse">‹</button><span>Sessions</span><button id="chat-new-session" style="background:var(--accent);border:none;border-radius:4px;padding:2px 8px;font-size:11px;cursor:pointer;color:#fff">+ New</button></div>' +
    '<div class="chat-session-list" id="chat-session-list"></div>' +
  '</div>' +
  '<div class="chat-main">' +
    '<div class="chat-messages" id="chat-messages" role="log" aria-live="polite" aria-label="Chat messages" tabindex="-1"></div>' +
    '<div class="chat-input-row"><textarea class="chat-input" id="chat-input" placeholder="Message Mai..." rows="1" aria-label="Message input" style="font-size:16px"></textarea><button class="chat-send" id="chat-send" title="Send" aria-label="Send message">➤</button></div>' +
  '</div>'

  var s = _findSession(_currentSession)
  if(s) _renderMessages(s.messages)
  _renderSessionList()

  document.getElementById('chat-new-session').addEventListener('click', _newSession)
  document.getElementById('chat-new-session').addEventListener('keydown', function(e){
    if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); _newSession() }
  })

  // Session panel collapse toggle
  var panel = document.getElementById('chat-sessions-panel')
  var toggle = document.getElementById('chat-sessions-toggle')
  var collapsed = false
  toggle.setAttribute('tabindex', '0')
  toggle.setAttribute('role', 'button')
  toggle.setAttribute('aria-expanded', 'true')
  toggle.addEventListener('click', function(){
    collapsed = !collapsed
    panel.classList.toggle('collapsed', collapsed)
    toggle.textContent = collapsed ? '›' : '‹'
    toggle.title = collapsed ? 'Expand' : 'Collapse'
    toggle.setAttribute('aria-expanded', String(!collapsed))
  })
  toggle.addEventListener('keydown', function(e){
    if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); this.click() }
  })

  var input = document.getElementById('chat-input')
  var sendBtn = document.getElementById('chat-send')
  var msgContainer = document.getElementById('chat-messages')

  // Screen reader live region for announcements
  var liveRegion = document.getElementById('chat-live-region')
  if(!liveRegion){
    liveRegion = document.createElement('div')
    liveRegion.id = 'chat-live-region'
    liveRegion.setAttribute('role', 'status')
    liveRegion.setAttribute('aria-live', 'polite')
    liveRegion.setAttribute('aria-atomic', 'true')
    liveRegion.style.cssText = 'position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0'
    msgContainer.parentNode.insertBefore(liveRegion, msgContainer.nextSibling)
  }

  function sendMessage(){
    var text = input.value.trim()
    if(!text) return
    var sess = _findSession(_currentSession)
    if(!sess) return
    // Append user message
    sess.messages.push({role:'user', content:text, ts:Date.now()})
    _renderMessages(sess.messages)
    _saveSessions()
    input.value = ''
    input.style.height = 'auto'
    input.focus()
    liveRegion.textContent = 'Message sent. Awaiting reply.'
    msgContainer.setAttribute('tabindex', '-1')

    // Show typing
    msgContainer.innerHTML += '<div class="chat-msg mai"><div class="chat-msg-content"><div class="chat-msg-bubble" style="color:var(--text-muted)"><span id="chat-typing">Mai is thinking...</span></div></div></div>'
    msgContainer.scrollTop = msgContainer.scrollHeight

    fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text, session_id:_currentSession})})
      .then(function(r){ return r.json() })
      .then(function(data){
        var typing = document.getElementById('chat-typing')
        if(typing) typing.textContent = ''
        sess.messages.push({role:'assistant', content:data.response || '(no response)', ts:Date.now()})
        _renderMessages(sess.messages)
        _saveSessions()
        liveRegion.textContent = 'New message from Mai.'
        input.focus()
      })
      .catch(function(err){
        var typing = document.getElementById('chat-typing')
        if(typing) typing.textContent = 'Error: ' + err.message
      })
  }

  sendBtn.addEventListener('click', sendMessage)
  input.addEventListener('keydown', function(e){
    if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendMessage() }
  })

  // Auto-resize input
  input.addEventListener('input', function(){
    this.style.height = 'auto'
    this.style.height = Math.min(this.scrollHeight, 120) + 'px'
  })
}

function _destroy(){
  _intervals.forEach(function(iv){ clearInterval(iv) })
  _intervals.length = 0
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Chat', subtitle: 'Conversation with Mai', icon: '💬', init: _init, destroy: _destroy })
})()
