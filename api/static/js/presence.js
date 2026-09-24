(function(){'use strict'

const STATE = {
  emotion: 'neutral',
  topic: '',
  goal: '',
  confidence: 0,
  workingMemory: [],
  recentThoughts: [],
  speaker: '',
  stories: [],
  storyIdx: 0,
  personalities: {},
  timeOfDay: 'night',
  hierarchy: { working: 0, short: 0, long: 0, archive: 0 },
  moduleActivity: {},
  graphNodes: [],
  graphEdges: [],
  cityPulseNodes: [],
}

const EMOJI_MAP = {
  happy: '😊', sad: '😔', angry: '😤', anxious: '😰',
  neutral: '😌', warm: '🥰', surprised: '😮', tired: '😴',
}

const PERSONALITIES = [
  { id: 'consciousness', label: 'Mind', icon: '🧠', page: '/desktop#space=consciousness', color: '#9D7BFF' },
  { id: 'chat', label: 'Voice', icon: '💬', page: '/desktop#space=chat', color: '#4FA7FF' },
  { id: 'memory', label: 'Memory', icon: '🧠', page: '/desktop#space=memory', color: '#67E8F9' },
  { id: 'dream', label: 'Dreams', icon: '💭', page: '/desktop#space=agency', color: '#5E81F4' },
  { id: 'graph', label: 'Graph', icon: '🕸', page: '/desktop#space=graph', color: '#49D17D' },
  { id: 'reasoning', label: 'Reason', icon: '⚡', page: '/desktop#space=reasoning', color: '#F5B642' },
  { id: 'agency', label: 'Agency', icon: '🎯', page: '/desktop#space=agency', color: '#FF8A65' },
  { id: 'emotion', label: 'Emotion', icon: '💖', page: '/desktop#space=consciousness', color: '#FF5D73' },
]

const MODULE_EVENT_MAP = {
  'state.emotion.changed': 'consciousness',
  'state.dreaming.started': 'dream',
  'state.dreaming.finished': 'dream',
  'state.goal.updated': 'consciousness',
  'state.voice.listening': 'chat',
  'state.voice.speaking': 'chat',
  'state.voice.idle': 'chat',
  'state.voice.wake': 'chat',
  'state.memory.updated': 'memory',
  'state.knowledge.updated': 'graph',
  'state.reasoning.busy': 'reasoning',
  'state.reasoning.complete': 'reasoning',
  'state.reasoning.reflection': 'reasoning',
  'state.belief.updated': 'reasoning',
  'state.agent.completed': 'agency',
}

const TL_TYPES = {
  'state.emotion.changed': 'emotion',
  'state.dreaming.started': 'dream',
  'state.dreaming.finished': 'dream',
  'state.goal.updated': 'goal',
  'state.voice.listening': 'voice',
  'state.voice.speaking': 'voice',
  'state.voice.idle': 'voice',
  'state.voice.wake': 'voice',
  'state.reasoning.busy': 'thought',
  'state.reasoning.complete': 'thought',
  'state.reasoning.reflection': 'thought',
  'state.belief.updated': 'thought',
  'state.memory.updated': 'memory',
  'state.knowledge.updated': 'system',
  'state.agent.completed': 'system',
}

let _realThoughtsCache = [] // fallback pool from backend
let _lastRealThought = ''

let idleTimer = null
const IDLE_TIMEOUT_MS = 120000
let timeline = []
let sse = null
let storyRotationTimer = null
const MOMENTS_KEY = 'mai_presence_moments'
let thoughtBubbleTimer = null

const MODULE_ACTIVITY = {}
PERSONALITIES.forEach(p => { MODULE_ACTIVITY[p.id] = 0 })

function timeAgo(ts) {
  const sec = Math.floor((Date.now() - ts) / 1000)
  if (sec < 60) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return min + 'm ago'
  const hr = Math.floor(min / 60)
  return hr + 'h ago'
}

function getEl(id) { return document.getElementById(id) }

function setText(id, text) {
  const el = getEl(id)
  if (el) el.textContent = text
}

function formatEmotion(emotionName) {
  return (emotionName || '').toLowerCase().trim() || 'neutral'
}

// ── Ambient Intelligence ─────────────────────────────────────────

function updateTimeOfDay() {
  const h = new Date().getHours()
  let tod
  if (h >= 6 && h < 12) tod = 'morning'
  else if (h >= 12 && h < 18) tod = 'afternoon'
  else if (h >= 18 && h < 21) tod = 'evening'
  else tod = 'night'
  document.body.classList.remove('time-morning', 'time-afternoon', 'time-evening', 'time-night')
  document.body.classList.add('time-' + tod)
  STATE.timeOfDay = tod
}

function getTimeGreeting() {
  const h = new Date().getHours()
  if (h < 6) return 'Still awake?'
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  if (h < 21) return 'Good evening'
  return 'Good night'
}

// ── Thought Bubble ───────────────────────────────────────────────

function updateBubbleThought(text) {
  const el = getEl('bubble-thought')
  if (!el) return
  const displayText = text || _lastRealThought || 'Waiting for a thought...'
  _lastRealThought = displayText
  el.style.opacity = '0'
  setTimeout(function(){
    el.textContent = displayText
    el.style.opacity = '1'
  }, 300)
}

async function refreshThoughtFromBackend() {
  try {
    const res = await fetch('/api/consciousness')
    if (!res.ok) return
    const data = await res.json()
    const cog = data.cognitive || {}
    const thoughts = cog.recent_thoughts || []
    if (thoughts.length > 0) {
      const t = typeof thoughts[0] === 'string' ? thoughts[0] : (thoughts[0].content || thoughts[0].text || '')
      if (t) {
        updateBubbleThought(t)
        return
      }
    }
    // Fallback: use reflections if available
    const reflect = data.reflections || []
    if (reflect.length > 0) {
      const t = reflect[0].summary || reflect[0].content || ''
      if (t) { updateBubbleThought(t); return }
    }
    // Use cached real thoughts as fallback pool
    if (_realThoughtsCache.length > 0) {
      const idx = Math.floor(Math.random() * _realThoughtsCache.length)
      updateBubbleThought(_realThoughtsCache[idx])
    }
  } catch(e){}
}

// ── Radial Gauge ─────────────────────────────────────────────────

function updateRadialGauge(pct) {
  const fill = getEl('gauge-fill')
  const text = getEl('gauge-pct')
  if (!fill) return
  const r = 50
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)
  fill.style.strokeDasharray = circ
  fill.style.strokeDashoffset = offset
  if (text) text.textContent = Math.round(pct * 100) + '%'

  // Color based on value
  const color = pct > 0.7 ? 'var(--success)' : pct > 0.35 ? 'var(--accent)' : 'var(--warning)'
  fill.style.stroke = color
}

// ── Update Hero ──────────────────────────────────────────────────

function updateHero(data) {
  if (!data) return
  const emotion = data.emotion || {}
  const cog = data.cognitive || {}

  const emoName = formatEmotion(emotion.dominant_emotion || emotion.emotion || emotion.name || STATE.emotion)
  STATE.emotion = emoName
  const emoji = EMOJI_MAP[emoName] || '😌'

  const greetEl = getEl('hero-greeting')
  if (greetEl) greetEl.textContent = getTimeGreeting()

  // Status badges
  const row = getEl('hero-status-row')
  if (row) {
    row.innerHTML =
      '<span class="hero-status-badge emotion" data-status="' + emoName + '">' + emoji + ' <span>' + emoName.charAt(0).toUpperCase() + emoName.slice(1) + '</span></span>' +
      '<span class="hero-status-badge thinking">🧠 <span>Thinking</span></span>' +
      '<span class="hero-status-badge listening">👂 <span>Listening</span></span>'
  }

  const topic = cog.current_topic || STATE.topic
  STATE.topic = topic
  const goal = cog.current_goal || STATE.goal
  STATE.goal = goal
  const conf = cog.confidence !== undefined ? cog.confidence : STATE.confidence
  STATE.confidence = conf

  // Goal sub
  setText('goal-sub', goal || 'Building semantic relationships')

  // Focus bar
  const focusPct = Math.round(conf * 100)
  const focusBar = getEl('focus-bar')
  if (focusBar) focusBar.style.width = focusPct + '%'
  setText('focus-pct', focusPct + '%')

  // Radial gauge
  updateRadialGauge(conf)

  // Attention bar
  const attn = getEl('gauge-attention')
  if (attn) {
    const filled = Math.round(conf * 8)
    attn.textContent = '█'.repeat(filled) + '░'.repeat(8 - filled)
  }

  // Working memory
  const wm = cog.working_memory || STATE.workingMemory
  STATE.workingMemory = wm
  setText('wm-count', wm.length + ' active thoughts')
  const wmEl = getEl('wm-chunks')
  if (wmEl && wm.length > 0) {
    wmEl.innerHTML = wm.slice(-6).map(function(m){
      const text = typeof m === 'string' ? m : (m.content || m.text || '')
      return '<span class="wm-chunk">' + text + '</span>'
    }).join('')
  }

  // Current thought
  const thoughts = cog.recent_thoughts || STATE.recentThoughts
  STATE.recentThoughts = thoughts
  const thoughtText = thoughts.length > 0
    ? (typeof thoughts[0] === 'string' ? thoughts[0] : (thoughts[0].content || thoughts[0].text || ''))
    : '—'
  setText('current-thought', thoughtText ? '"' + thoughtText + '"' : '—')

  // Cache real thoughts for bubble fallback
  if (Array.isArray(thoughts) && thoughts.length > 0) {
    _realThoughtsCache = thoughts.slice(0, 20).map(function(t){
      return typeof t === 'string' ? t : (t.content || t.text || '')
    }).filter(Boolean)
  }

  // Bubble thought rotates independently

  // Dock emotion
  setText('dock-emotion', emoji + ' ' + emoName.charAt(0).toUpperCase() + emoName.slice(1))
}

// ── Load Hierarchy ───────────────────────────────────────────────

async function loadHierarchy() {
  try {
    const res = await fetch('/api/memory/stats')
    if (!res.ok) return
    const data = await res.json()
    const total = data.vector_count || 0
    STATE.hierarchy = {
      working: data.working_memory || data.working || 0,
      short: data.short_term || data.short || 0,
      long: data.long_term || data.long || data.semantic || 0,
      archive: data.archive || data.autobiographical || 0,
    }

    const max = Math.max(STATE.hierarchy.working, STATE.hierarchy.short, STATE.hierarchy.long, STATE.hierarchy.archive, 1)
    ;['working','short','long','archive'].forEach(function(key){
      const val = STATE.hierarchy[key] || 0
      const pct = Math.round((val / max) * 100)
      const bar = document.querySelector('.mem-bar-fill.' + key)
      if (bar) bar.style.width = pct + '%'
      setText('mem-' + key, val)
    })
  } catch(e){}
}

// ── Load Stories ─────────────────────────────────────────────────

async function loadStories() {
  try {
    const res = await fetch('/api/reasoning/reflect/history')
    if (!res.ok) return
    const data = await res.json()
    const reflections = Array.isArray(data) ? data : (data.reflections || data.history || [])
    if (reflections.length > 0 && JSON.stringify(reflections) !== JSON.stringify(STATE.stories)) {
      STATE.stories = reflections
      STATE.storyIdx = 0
      showStory(0)
    }
  } catch(e){}
}

function showStory(index) {
  const el = getEl('reflection-body')
  const timeEl = getEl('reflection-time')
  const confEl = getEl('reflection-confidence')
  if (!el) return
  const stories = STATE.stories
  if (!stories || stories.length === 0) {
    el.textContent = '"Waiting for reflections..."'
    if (timeEl) timeEl.textContent = ''
    if (confEl) confEl.textContent = ''
    return
  }
  const idx = ((index % stories.length) + stories.length) % stories.length
  STATE.storyIdx = idx
  const s = stories[idx]
  const summary = s.summary || s.content || s.text || ''
  const time = s.timestamp || s.created_at || s.time || ''
  const sConf = s.confidence !== undefined ? s.confidence : null

  el.textContent = '"' + summary.slice(0, 200) + (summary.length > 200 ? '...' : '') + '"'
  if (timeEl) timeEl.textContent = typeof time === 'string' ? time : new Date(time).toLocaleString()
  if (confEl) confEl.textContent = sConf !== null ? 'Confidence ' + Math.round(sConf * 100) + '%' : ''
}

function nextStory() {
  if (STATE.stories.length > 0) showStory(STATE.storyIdx + 1)
}

// ── Load Personalities / Subsystems ──────────────────────────────

async function loadPersonalities() {
  const grid = getEl('subsystem-grid')
  if (!grid) return
  grid.innerHTML = '<div class="moments-empty" style="padding:8px">Loading subsystems...</div>'
  try {
    const [healthRes, statusRes] = await Promise.all([
      fetch('/api/system/health').then(function(r){ return r.json() }).catch(function(){ return {} }),
      fetch('/api/status').then(function(r){ return r.json() }).catch(function(){ return {} }),
    ])
    const dreamActive = statusRes.dream && statusRes.dream.is_dreaming
    STATE.personalities = {
      consciousness: { status: 'active', detail: 'Online', load: 82 },
      chat: { status: 'active', detail: 'Listening', load: 45 },
      memory: { status: healthRes.memory ? 'active' : 'idle', detail: healthRes.memory ? healthRes.memory + ' mem' : '—', load: 67 },
      dream: { status: dreamActive ? 'busy' : 'idle', detail: dreamActive ? 'Dreaming' : 'Asleep', load: dreamActive ? 74 : 12 },
      graph: { status: 'active', detail: 'Synchronized', load: 38 },
      reasoning: { status: 'active', detail: 'Ready', load: 56 },
      agency: { status: 'active', detail: 'Standby', load: 23 },
      emotion: { status: 'active', detail: emojiName(STATE.emotion), load: 61 },
    }
  } catch(e){
    PERSONALITIES.forEach(function(p){ STATE.personalities[p.id] = { status: 'idle', detail: '—', load: 0 } })
  }

  grid.innerHTML = PERSONALITIES.map(function(p){
    const ps = STATE.personalities[p.id] || { status: 'idle', detail: '—', load: 0 }
    const activity = MODULE_ACTIVITY[p.id] || 0
    return '<a class="subsystem-card" data-module="' + p.id + '" href="' + p.page + '">' +
      '<div class="subsys-icon" style="background:' + p.color + '22;color:' + p.color + '">' + p.icon + '</div>' +
      '<div class="subsys-info">' +
        '<span class="subsys-name">' + p.label + '</span>' +
        '<span class="subsys-status ' + ps.status + '">' + ps.detail + '</span>' +
      '</div>' +
      '<div class="subsys-meta">' +
        '<span class="subsys-load-label">Load</span>' +
        '<span class="subsys-load-val">' + ps.load + '%</span>' +
      '</div>' +
      '<span class="p-status-dot ' + ps.status + '"></span>' +
    '</a>'
  }).join('')

  // Dock stats
  const memStats = STATE.personalities.memory || {}
  setText('dock-memory', '🧠 ' + (memStats.detail ? memStats.detail.split(' ')[0] : '0'))
}

function emojiName(em) {
  return EMOJI_MAP[em] || '😌'
}

function pulseModule(moduleId) {
  MODULE_ACTIVITY[moduleId] = (MODULE_ACTIVITY[moduleId] || 0) + 1
  const card = document.querySelector('.subsystem-card[data-module="' + moduleId + '"]')
  if (card) {
    card.classList.remove('pulse')
    void card.offsetWidth
    card.classList.add('pulse')
  }

  // Pulse city district
  const district = document.querySelector('.city-district[data-district="' + moduleId + '"] .district-dot')
  if (district) {
    district.classList.remove('pulse')
    void district.offsetWidth
    district.classList.add('pulse')
  }
}

// ── Timeline ─────────────────────────────────────────────────────

function formatEventTitle(topic, data) {
  const d = data || {}
  const label = topic.split('.').pop().replace(/_/g, ' ')
  switch (topic) {
    case 'state.emotion.changed': return 'Mood shifted to ' + (d.dominant || label)
    case 'state.dreaming.finished': return 'Dream complete — ' + (d.level || '') + (d.tasks ? ' (' + d.tasks.length + ' tasks)' : '')
    case 'state.dreaming.started': return 'Dream started — ' + (d.level || '')
    case 'state.goal.updated': return 'Goal ' + (d.status || 'updated') + ': ' + (d.description || d.id || label)
    case 'state.voice.listening': return 'Listening...'
    case 'state.voice.speaking': return 'Speaking: "' + (d.text || '').slice(0, 60) + (d.text && d.text.length > 60 ? '...' : '') + '"'
    case 'state.voice.idle': return 'Voice idle'
    case 'state.voice.wake': return 'Wake word: ' + (d.wake_word || 'detected')
    case 'state.reasoning.busy': return 'Reasoning...'
    case 'state.reasoning.complete': return 'Response ready'
    case 'state.reasoning.reflection': loadStories(); return 'New reflection'
    case 'state.belief.updated': return 'Belief updated'
    case 'state.memory.updated': loadHierarchy(); return 'Memory updated'
    case 'state.knowledge.updated': loadPersonalities(); return 'Knowledge graph updated'
    case 'state.agent.completed': loadPersonalities(); return 'Agent task complete'
    default: return topic
  }
}

function addTimelineEvent(event) {
  const topic = event.topic, data = event.data || {}
  timeline.push({ type: TL_TYPES[topic] || 'system', title: formatEventTitle(topic, data), time: Date.now(), topic: topic, data: data })
  if (timeline.length > 100) timeline = timeline.slice(-100)
  renderTimeline()
}

function renderTimeline() {
  const list = getEl('timeline-list')
  if (!list) return
  if (timeline.length === 0) {
    list.innerHTML = '<div class="timeline-empty">Waiting for activity...</div>'
    setText('timeline-count', '0 events')
    return
  }
  list.innerHTML = timeline.slice(-20).reverse().map(function(ev){
    return '<div class="timeline-event">' +
      '<div class="tl-dot ' + ev.type + '"></div>' +
      '<div class="tl-content"><div class="tl-title">' + ev.title + '</div><div class="tl-time">' + timeAgo(ev.time) + '</div></div>' +
    '</div>'
  }).join('')
  setText('timeline-count', timeline.length + ' events')
}

// ── Moments ──────────────────────────────────────────────────────

function getMoments() {
  try { return JSON.parse(localStorage.getItem(MOMENTS_KEY) || '[]') } catch(e){ return [] }
}

function saveMoments(moments) {
  try { localStorage.setItem(MOMENTS_KEY, JSON.stringify(moments)) } catch(e){}
}

function captureMoment() {
  const moments = getMoments()
  moments.unshift({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 5),
    emotion: STATE.emotion,
    topic: STATE.topic,
    goal: STATE.goal,
    confidence: STATE.confidence,
    thought: STATE.recentThoughts[0] || '',
    time: Date.now(),
    timeOfDay: STATE.timeOfDay,
  })
  if (moments.length > 20) moments.length = 20
  saveMoments(moments)
  renderMoments()
}

