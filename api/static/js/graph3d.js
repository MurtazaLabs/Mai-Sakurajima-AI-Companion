let THREE, OrbitControls

async function loadThree(){
  try{
    const[mod,oc]=await Promise.all([
      import('three'),
      import('three/addons/controls/OrbitControls.js')
    ])
    THREE=mod.default||mod;OrbitControls=oc.OrbitControls
    return true
  }catch(e){
    const el=document.getElementById('graph-container')
    if(el)el.innerHTML='<div class="no-data"><span>3D engine unavailable</span><span style="font-size:11px;color:var(--text-muted)">Cannot load Three.js from CDN. Check your internet connection or try a modern browser.</span></div>'
    return false
  }
}

const NODE_COLORS={
  cognitive:0x9D7BFF,entity:0x4FA7FF,memory:0x67E8F9,rule:0xFFC857,
  thought:0x3DDC97,emotion:0xFF5D73,belief:0xB794FF,goal:0xFF8A65,
  'goal:active':0xFF8A65,'goal:completed':0x3DDC97,'goal:failed':0xFF5D73,default:0x70798C
}

const NODE_LABELS={
  belief:'Belief',emotion:'Emotion',memory:'Memory',thought:'Thought',rule:'Rule',
  'goal:active':'Active Goal','goal:completed':'Completed Goal','goal:failed':'Failed Goal',
  entity:'Entity',person:'Person',place:'Place',project:'Project',technology:'Technology',
  event:'Event',skill:'Skill',media:'Media',organization:'Organization',
  relationship:'Relationship',interest:'Interest',character:'Character',topic:'Topic',unknown:'Unknown'
}

function nodeColor(t){return NODE_COLORS[t]||NODE_COLORS.default}

