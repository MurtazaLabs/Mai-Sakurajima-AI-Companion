(function(){'use strict'
const orb=(function(){
  const SIZE=72,R=28,PI2=Math.PI*2
  let state='idle',emotion='neutral',thought='',goal='',conf=0
  let menuOpen=false,fade=0,pulse=0,phase=0,particles=[],ripples=[]
  let canvas,ctx,animId,pollTimer

  function createCanvas(){
    const c=document.createElement('canvas')
    c.width=SIZE;c.height=SIZE
    c.style.cssText='position:fixed;bottom:calc(var(--taskbar-height,64px) + 32px);right:24px;z-index:9999;cursor:pointer;border-radius:50%'
    c.addEventListener('click',toggleMenu)
    document.body.appendChild(c)
    return c
  }

  function toggleMenu(e){
    e.stopPropagation()
    menuOpen=!menuOpen
    document.getElementById('mai-orb-menu').classList.toggle('open',menuOpen)
  }

  function createMenu(){
    const d=document.createElement('div')
    d.id='mai-orb-menu'
    d.innerHTML='<div class="orb-menu-mood"></div><div class="orb-menu-thought"></div><div class="orb-menu-goal"></div>'
    d.addEventListener('click',e=>e.stopPropagation())
    document.body.appendChild(d)
    document.addEventListener('click',()=>{menuOpen=false;d.classList.remove('open')})
    return d
  }

  function fetchState(){
    fetch('/api/consciousness').then(r=>r.json()).then(d=>{
      if(d.emotion){
        emotion=d.emotion.dominant_emotion||d.emotion.name||'neutral'
        conf=d.emotion.confidence||0
      }
      if(d.cognitive){
        thought=d.cognitive.current_thought||d.cognitive.recent_thoughts?.[0]||''
        goal=d.cognitive.current_goal||''
      }
      const menu=document.getElementById('mai-orb-menu')
      if(menu){
        menu.querySelector('.orb-menu-mood').textContent='Mood: '+emotion
        menu.querySelector('.orb-menu-thought').textContent=thought||'—'
        menu.querySelector('.orb-menu-goal').textContent=goal?'Goal: '+goal:''
      }
    }).catch(()=>{})
    fetch('/api/voice/status').then(r=>r.json()).then(d=>{
      if(d.state==='listening'||d.state==='listening_for_wake')state='listening'
      else if(d.state==='speech'||d.state==='recording'||d.state==='processing'||d.state==='transcribing')state='speaking'
      else if(d.is_speaking)state='thinking'
      else state='idle'
      if(d.state==='wake_detected')state='speaking'
    }).catch(()=>{})
  }

  function addParticle(){
    const a=Math.random()*PI2,spd=0.2+Math.random()*0.3
    const dist=R+8+Math.random()*20
    particles.push({x:Math.cos(a)*dist,y:Math.sin(a)*dist,dx:Math.cos(a)*spd,dy:Math.sin(a)*spd,size:1+Math.random()*2,life:1,decay:0.003+Math.random()*0.005,angle:a,orbit:dist,spd:spd})
  }

  function addRipple(){
    ripples.push({r:4,alpha:0.6,speed:0.5+Math.random()*0.3})
  }

  function draw(t){
    if(!ctx)return
    ctx.clearRect(0,0,SIZE,SIZE)
    phase+=0.015
    pulse=Math.sin(phase*1.5)*0.5+0.5

    // Particle count by state
    const targetP=state==='idle'?3:state==='thinking'?8:state==='listening'?6:10
    while(particles.length<targetP&&Math.random()<0.3)addParticle()
    if(particles.length>targetP+5)particles=particles.slice(-targetP-5)

    // Breathing scale
    const breath=1+0.025*Math.sin(phase*0.8)

    // Update particles
    for(let i=particles.length-1;i>=0;i--){
      const p=particles[i]
      if(state==='thinking'){
        p.angle+=0.015
        p.x=Math.cos(p.angle)*p.orbit
        p.y=Math.sin(p.angle)*p.orbit
      }else{
        p.x+=p.dx;p.y+=p.dy
        const dist=Math.sqrt(p.x*p.x+p.y*p.y)
        if(dist>R+45)p.life-=0.02
      }
      p.life-=p.decay
      if(p.life<=0)particles.splice(i,1)
    }

    // Ripples (speaking state)
    if(state==='speaking'&&Math.random()<0.15)addRipple()
    for(let i=ripples.length-1;i>=0;i--){
      const rp=ripples[i]
      rp.r+=rp.speed
      rp.alpha-=0.015
      if(rp.alpha<=0){ripples.splice(i,1);continue}
      ctx.beginPath()
      ctx.arc(SIZE/2,SIZE/2,rp.r,0,PI2)
      ctx.strokeStyle=`rgba(157,123,255,${rp.alpha*0.4})`
      ctx.lineWidth=1.5
      ctx.stroke()
    }

    // Outer glow
    const glowSize=R*2+40+10*pulse
    const grad=ctx.createRadialGradient(SIZE/2,SIZE/2,R*0.3,SIZE/2,SIZE/2,glowSize)
    let gColor='rgba(79,167,255,0.12)'
    if(state==='listening')gColor='rgba(255,200,87,0.18)'
    else if(state==='thinking')gColor='rgba(157,123,255,0.18)'
    else if(state==='speaking')gColor='rgba(61,220,151,0.18)'
    grad.addColorStop(0,'rgba(255,255,255,0.05)')
    grad.addColorStop(0.5,gColor)
    grad.addColorStop(1,'rgba(0,0,0,0)')
    ctx.fillStyle=grad
    ctx.fillRect(0,0,SIZE,SIZE)

    // Draw particles
    for(const p of particles){
      ctx.beginPath()
      ctx.arc(SIZE/2+p.x,SIZE/2+p.y,p.size*p.life,0,PI2)
      ctx.fillStyle=`rgba(157,123,255,${p.life*0.6})`
      ctx.fill()
    }

    // Core glow ring (listening)
    if(state==='listening'){
      ctx.beginPath()
      ctx.arc(SIZE/2,SIZE/2,R*breath+4,0,PI2)
      ctx.strokeStyle=`rgba(255,200,87,${0.3+0.2*pulse})`
      ctx.lineWidth=2.5
      ctx.stroke()
    }

    // Thinking ring rotation
    if(state==='thinking'){
      ctx.beginPath()
      ctx.arc(SIZE/2,SIZE/2,R*breath+3,0,PI2*0.7)
      ctx.strokeStyle=`rgba(157,123,255,${0.3+0.2*pulse})`
      ctx.lineWidth=2
      ctx.stroke()
    }

    // Core circle
    ctx.beginPath()
    ctx.arc(SIZE/2,SIZE/2,R*breath,0,PI2)
    let fill='rgba(79,167,255,0.35)'
    if(state==='listening')fill='rgba(255,200,87,0.4)'
    else if(state==='thinking')fill='rgba(157,123,255,0.4)'
    else if(state==='speaking')fill='rgba(61,220,151,0.4)'
    ctx.fillStyle=fill
    ctx.fill()

    // Inner glow
    const ig=ctx.createRadialGradient(SIZE/2-R*0.3,SIZE/2-R*0.3,0,SIZE/2,SIZE/2,R*breath)
    ig.addColorStop(0,'rgba(255,255,255,0.3)')
    ig.addColorStop(1,'rgba(255,255,255,0)')
    ctx.fillStyle=ig
    ctx.fill()

    animId=requestAnimationFrame(draw)
  }

  function start(){
    if(canvas)return
    canvas=createCanvas()
    ctx=canvas.getContext('2d')
    createMenu()
    fetchState()
    pollTimer=setInterval(fetchState,3000)
    draw()
  }

  return{start}
})()

document.addEventListener('DOMContentLoaded',()=>orb.start())
})()