function renderMoments() {
  const list = getEl('moments-list')
  if (!list) return
  const moments = getMoments()
  setText('moments-count', moments.length)
  if (moments.length === 0) {
    list.innerHTML = '<div class="moments-empty">Moments appear here when captured</div>'
    return
  }
  list.innerHTML = moments.slice(0, 10).map(function(m){
    const emoji = EMOJI_MAP[m.emotion] || '😌'
    return '<div class="moment-row">' +
      '<span class="moment-icon">' + emoji + '</span>' +
      '<span class="moment-desc">' + (m.topic || 'Memory captured') + '</span>' +
      '<span class="moment-time">' + timeAgo(m.time) + '</span>' +
    '</div>'
  }).join('')
}

// ── City Districts ───────────────────────────────────────────────

function pulseCityDistrict(districtId) {
  const dot = document.querySelector('.city-district[data-district="' + districtId + '"] .district-dot')
  if (dot) {
    dot.classList.remove('pulse')
    void dot.offsetWidth
    dot.classList.add('pulse')
  }
}

// ── SSE Connection ───────────────────────────────────────────────

function connectSSE() {
  if (sse) sse.close()
  sse = new EventSource('/api/stream')
  sse.onmessage = function(e) {
    try {
      const msg = JSON.parse(e.data)
      addTimelineEvent(msg)
      const moduleId = MODULE_EVENT_MAP[msg.topic]
      if (moduleId) {
        pulseModule(moduleId)
        pulseCityDistrict(moduleId)
      }
      if (msg.topic === 'state.emotion.changed') { refreshState(); refreshThoughtFromBackend() }
      if (msg.topic === 'state.reasoning.complete') { refreshState(); refreshThoughtFromBackend() }
      if (msg.topic === 'state.dreaming.finished' || msg.topic === 'state.dreaming.started') loadPersonalities()
      if (msg.topic === 'state.memory.updated') { loadPersonalities(); loadHierarchy() }
      if (msg.topic === 'state.reasoning.reflection') { loadStories(); refreshThoughtFromBackend() }
      if (msg.topic === 'state.knowledge.updated') { loadPersonalities() }
    } catch(err){}
  }
  sse.onerror = function(){}
}

