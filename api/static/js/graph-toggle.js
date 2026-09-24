document.getElementById("graph-toggle")?.addEventListener("click", function () {
  var c = document.getElementById("graph-container");
  if (this.textContent === "3D") {
    this.textContent = "2D";
    c.innerHTML = '<div class="no-data" id="graph-loading"><span>Loading 3D graph...</span></div>';
    var s = document.createElement("script");
    s.type = "importmap";
    s.textContent = JSON.stringify({"imports": {"three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js", "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}});
    document.head.appendChild(s);
    var m = document.createElement("script");
    m.type = "module";
    m.src = "js/graph3d.js";
    document.body.appendChild(m);
  } else {
    this.textContent = "3D";
    c.innerHTML = '<div class="no-data" id="graph-loading"><span>Loading graph...</span></div>';
    location.reload();
  }
});
