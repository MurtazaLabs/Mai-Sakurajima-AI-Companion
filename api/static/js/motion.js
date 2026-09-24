(function(){'use strict'
// Add ambient motion classes to elements
function initMotion(){
  // Wallpaper drift
  const wp=document.getElementById('wallpaper')
  if(wp)wp.classList.add('animate-wallpaper')

  // Panel float on subsystem pages
  document.querySelectorAll('.section-card, .memory-card, .voice-hero, .reflection-card, .thought-entry').forEach((el,i)=>{
    el.classList.add(i%2===0?'animate-float':'animate-float-delayed')
  })
}

// Pointer glow trail
let glowEl=null
function initCursorGlow(){
  if(glowEl)return
  glowEl=document.createElement('div')
  glowEl.style.cssText='position:fixed;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle,rgba(79,167,255,0.04) 0%,transparent 70%);pointer-events:none;z-index:9997;transform:translate(-50%,-50%);transition:left 0.3s ease,top 0.3s ease'
  document.body.appendChild(glowEl)
  let raf=null
  document.addEventListener('mousemove',e=>{
    if(raf)return
    raf=requestAnimationFrame(()=>{
      glowEl.style.left=e.clientX+'px'
      glowEl.style.top=e.clientY+'px'
      raf=null
    })
  })
}

// Parallax — subtle wallpaper offset based on mouse position
// Combines mouse-responsive parallax with a slow ambient drift
let parallaxRaf=null
let parallaxEl=null
let parallaxIdleTimer=null
let parallaxDriftAngle=0
function initParallax(){
  parallaxEl=document.getElementById('wallpaper')
  if(!parallaxEl)return

  // Slow ambient drift (replaces CSS animation which conflicted with inline transform)
  function driftTick(){
    parallaxDriftAngle+=0.002
    const driftX=Math.sin(parallaxDriftAngle)*4
    const driftY=Math.cos(parallaxDriftAngle*0.7)*3
    // Only apply drift when no recent mouse move
    if(!parallaxIdleTimer){
      parallaxEl.style.transform='translate('+driftX+'px,'+driftY+'px)'
    }
    requestAnimationFrame(driftTick)
  }
  requestAnimationFrame(driftTick)

  // Mouse parallax (overrides drift with smooth transition)
  document.addEventListener('mousemove',function(e){
    if(parallaxRaf)return
    if(parallaxIdleTimer)clearTimeout(parallaxIdleTimer)
    parallaxIdleTimer=setTimeout(function(){ parallaxIdleTimer=null },2000)
    parallaxRaf=requestAnimationFrame(function(){
      const cx=window.innerWidth/2
      const cy=window.innerHeight/2
      const dx=(e.clientX-cx)/cx
      const dy=(e.clientY-cy)/cy
      parallaxEl.style.transform='translate('+(dx*6)+'px,'+(dy*4)+'px)'
      parallaxRaf=null
    })
  })
}

document.addEventListener('DOMContentLoaded',()=>{
  initMotion()
  if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    initCursorGlow()
    initParallax()
  }
})
})()
