// Space — Voice
(function(){'use strict'
var _intervals = []
var _id = 'voice'
var waveformCtx = null, _lastTranscript = '', _lastData = '', _waveCanvas = null

function roundRect(ctx, x, y, w, h, r){
  ctx.beginPath(); ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y); ctx.quadraticCurveTo(x+w, y, x+w, y+r)
  ctx.lineTo(x+w, y+h-r); ctx.quadraticCurveTo(x+w, y+h, x+w-r, y+h)
  ctx.lineTo(x+r, y+h); ctx.quadraticCurveTo(x, y+h, x, y+h-r)
  ctx.lineTo(x, y+r); ctx.quadraticCurveTo(x, y, x+r, y); ctx.closePath()
}

function createWaveform(ep){
  if(document.getElementById(_id + '-waveform-canvas')) return
  var w = document.createElement('div'); w.className = 'voice-waveform-wrap'; w.id = _id + '-waveform-wrap'
  w.innerHTML = '<canvas id="' + _id + '-waveform-canvas" height="80"></canvas><div class="voice-waveform-labels"><span>Live</span><span id="waveform-status">Idle</span></div>'
  ep.insertBefore(w, ep.firstChild)
  var c = document.getElementById(_id + '-waveform-canvas')
  if(!c) return
  waveformCtx = c.getContext('2d')
  _waveCanvas = c
  var r = c.parentElement.getBoundingClientRect(); c.width = r.width - 40
}

function drawWaveform(active){
  var c = document.getElementById(_id + '-waveform-canvas')
  if(!c || !waveformCtx) return
  var w = c.width, h = c.height, mx = w/2, my = h/2, t = Date.now()/1000
  waveformCtx.clearRect(0, 0, w, h)
  if(active){
    var bars = 64, barW = w / bars
    for(var i = 0; i < bars; i++){
      var amp = Math.max(2, (Math.sin(t*3 + i*0.5)*0.5 + 0.5)*25 + Math.random()*15)
      var x = i*barW + barW*0.1, x2 = (bars-1-i)*barW + barW*0.1
      waveformCtx.fillStyle = 'rgba(79,167,255,' + (0.3 + amp/50) + ')'
      var r = Math.min(barW*0.3, 4)
      roundRect(waveformCtx, x, my - amp/2, barW*0.8, amp, r); waveformCtx.fill()
      if(x2 !== x){ roundRect(waveformCtx, x2, my - amp/2, barW*0.8, amp, r); waveformCtx.fill() }
    }
  } else {
    var barW2 = 4, gap = 4, count = Math.floor(w / (barW2 + gap))
    waveformCtx.fillStyle = 'rgba(79,167,255,0.12)'
    for(var j = 0; j < count; j++){ var x3 = j*(barW2+gap) + (w - count*(barW2+gap))/2; waveformCtx.fillRect(x3, my-1, barW2, 2) }
  }
}

function loadTranscript(){
  fetch('/api/voice/details').then(function(r){ return r.json() }).then(function(d){
    var e = document.getElementById(_id + '-transcript-text')
    if(!e) return
    var rt = d.realtime || {}, txt = rt.last_transcript || rt.transcription || (d.stt && d.stt.last_text) || ''
    if(txt && txt !== _lastTranscript){ e.textContent = '"' + txt + '"'; _lastTranscript = txt }
  }).catch(function(){})
}

async function load() {
  var ep = document.getElementById(_id + '-content')
  if(!ep) return
  try{
    var statusResp = await fetch('/api/voice/status')
    var detailsResp = await fetch('/api/voice/details')
    var status = await statusResp.json()
    var details = await detailsResp.json()

    var dataKey = JSON.stringify({s:status, d:details})
    if(dataKey === _lastData) return
    _lastData = dataKey

    var d = details || {}, s = status || {}
    var state = s.state || 'unavailable', sp = s.is_speaking, mic = s.mic_active
    var m = d.metrics || {}, tts = d.tts || {}, stt = d.stt || {}, rt = d.realtime || {}, emo = d.emotion_detector || {}
    var iconClass = '', stateLabel = state, isActive = false
    if(state === 'listening' || state === 'listening_for_wake'){ iconClass = 'listening'; stateLabel = 'Listening' }
    else if(state === 'speech' || state === 'recording' || state === 'processing'){ iconClass = 'active'; stateLabel = 'Active'; isActive = true }
    else if(state === 'wake_detected'){ iconClass = 'active'; stateLabel = 'Wake Detected'; isActive = true }
    else if(state === 'error' || state === 'unavailable'){ iconClass = 'error'; stateLabel = 'Unavailable' }
    var emoConf = emo.confidence || 0

    var voiceActive = !!(state === 'listening' || state === 'listening_for_wake' || state === 'speech' || state === 'recording' || state === 'processing' || state === 'wake_detected')

    ep.innerHTML =
      '<div class="voice-toggle-wrap" style="display:flex;justify-content:center;margin-bottom:16px">' +
        '<button id="voice-toggle-btn" class="voice-toggle-btn ' + (voiceActive ? 'on' : 'off') + '" style="display:flex;align-items:center;gap:10px;padding:12px 28px;border:2px solid ' + (voiceActive ? 'var(--success)' : 'var(--text-muted)') + ';border-radius:30px;background:' + (voiceActive ? 'rgba(61,220,151,0.1)' : 'rgba(112,121,140,0.08)') + ';color:' + (voiceActive ? 'var(--success)' : 'var(--text-muted)') + ';font-size:15px;font-weight:600;cursor:pointer;transition:all 200ms ease;outline:none">' +
          '<span style="font-size:20px">' + (voiceActive ? '🎙' : '🔇') + '</span>' +
          '<span>' + (voiceActive ? 'Voice On' : 'Voice Off') + '</span>' +
        '</button>' +
      '</div>' +
      '<div class="voice-transcript-wrap" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:16px 20px;margin-bottom:12px"><div class="voice-transcript-label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px">Live Transcription</div><div id="' + _id + '-transcript-text" class="voice-transcript-empty" style="font-size:14px;color:var(--text-secondary);font-style:italic;min-height:20px">Listening for speech...</div></div>' +
      '<div class="voice-emotion-wrap" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:16px 20px;margin-bottom:12px"><div class="voice-emotion-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><div class="voice-emotion-label" style="font-size:18px;font-weight:600;color:var(--text-primary);text-transform:capitalize">' + (emo.label || 'neutral') + '</div><div class="voice-emotion-confidence" style="display:flex;align-items:center;gap:8px"><span class="pct" style="font-size:14px;font-weight:600;color:var(--accent-highlight);font-family:var(--font-mono)">' + (emoConf ? Math.round(emoConf*100) + '%' : '—') + '</span><div class="voice-emotion-bar-bg" style="width:120px;height:6px;background:var(--glass-strong);border-radius:3px;overflow:hidden"><div class="voice-emotion-bar-fill" style="height:100%;width:' + (emoConf ? Math.round(emoConf*100) : 0) + '%;background:linear-gradient(90deg,var(--accent-highlight),var(--accent));border-radius:3px;transition:width 0.5s ease"></div></div></div></div><div style="font-size:11px;color:var(--text-muted)">' + (emo.features ? Object.entries(emo.features).map(function(kv){ return kv[0] + ': ' + (typeof kv[1] === 'number' ? kv[1].toFixed(3) : kv[1]) }).join(' · ') : 'No features') + '</div></div>' +
      '<div class="voice-status-row" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">' +
        '<div class="voice-status-chip' + (isActive ? ' active' : '') + '" style="padding:4px 12px;border-radius:8px;font-size:11px;background:rgba(18,21,28,0.7);border:1px solid var(--glass-border);color:var(--text-muted)">' + stateLabel + '</div>' +
        '<div class="voice-status-chip' + (sp ? ' active' : '') + '">' + (sp ? 'Speaking' : 'Silent') + '</div>' +
        '<div class="voice-status-chip' + (mic ? ' active' : '') + '">' + (mic ? 'Mic On' : 'Mic Off') + '</div>' +
        (s.wake_detected ? '<div class="voice-status-chip active">Wake!</div>' : '') +
        '<div class="voice-status-chip">Wake: ' + ((s.wake_words || []).join(', ') || '—') + '</div>' +
        '<div class="voice-status-chip">Porcupine: ' + (s.porcupine_active ? 'On' : 'Off') + '</div>' +
      '</div>' +
      '<div class="voice-stats-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px">' +
        '<div class="voice-stat" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:10px;padding:12px;text-align:center"><div class="val" style="font-size:22px;font-weight:700;color:var(--text-primary)">' + (m.recordings || 0) + '</div><div class="lbl" style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-top:2px">Recordings</div></div>' +
        '<div class="voice-stat"><div class="val">' + (m.total_duration_seconds ? Math.round(m.total_duration_seconds) + 's' : '—') + '</div><div class="lbl">Total Audio</div></div>' +
        '<div class="voice-stat"><div class="val">' + (m.successful_transcriptions || 0) + '</div><div class="lbl">Transcriptions</div></div>' +
        '<div class="voice-stat"><div class="val">' + (m.wake_detections || 0) + '</div><div class="lbl">Wake Dets</div></div>' +
        '<div class="voice-stat"><div class="val">' + (m.errors || 0) + '</div><div class="lbl">Errors</div></div>' +
        '<div class="voice-stat"><div class="val">' + (m.transcription_success_rate ? Math.round(m.transcription_success_rate*100) + '%' : '—') + '</div><div class="lbl">Success Rate</div></div>' +
      '</div>' +
      '<div class="memory-grid" style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:12px">' +
        '<div class="section-card" style="background:var(--glass);border:1px solid var(--glass-border);border-radius:14px;padding:16px 20px"><h2 style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">Config</h2>' +
          voiceConfigRow('Sample Rate', d.sample_rate) +
          voiceConfigRow('VAD Threshold', d.vad_threshold) +
          voiceConfigRow('Silence Timeout', d.silence_timeout ? d.silence_timeout + 's' : '—') +
          voiceConfigRow('Max Recording', d.max_recording ? d.max_recording + 's' : '—') +
        '</div>' +
        '<div class="section-card"><h2 style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">TTS</h2>' +
          voiceConfigRow('Engine', tts.engine) +
          voiceConfigRow('Voice', tts.voice) +
          voiceConfigRow('Language', tts.language) +
          voiceConfigRow('Speed', tts.base_speed) +
          voiceConfigRow('Emotion', tts.last_emotion) +
        '</div>' +
        (rt && rt.player_state ? '<div class="section-card"><h2>Stream Player</h2>' + voiceConfigRow('State', rt.player_state) + voiceConfigRow('Queue Size', rt.queue_size || 0) + voiceConfigRow('Speaking', rt.is_speaking ? 'Yes' : 'No') + '</div>' : '') +
        (stt && stt.device ? '<div class="section-card"><h2>STT</h2>' + voiceConfigRow('Device', stt.device) + voiceConfigRow('Sample Rate', stt.sample_rate) + '</div>' : '') +
      '</div>'

    var anf = d.adaptive_noise, aec = d.full_aec, diar = d.diarization
    if(anf || aec || diar){
      var chips = document.createElement('div'); chips.className = 'voice-status-row'; chips.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-top:8px'
      if(anf && anf.adaptive_updates !== undefined){ var c = document.createElement('div'); c.className = 'voice-status-chip'; c.textContent = 'Noise Filter: ' + anf.adaptive_updates + ' updates · profile ' + (anf.profile_available ? '✓' : '✗'); chips.appendChild(c) }
      if(aec && aec.filter_length !== undefined){ var c2 = document.createElement('div'); c2.className = 'voice-status-chip'; c2.textContent = 'AEC: ' + aec.filter_length + ' taps · DT:' + (aec.double_talk ? '✓' : '✗'); chips.appendChild(c2) }
      if(diar && diar.registered_profiles !== undefined){ var c3 = document.createElement('div'); c3.className = 'voice-status-chip'; c3.textContent = 'Diarization: ' + diar.registered_profiles + ' profiles · ' + (diar.total_segments || 0) + ' segs'; chips.appendChild(c3) }
      ep.appendChild(chips)
    }

    // Wire toggle button
    var toggleBtn = document.getElementById('voice-toggle-btn')
    if(toggleBtn){
      toggleBtn.addEventListener('click', function(){
        fetch('/api/voice/toggle', {method:'POST'}).then(function(r){ return r.json() }).then(function(resp){
          load()
        }).catch(function(){})
      })
    }

    createWaveform(ep)
    if(waveformCtx){
      var ws = document.getElementById('waveform-status')
      if(ws) ws.textContent = isActive ? 'Active' : 'Idle'
      drawWaveform(isActive)
    }
  } catch(e){
    ep.innerHTML = '<div class="no-data"><span>' + e.message + '</span></div>'
  }
}

function voiceConfigRow(key, val){
  return '<div class="voice-config-row" style="display:flex;justify-content:space-between;padding:5px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,0.03)"><span class="key" style="color:var(--text-secondary)">' + key + '</span><span class="val" style="color:var(--text-primary)">' + (val !== undefined && val !== null ? val : '—') + '</span></div>'
}

function _init(){
  load()
  _intervals.push(setInterval(function(){
    fetch('/api/voice/status').then(function(r){ return r.json() }).then(function(s){
      var active = !!(s.is_speaking || s.mic_active || s.state === 'speech' || s.state === 'recording' || s.state === 'processing')
      var ws = document.getElementById('waveform-status')
      if(ws) ws.textContent = active ? 'Active' : 'Idle'
      if(waveformCtx) drawWaveform(active)
      loadTranscript()
    }).catch(function(){ if(waveformCtx) drawWaveform(false) })
    load()
  }, 3000))
}

function _destroy(){
  _intervals.forEach(function(iv){ clearInterval(iv) })
  _intervals.length = 0
  waveformCtx = null
  _waveCanvas = null
  _lastData = ''
  _lastTranscript = ''
}

window.MaiSpaces = window.MaiSpaces || {}
window.MaiSpaces[_id] = { init: _init, destroy: _destroy }
if(window.MaiRouter) window.MaiRouter.register(_id, { label: 'Voice Center', subtitle: 'Speech, transcription & audio', icon: '🎤', init: _init, destroy: _destroy })
})()
