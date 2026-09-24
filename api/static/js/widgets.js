(function(){'use strict'
const gw=document.getElementById('desktop-widgets')
if(!gw)return

function getTimeBasedGreeting(){
  const h=new Date().getHours()
  if(h<6)return'Still awake?'
  if(h<12)return'Good Morning'
  if(h<17)return'Good Afternoon'
  if(h<21)return'Good Evening'
  return'Good Night'
}

async function loadWidgets(){
  try{
    const[con,mem,goal]=await Promise.all([
      fetch('/api/consciousness').then(r=>r.json()),
      fetch('/api/memory/stats').then(r=>r.json()),
      fetch('/api/goals').then(r=>r.json()).catch(()=>({}))
    ])
    const em=con.emotion||{},cog=con.cognitive||{},per=con.personality||{}
    const emotionName=em.emotion||em.name||em.dominant_emotion||'neutral'
    const thought=cog.recent_thoughts?.[0]||''
    const gs=goal.stats||{}
    const activeGoals=gs.active||gs.total||0
    const memCount=mem.vector_count||0

    let html='<div class="widgets-row">'
    // Greeting widget
    html+=`<div class="widget-card animate-float">
  <div class="widget-greeting">${getTimeBasedGreeting()}</div>
  <div class="widget-mai-name">Mai</div>
  <div class="widget-emotion">Feeling <strong>${emotionName}</strong></div>
</div>`
    // Goal widget
    html+=`<div class="widget-card animate-float-delayed">
  <div class="widget-label">Current Goal</div>
  <div class="widget-value">${cog.current_goal||'Be present with you'}</div>
  <div class="widget-label" style="margin-top:6px">Active Goals</div>
  <div class="widget-value">${activeGoals}</div>
</div>`
    // Memory widget
    html+=`<div class="widget-card animate-float">
  <div class="widget-label">Memory</div>
  <div class="widget-value" style="font-size:28px">${memCount}</div>
  <div class="widget-label">stored memories</div>
  ${thought?`<div class="widget-thought">"${thought.slice(0,80)}${thought.length>80?'...':''}"</div>`:''}
</div>`
    // Personality widget
    html+=`<div class="widget-card animate-float-delayed">
  <div class="widget-label">Personality</div>
  ${per?Object.entries(per).slice(0,4).map(([k,v])=>`<div class="widget-trait"><span>${k}</span><div class="widget-trait-bar"><div class="widget-trait-fill" style="width:${(v*100).toFixed(0)}%"></div></div></div>`).join(''):'<div class="widget-value">—</div>'}
</div>`
    html+='</div>'
    gw.innerHTML=html
  }catch(e){
    gw.innerHTML='<div class="no-data"><span>Widgets unavailable</span></div>'
  }
}

document.addEventListener('DOMContentLoaded',()=>{
  loadWidgets()
  setInterval(loadWidgets,15000)
})
})()