// ── Idle Detection ──────────────────────────────────────────────

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer)
  document.body.classList.remove('idle')
  idleTimer = setTimeout(enterIdle, IDLE_TIMEOUT_MS)
}

function enterIdle() {
  document.body.classList.add('idle')
}

// ── Refresh State ────────────────────────────────────────────────

async function refreshState() {
  try {
    const res = await fetch('/api/consciousness')
    if (res.ok) {
      const data = await res.json()
      updateHero(data)
    }
  } catch(e){}
}

// ── Dock Clock ───────────────────────────────────────────────────

function dockTick() {
  const now = new Date()
  const el = getEl('dock-time')
  if (el) el.textContent = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0')
}

// ── Init ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function(){
  updateTimeOfDay()
  setInterval(updateTimeOfDay, 60000)

  refreshState()
  loadStories()
  loadHierarchy()
  loadPersonalities()
  renderMoments()
  connectSSE()
  dockTick()

  // Thought bubble — fetch real thought from backend
  refreshThoughtFromBackend()
  thoughtBubbleTimer = setInterval(refreshThoughtFromBackend, 12000)

  // Polling: SSE handles live updates; keep only fallback intervals
  // (SSE events trigger refreshState, loadPersonalities, loadHierarchy)
  setInterval(refreshState, 60000)      // fallback: 60s
  setInterval(loadPersonalities, 120000) // fallback: 2min
  setInterval(loadHierarchy, 120000)     // fallback: 2min
  storyRotationTimer = setInterval(nextStory, 30000)
  setInterval(dockTick, 1000)

  const idleEvents = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel']
  idleEvents.forEach(function(ev){ document.addEventListener(ev, resetIdleTimer, { passive: true }) })
  resetIdleTimer()

  const captureBtn = getEl('capture-btn')
  if (captureBtn) captureBtn.addEventListener('click', captureMoment)

  // Radial gauge init
  updateRadialGauge(STATE.confidence)
})
})()