async function init(){
  const ok=await loadThree()
  if(!ok)return

  const container=document.getElementById('graph-container')
  if(!container)return

  let data
  try{
    const r=await fetch('/api/graph')
    if(!r.ok)throw new Error('HTTP '+r.status)
    data=await r.json()
  }catch(e){
    document.getElementById('graph-loading').innerHTML='<span>Cannot load graph</span><span style="font-size:11px">'+e.message+'</span>'
    return
  }

  const nodes=data.nodes||[],edges=data.edges||[]
  const loading=document.getElementById('graph-loading')
  if(loading)loading.remove()

  if(!nodes.length){
    container.innerHTML+='<div class="no-data"><span>No graph data available yet</span></div>'
    return
  }

  const uniqueTypes=new Set(nodes.map(n=>n.type))
  document.getElementById('graph-stats').innerHTML=nodes.length+' nodes · '+edges.length+' edges · '+uniqueTypes.size+' types'

  const legendEl=document.getElementById('graph-legend')
  const ordered=['cognitive','entity','memory','thought','rule','emotion']
  const shown=new Set()
  let lhtml=''
  for(const g of ordered){if(uniqueTypes.has(g)&&!shown.has(g)){shown.add(g);lhtml+='<span class="legend-dot" style="background:#'+nodeColor(g).toString(16).padStart(6,'0')+'"></span>'+g+' '}}
  for(const t of uniqueTypes){if(!shown.has(t)&&NODE_LABELS[t]){shown.add(t);lhtml+='<span class="legend-dot" style="background:#'+nodeColor(t).toString(16).padStart(6,'0')+'"></span>'+NODE_LABELS[t]+' '}}
  legendEl.innerHTML=lhtml

  const rect=container.getBoundingClientRect()
  const W=rect.width,H=Math.max(rect.height,400)

  const scene=new THREE.Scene()
  const camera=new THREE.PerspectiveCamera(45,W/H,0.1,1000)
  camera.position.set(30,20,40)

  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true})
  renderer.setSize(W,H)
  renderer.setPixelRatio(Math.min(devicePixelRatio,2))
  renderer.setClearColor(0x090B10,0)
  container.appendChild(renderer.domElement)

  const controls=new OrbitControls(camera,renderer.domElement)
  controls.enableDamping=true;controls.dampingFactor=0.08
  controls.rotateSpeed=0.8;controls.zoomSpeed=1.2
  controls.minDistance=10;controls.maxDistance=200
  controls.autoRotate=true;controls.autoRotateSpeed=0.5

  scene.add(new THREE.AmbientLight(0x404060,1.5))
  const dl=new THREE.DirectionalLight(0xffffff,2);dl.position.set(20,30,20);scene.add(dl)
  const dl2=new THREE.DirectionalLight(0x4FA7FF,1);dl2.position.set(-20,10,-20);scene.add(dl2)

  const starGeo=new THREE.BufferGeometry()
  const starC=800,starP=new Float32Array(starC*3)
  for(let i=0;i<starC*3;i++)starP[i]=(Math.random()-0.5)*300
  starGeo.setAttribute('position',new THREE.BufferAttribute(starP,3))
  scene.add(new THREE.Points(starGeo,new THREE.PointsMaterial({color:0xffffff,size:0.3,transparent:true,opacity:0.4})))

  const nodeMeshes={}
  const nodeGroup=new THREE.Group();scene.add(nodeGroup)

  for(const nd of nodes){
    const r=nd.group==='cognitive'?3.5:2.5
    const mat=new THREE.MeshPhongMaterial({color:nodeColor(nd.type),emissive:nodeColor(nd.type),emissiveIntensity:0.15,specular:0x444466,shininess:30})
    const mesh=new THREE.Mesh(new THREE.SphereGeometry(r,24,24),mat)
    mesh.position.set((Math.random()-0.5)*30,(Math.random()-0.5)*20,(Math.random()-0.5)*30)
    mesh.userData={id:nd.id,name:nd.name,type:nd.type,group:nd.group,metadata:nd.metadata||{},baseColor:nodeColor(nd.type),origR:r}
    nodeGroup.add(mesh);nodeMeshes[nd.id]=mesh
  }

  const edgeMat=new THREE.LineBasicMaterial({color:0x4FA7FF,transparent:true,opacity:0.12})
  const edgeGroup=new THREE.Group();scene.add(edgeGroup)

  for(const e of edges){
    const s=nodeMeshes[e.source],t=nodeMeshes[e.target]
    if(!s||!t)continue
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([s.position,t.position]),edgeMat)
    line.userData={source:e.source,target:e.target};edgeGroup.add(line)
  }

  const sim={nodes:[],edges:[]}
  for(const nd of nodes){const m=nodeMeshes[nd.id];if(m)sim.nodes.push({mesh:m,pos:m.position.clone(),vel:new THREE.Vector3(),id:nd.id,type:nd.type})}
  const nodeIndex={}
  sim.nodes.forEach((n,i)=>{nodeIndex[n.id]=i})
  for(const e of edges){const si=nodeIndex[e.source],ti=nodeIndex[e.target];if(si!==undefined&&ti!==undefined)sim.edges.push({a:si,b:ti})}

  let simFrames=200
  function simStep(){
    const rep=15,att=0.005,damp=0.92,minD=3
    for(let i=0;i<sim.nodes.length;i++){
      const n=sim.nodes[i]
      n.vel.x+=(-n.pos.x)*0.003;n.vel.y+=(-n.pos.y)*0.003;n.vel.z+=(-n.pos.z)*0.003
      for(let j=i+1;j<sim.nodes.length;j++){
        const o=sim.nodes[j],dx=n.pos.x-o.pos.x,dy=n.pos.y-o.pos.y,dz=n.pos.z-o.pos.z
        let d=Math.sqrt(dx*dx+dy*dy+dz*dz)||1;const f=rep/(d*d)
        if(d<minD)d=minD;const fx=(dx/d)*f,fy=(dy/d)*f,fz=(dz/d)*f
        n.vel.x+=fx;n.vel.y+=fy;n.vel.z+=fz;o.vel.x-=fx;o.vel.y-=fy;o.vel.z-=fz
      }
    }
    for(const e of sim.edges){
      const a=sim.nodes[e.a],b=sim.nodes[e.b],dx=b.pos.x-a.pos.x,dy=b.pos.y-a.pos.y,dz=b.pos.z-a.pos.z
      const d=Math.sqrt(dx*dx+dy*dy+dz*dz)||1,f=att*(d-15)
      const fx=(dx/d)*f,fy=(dy/d)*f,fz=(dz/d)*f
      a.vel.x+=fx;a.vel.y+=fy;a.vel.z+=fz;b.vel.x-=fx;b.vel.y-=fy;b.vel.z-=fz
    }
    for(const n of sim.nodes){n.vel.multiplyScalar(damp);n.pos.add(n.vel);n.mesh.position.copy(n.pos)}
    let ei=0
    for(const e of edges){
      const s=nodeMeshes[e.source],t=nodeMeshes[e.target]
      if(!s||!t)continue;const line=edgeGroup.children[ei];if(line){const p=line.geometry.attributes.position;p.setXYZ(0,s.position.x,s.position.y,s.position.z);p.setXYZ(1,t.position.x,t.position.y,t.position.z);p.needsUpdate=true};ei++
    }
  }

  function simLoop(){if(simFrames>0){simStep();simFrames--;if(simFrames===0){for(const n of sim.nodes)n.vel.set(0,0,0)}}}

  const raycaster=new THREE.Raycaster()
  const pointer=new THREE.Vector2()
  let hovered=null
  const tooltip=document.getElementById('graph-tooltip')

  renderer.domElement.addEventListener('pointermove',e=>{
    const r=renderer.domElement.getBoundingClientRect()
    pointer.x=((e.clientX-r.left)/r.width)*2-1;pointer.y=-((e.clientY-r.top)/r.height)*2+1
  })

  function updateHover(){
    raycaster.setFromCamera(pointer,camera)
    const hits=raycaster.intersectObjects(Object.values(nodeMeshes))
    if(hovered){hovered.material.emissiveIntensity=0.15;hovered.material.color.setHex(hovered.userData.baseColor);hovered=null;tooltip.className='graph-tooltip'}
    if(hits.length){
      const m=hits[0].object;m.material.emissiveIntensity=0.6;m.material.color.setHex(0xffffff);hovered=m
      const ud=m.userData,meta=ud.metadata
      let detail=''
      if(meta){
        if(meta.confidence)detail+='Confidence: '+(meta.confidence*100).toFixed(0)+'%'
        if(meta.status)detail+=(detail?' · ':'')+'Status: '+meta.status
        if(meta.description)detail+=(detail?' · ':'')+meta.description
        if(meta.text)detail+=(detail?' · ':'')+meta.text.substring(0,60)
        if(meta.conclusion)detail+=(detail?' · ':'')+meta.conclusion.substring(0,60)
        if(meta.emotion_type)detail+=(detail?' · ':'')+'Emotion: '+meta.emotion_type
        if(meta.predicate)detail+=(detail?' · ':'')+'rel: '+meta.predicate
        if(meta.intensity!==undefined)detail+=(detail?' · ':'')+'intensity: '+meta.intensity.toFixed(2)
      }
      tooltip.innerHTML='<div class="tt-label">'+(NODE_LABELS[ud.type]||ud.type)+'</div><div class="tt-name">'+(ud.name||ud.id)+'</div>'+(detail?'<div class="tt-detail">'+detail+'</div>':'')
      tooltip.className='graph-tooltip visible'
      const cr=container.getBoundingClientRect(),mx=hits[0].point.clone().project(camera)
      tooltip.style.left=((mx.x+1)/2*cr.width+12)+'px';tooltip.style.top=((-mx.y+1)/2*cr.height-10)+'px'
    }
  }

  document.getElementById('graph-search').addEventListener('input',()=>{
    const q=document.getElementById('graph-search').value.toLowerCase().trim()
    for(const[id,mesh]of Object.entries(nodeMeshes)){
      if(!q||mesh.userData.name.toLowerCase().includes(q)||mesh.userData.id.toLowerCase().includes(q)){mesh.material.emissiveIntensity=q?0.4:0.15;mesh.material.color.setHex(mesh.userData.baseColor);mesh.scale.set(1,1,1)}
      else{mesh.material.emissiveIntensity=0;mesh.material.color.setHex(0x333355);mesh.scale.set(0.3,0.3,0.3)}
    }
    const dim=!!q;for(const c of edgeGroup.children)c.material.opacity=dim?0.02:0.12
  })

  window.addEventListener('resize',()=>{
    const r=container.getBoundingClientRect(),w=r.width,h=Math.max(r.height,400)
    camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h)
  })

  function animate(){requestAnimationFrame(animate);simLoop();controls.update();updateHover();renderer.render(scene,camera)}
  setTimeout(()=>{controls.autoRotate=true},2500)
  animate()
}

document.addEventListener('DOMContentLoaded',init)