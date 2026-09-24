(function(){'use strict'
const DD=!!document.getElementById('desktop')
if(!DD)return

const WM={
  _z:100,
  _windows:{},
  _appWindows:{},
  _minimized:{},
  _restore:{},
  _list:[],

  get apps(){return window._MAI_APP_LIST||[]},

  open(app){
    if(!app)return null
    // If already open and not minimized, focus it
    const existing=this._appWindows[app.id]
    if(existing){
      const w=document.getElementById(existing)
      if(w){
        if(this._minimized[existing]){
          this.restore(existing)
        }else{
          w.style.zIndex=++this._z
          this._updateDock()
        }
        return w
      }
    }
    return this._create(app)
  },

  _create(app){
    const id='win-'+app.id+'-'+Date.now()
    const w=document.createElement('div')
    w.className='desktop-window'
    w.id=id
    w.dataset.appId=app.id
    w.style.cssText='position:fixed;z-index:'+(++this._z)+';display:flex;flex-direction:column'

    // Size & position (cascade)
    const count=this._list.length
    w.style.width='660px';w.style.height='500px'
    w.style.left=(80+count*28)+'px'
    w.style.top=(60+count*28)+'px'

    // Title bar
    const tb=document.createElement('div')
    tb.className='win-titlebar'
    tb.innerHTML='<div class="win-dots"><span class="win-dot win-close" data-action="close"></span><span class="win-dot win-minimize" data-action="minimize"></span><span class="win-dot win-maximize" data-action="maximize"></span></div><span class="win-title">'+app.label+'</span><span class="win-spacer"></span><span class="win-close-x" data-action="close">✕</span>'

    // Body
    const body=document.createElement('div')
    body.className='win-body'
    const ifr=document.createElement('iframe')
    ifr.src=app.page;ifr.title=app.label
    ifr.setAttribute('loading','lazy')
    body.appendChild(ifr)

    // Resize handles
    const handles=['n','s','e','w','ne','nw','se','sw']
    handles.forEach(h=>{
      const el=document.createElement('div')
      el.className='win-handle win-handle-'+h
      el.dataset.edge=h
      w.appendChild(el)
    })

    w.appendChild(tb)
    w.appendChild(body)
    document.body.appendChild(w)

    // --- Drag ---
    let dx=false,dsx=0,dsy=0,doffX=0,doffY=0
    const grab=e=>{
      if(e.target.closest('[data-action]')||e.target.closest('.win-handle')||e.target.closest('.win-dots'))return
      dx=true
      const r=w.getBoundingClientRect()
      doffX=e.clientX-r.left;doffY=e.clientY-r.top
      w.style.cursor='grabbing'
      w.style.transition='none'
      e.preventDefault()
    }
    tb.addEventListener('mousedown',grab)
    document.addEventListener('mousemove',e=>{
      if(!dx)return
      const mx=e.clientX-doffX,my=e.clientY-doffY
      w.style.left=mx+'px';w.style.top=my+'px'
      this._clearRestore(id)
    })
    document.addEventListener('mouseup',()=>{if(dx){dx=false;w.style.cursor=''}})

    // --- Resize ---
    let rx=false,re='',rsx=0,rsy=0,rw=0,rh=0,rl=0,rt=0
    const hMap={e:[1,0,0,0],w:[-1,0,1,0],s:[0,1,0,0],n:[0,-1,0,1],ne:[1,-1,0,1],nw:[-1,-1,1,1],se:[1,1,0,0],sw:[-1,1,1,0]}
    w.querySelectorAll('.win-handle').forEach(el=>{
      el.addEventListener('mousedown',e=>{
        rx=true;re=el.dataset.edge
        const r=w.getBoundingClientRect()
        rw=r.width;rh=r.height;rl=r.left;rt=r.top;rsx=e.clientX;rsy=e.clientY
        w.style.transition='none'
        e.preventDefault()
      })
    })
    document.addEventListener('mousemove',e=>{
      if(!rx)return
      const d=e.clientX-rsx,dy=e.clientY-rsy,m=hMap[re]
      if(!m)return
      let nx=rl,ny=rt,nw=rw,nh=rh
      if(m[0]!==0){nw=Math.max(320,rw+m[0]*d);if(m[2]!==0)nx=rl+rw-nw}
      if(m[1]!==0){nh=Math.max(240,rh+m[1]*dy);if(m[3]!==0)ny=rt+rh-nh}
      w.style.left=nx+'px';w.style.top=ny+'px';w.style.width=nw+'px';w.style.height=nh+'px'
      this._clearRestore(id)
    })
    document.addEventListener('mouseup',()=>{rx=false})

    // --- Focus ---
    w.addEventListener('mousedown',()=>{w.style.zIndex=++this._z;this._updateDock()})

    // --- Actions (close/minimize/maximize) ---
    w.addEventListener('click',e=>{
      const btn=e.target.closest('[data-action]')
      if(!btn)return
      const a=btn.dataset.action
      if(a==='close')this.close(id)
      else if(a==='minimize')this.minimize(id)
      else if(a==='maximize')this.toggleMaximize(id)
    })

    // Double-click title bar maximizes
    tb.addEventListener('dblclick',e=>{
      if(e.target.closest('[data-action]')||e.target.closest('.win-dots'))return
      this.toggleMaximize(id)
    })

    this._windows[id]=app
    this._appWindows[app.id]=id
    this._list.push(id)
    this._updateDock()
    return w
  },

  close(id){
    const w=document.getElementById(id)
    if(!w)return
    const app=this._windows[id]
    w.style.transition='transform 200ms ease,opacity 200ms ease'
    w.style.transform='scale(0.9)';w.style.opacity='0'
    setTimeout(()=>{
      w.remove()
      delete this._windows[id]
      delete this._minimized[id]
      delete this._restore[id]
      if(app)delete this._appWindows[app.id]
      const i=this._list.indexOf(id)
      if(i>-1)this._list.splice(i,1)
      this._updateDock()
    },200)
  },

  minimize(id){
    const w=document.getElementById(id)
    if(!w)return
    this._minimized[id]=true
    w.classList.add('minimized')
    w.style.zIndex=0
    this._updateDock()
  },

  restore(id){
    const w=document.getElementById(id)
    if(!w)return
    this._minimized[id]=false
    w.classList.remove('minimized')
    w.style.zIndex=++this._z
    const r=this._restore[id]
    if(r){w.style.left=r.x+'px';w.style.top=r.y+'px';w.style.width=r.w+'px';w.style.height=r.h+'px';delete this._restore[id]}
    this._updateDock()
  },

  _clearRestore(id){delete this._restore[id]},

  toggleMaximize(id){
    const w=document.getElementById(id)
    if(!w)return
    if(w.classList.contains('maximized')){
      w.classList.remove('maximized')
      const r=this._restore[id]
      if(r){w.style.left=r.x+'px';w.style.top=r.y+'px';w.style.width=r.w+'px';w.style.height=r.h+'px';delete this._restore[id]}
    }else{
      const r=w.getBoundingClientRect()
      this._restore[id]={x:r.left,y:r.top,w:r.width,h:r.height}
      w.classList.add('maximized')
      w.style.left='0';w.style.top='0';w.style.width='100vw';w.style.height='100vh'
      w.style.zIndex=++this._z
    }
    this._updateDock()
  },

  getState(){return{count:this._list.length,windows:this._list.map(id=>{const w=document.getElementById(id);return{id,app:this._windows[id]?.label||'',minimized:!!this._minimized[id],maximized:w?.classList.contains('maximized')||false,visible:!!w}})} },

  _updateDock(){
    if(!window._MAI_TASKBAR_UPDATE)return
    const running=[]
    this._list.forEach(id=>{
      const app=this._windows[id]
      if(!app)return
      const w=document.getElementById(id)
      running.push({id:app.id,label:app.label,minimized:!!this._minimized[id],active:!!w&&!this._minimized[id]&&w.style.zIndex==this._z,exists:true})
    })
    window._MAI_TASKBAR_UPDATE(running)
  }
}

window._MAI_WM=WM

// Override desktop icon clicks only (taskbar + start menu have own handlers)
document.addEventListener('click',e=>{
  const icon=e.target.closest('.desktop-icon')
  if(!icon||icon.closest('#start-menu'))return
  e.preventDefault()
  const label=icon.querySelector('span')?.textContent||''
  const entry=WM.apps.find(a=>a.label===label)
  if(entry)WM.open(entry)
})
})()