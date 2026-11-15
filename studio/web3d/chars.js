/* The four 3D characters (old man, young man in a yellow hoodie, spiky-hair boy, young woman in a sari),
   built exactly like their preview pages, posed per video frame and rendered to a transparent PNG.
   Python calls R3.render({...}) through a headless browser (see studio/three_d.py). */
(function(){
  var renderer, scene, camera, stool, CH = {};
  var TARGET_Y = 0.9, PHI = 1.42;

  function init(){
    var canvas = document.getElementById('view');
    renderer = new THREE.WebGLRenderer({canvas:canvas, antialias:true, alpha:true, preserveDrawingBuffer:true});
    renderer.setPixelRatio(1);
    renderer.setClearColor(0x000000, 0);
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    scene = new THREE.Scene();
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);
    scene.add(new THREE.HemisphereLight(0xffffff, col(0x8fa3c4), 0.85));
    var sun = new THREE.DirectionalLight(0xfff4e0, 0.95);
    sun.position.set(2.2, 4, 3); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -1.8; sun.shadow.camera.right = 1.8;
    sun.shadow.camera.top = 2.4; sun.shadow.camera.bottom = -0.6;
    sun.shadow.camera.near = 0.5; sun.shadow.camera.far = 12;
    sun.shadow.bias = -0.0015;
    scene.add(sun);
    var rim = new THREE.DirectionalLight(0xbcd4ff, 0.45);
    rim.position.set(-3, 2, -3); scene.add(rim);
    var ground = new THREE.Mesh(new THREE.CircleGeometry(1.5, 48), new THREE.ShadowMaterial({opacity:0.22}));
    ground.rotation.x = -Math.PI/2; ground.receiveShadow = true; scene.add(ground);
    stool = mesh(new THREE.CylinderGeometry(0.2, 0.22, 0.38, 28), mat(0xB9855A, 0.8));
    stool.position.set(0, 0.19, -0.03); stool.receiveShadow = true; stool.visible = false; scene.add(stool);
  }

  /* ---------------------------------------------------------------- helpers */
  /* Colours are written as sRGB hex; three.js r128 works in linear light, so convert them (otherwise they look washed out). */
  function col(c){ return new THREE.Color(c).convertSRGBToLinear(); }
  function mat(c, r){ return new THREE.MeshStandardMaterial({color:col(c), roughness:r == null ? 0.75 : r, metalness:0}); }
  function mesh(geo, m){ var x = new THREE.Mesh(geo, m); x.castShadow = true; return x; }
  function sphere(r, m){ return mesh(new THREE.SphereGeometry(r, 28, 20), m); }
  function capsule(r, len, m){
    var g = new THREE.Group();
    var c = mesh(new THREE.CylinderGeometry(r, r, len, 22), m); c.position.y = -len/2;
    var a = sphere(r, m), b = sphere(r, m); b.position.y = -len;
    g.add(c, a, b); return g;
  }
  function hairTexture(M){
    var hc = document.createElement('canvas'); hc.width = hc.height = 256;
    var hx = hc.getContext('2d'); if(!hx) return;
    hx.fillStyle = '#c8c8c8'; hx.fillRect(0, 0, 256, 256);
    var seed = 7; function rnd(){ seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    for(var i = 0; i < 900; i++){
      var g = 140 + Math.floor(rnd()*115), x0 = rnd()*256;
      hx.strokeStyle = 'rgb('+g+','+g+','+g+')'; hx.lineWidth = 1 + rnd()*2;
      hx.beginPath(); hx.moveTo(x0, rnd()*256); hx.lineTo(x0 + rnd()*10 - 5, rnd()*256); hx.stroke();
    }
    var ht = new THREE.CanvasTexture(hc);
    ht.wrapS = ht.wrapT = THREE.RepeatWrapping; ht.repeat.set(3, 1); ht.encoding = THREE.sRGBEncoding;
    M.hair.map = ht; M.hair.bumpMap = ht; M.hair.bumpScale = 0.006;
  }

  /* ---------------------------------------------------------------- characters */
  var MATS = {
    oldman: function(){ return {
      skin:mat(0xD9A882,0.7), skinDark:mat(0xC4916C,0.75), hair:mat(0xDCDCE2,0.6), line:mat(0xB07F5C,0.8),
      hoodie:mat(0x7A8F6A,0.9), hoodieDark:mat(0x5F7353,0.9), jeans:mat(0x6B5847,0.9),
      shoe:mat(0x4A3B30,0.6), sole:mat(0x2E2520,0.7), white:mat(0xFFFFFF,0.35),
      iris:mat(0x5A3A22,0.4), pupil:mat(0x17110F,0.3), lip:mat(0xB5645A,0.6), mouth:mat(0x4A1A1E,0.8)}; },
    hoodie: function(){ return {
      skin:mat(0xE3B08A,0.65), skinDark:mat(0xD09A74,0.7), hair:mat(0x5A4030,0.5),
      hoodie:mat(0xF7C24A,0.85), hoodieDark:mat(0xE5A52C,0.85), jeans:mat(0x3B5FA8,0.9),
      shoe:mat(0xF6F6F6,0.6), sole:mat(0xE2574C,0.7), white:mat(0xFFFFFF,0.35),
      iris:mat(0x5A3A22,0.4), pupil:mat(0x17110F,0.3), lip:mat(0xB5645A,0.6), mouth:mat(0x4A1A1E,0.8)}; },
    spiky: function(){ return {
      skin:mat(0xE3B08A,0.65), skinDark:mat(0xD09A74,0.7), hair:mat(0x40302A,0.45),
      hoodie:mat(0x26282E,0.5), hoodieDark:mat(0x16171B,0.5), zip:mat(0x9A9DA6,0.35), jeans:mat(0x3A3F4B,0.9),
      shoe:mat(0xF6F6F6,0.6), sole:mat(0x3B82C4,0.7), white:mat(0xFFFFFF,0.35),
      iris:mat(0x5A3A22,0.4), pupil:mat(0x17110F,0.3), lip:mat(0xB5645A,0.6), mouth:mat(0x4A1A1E,0.8)}; },
    woman: function(){ return {
      skin:mat(0xE8B890,0.6), skinDark:mat(0xD6A27A,0.7), hair:mat(0x4A3020,0.5), gold:mat(0xE8B84A,0.4),
      lash:mat(0x1E1614,0.5), lips:mat(0xD0566E,0.45),
      hoodie:mat(0xffffff,0.75), hoodieDark:mat(0x16807A,0.8), blouse:mat(0x1F7A5C,0.75), sari:mat(0xC62845,0.7),
      jeans:mat(0xB02040,0.9), shoe:mat(0xE8B84A,0.45), sole:mat(0x8A6A1F,0.7), white:mat(0xFFFFFF,0.35),
      iris:mat(0x6B4226,0.35), pupil:mat(0x17110F,0.3), lip:mat(0x8E2F45,0.6), mouth:mat(0x4A1A1E,0.8)}; }
  };

  function build(kind){
    var M = MATS[kind](); M.lip.side = THREE.DoubleSide;
    if(kind !== 'oldman') hairTexture(M);
    var rig = {kind:kind, J:{}, eyes:[], brows:[], headBias:0, spineBias:0, browBias:0, SK:null};
    var J = rig.J;
    var root = new THREE.Group(); root.position.y = 0.80; root.rotation.order = 'YXZ'; scene.add(root); rig.root = root;
    var woman = kind === 'woman';

    var pelvis = sphere(0.17, M.jeans);
    pelvis.scale.set(woman ? 0.95 : 1.12, 0.7, woman ? 0.75 : 0.85); pelvis.position.y = 0.02; root.add(pelvis);
    var spine = new THREE.Group(); root.add(spine); J.spine = spine;

    /* torso */
    if(kind === 'oldman'){
      var chest = capsule(0.17, 0.30, M.hoodie); chest.position.y = 0.42; chest.scale.set(1.2, 1, 0.96); spine.add(chest);
      var pocket = mesh(new THREE.BoxGeometry(0.2, 0.085, 0.03), M.hoodieDark); pocket.position.set(0, 0.13, 0.152); spine.add(pocket);
      var hood = mesh(new THREE.TorusGeometry(0.085, 0.04, 14, 28), M.hoodieDark);
      hood.rotation.x = Math.PI/2 - 0.25; hood.position.set(0, 0.485, -0.015); hood.scale.set(1.15, 1.1, 1); spine.add(hood);
      [0,1,2].forEach(function(i){ var d = sphere(0.013, M.hoodieDark); d.scale.z = 0.5; d.position.set(0, 0.37 - 0.075*i, 0.166); spine.add(d); });
      var neck = mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.12, 18), M.skinDark); neck.position.y = 0.51; spine.add(neck);
      rig.headBias = -0.07; rig.spineBias = 0.12;
    } else if(kind === 'hoodie' || kind === 'spiky'){
      var chest2 = capsule(0.17, 0.30, M.hoodie); chest2.position.y = 0.42; chest2.scale.set(1.2, 1, 0.85); spine.add(chest2);
      if(kind === 'hoodie'){
        var pocket2 = mesh(new THREE.BoxGeometry(0.2, 0.085, 0.03), M.hoodieDark); pocket2.position.set(0, 0.13, 0.135); spine.add(pocket2);
        [-1,1].forEach(function(s){ var d = sphere(0.012, M.white); d.position.set(0.03*s, 0.37, 0.148); spine.add(d); });
      } else {
        var tee = mesh(new THREE.BoxGeometry(0.07, 0.29, 0.02), M.shoe); tee.position.set(0, 0.275, 0.14); spine.add(tee);
        [-1,1].forEach(function(s){
          var z = mesh(new THREE.BoxGeometry(0.008, 0.29, 0.024), M.zip); z.position.set(0.039*s, 0.275, 0.14); spine.add(z);
          var pk = mesh(new THREE.BoxGeometry(0.07, 0.012, 0.02), M.hoodieDark); pk.position.set(0.11*s, 0.15, 0.125); pk.rotation.z = -0.25*s; spine.add(pk);
        });
      }
      var hood2 = mesh(new THREE.TorusGeometry(0.085, 0.04, 14, 28), M.hoodieDark);
      hood2.rotation.x = Math.PI/2 - 0.25; hood2.position.set(0, 0.485, -0.015); hood2.scale.set(1.15, 1.1, 1); spine.add(hood2);
      var neck2 = mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.12, 18), M.skinDark); neck2.position.y = 0.51; spine.add(neck2);
    } else {
      var prof = [[0.15,-0.09],[0.168,-0.02],[0.152,0.06],[0.118,0.16],[0.134,0.25],[0.15,0.33],[0.14,0.39],[0.09,0.44],[0.05,0.465]]
        .map(function(p){ return new THREE.Vector2(p[0], p[1]); });
      M.hoodie.side = THREE.DoubleSide;
      var chestG = new THREE.LatheGeometry(prof, 36);
      (function(){
        var p = chestG.attributes.position, c = new Float32Array(p.count*3), a = col(0x1F7A5C), b = col(0xC62845);
        for(var v = 0; v < p.count; v++){ var k = p.getY(v) > 0.2 ? a : b; c[v*3] = k.r; c[v*3+1] = k.g; c[v*3+2] = k.b; }
        chestG.setAttribute('color', new THREE.BufferAttribute(c, 3));
      })();
      M.hoodie.vertexColors = true;
      var chest3 = mesh(chestG, M.hoodie); chest3.scale.set(1.15, 1, 0.8); spine.add(chest3);
      var drape = new THREE.Group(); drape.position.set(0, 0.27, 0); drape.rotation.z = 0.75; spine.add(drape);
      var pallu = mesh(new THREE.TorusGeometry(0.175, 0.018, 10, 48), M.sari);
      pallu.rotation.x = Math.PI/2; pallu.scale.set(1.2, 0.82, 4.5); drape.add(pallu);
      var tail = mesh(new THREE.BoxGeometry(0.15, 0.42, 0.014), M.sari); tail.position.set(0.13, 0.2, -0.15); tail.rotation.z = -0.06; spine.add(tail);
      var tailEdge = mesh(new THREE.BoxGeometry(0.152, 0.035, 0.016), M.gold); tailEdge.position.set(0.142, -0.005, -0.15); tailEdge.rotation.z = -0.06; spine.add(tailEdge);
      var trim = mesh(new THREE.TorusGeometry(0.052, 0.008, 8, 28), M.gold); trim.rotation.x = Math.PI/2; trim.scale.set(1.15, 0.8, 1); trim.position.y = 0.465; spine.add(trim);
      var neck3 = mesh(new THREE.CylinderGeometry(0.04, 0.045, 0.12, 18), M.skin); neck3.position.y = 0.51; spine.add(neck3);
      rig.browBias = 0.08;
    }

    /* head */
    var RX = woman ? 0.15 : 0.156, RY = woman ? 0.185 : 0.19, RZ = 0.17;
    function faceZ(x, y){ return RZ*Math.sqrt(Math.max(0, 1 - (x*x)/(RX*RX) - (y*y)/(RY*RY))); }
    var head = new THREE.Group(); head.position.y = 0.69; spine.add(head); J.head = head;
    var skull = sphere(1, M.skin); skull.scale.set(RX, RY, RZ); head.add(skull);
    var jaw = sphere(woman ? 0.1 : 0.11, M.skin); jaw.position.set(0, woman ? -0.085 : -0.088, 0.02); jaw.scale.set(woman ? 1 : 1.05, 1, 1.05); head.add(jaw);

    if(kind === 'oldman'){
      var capO = mesh(new THREE.SphereGeometry(1, 36, 18, 0, Math.PI*2, 0, Math.PI*0.3), M.hair);
      capO.scale.set(RX*1.07, RY*1.07, RZ*1.1); capO.rotation.x = -0.95; head.add(capO);
      var backO = sphere(0.15, M.hair); backO.position.set(0, -0.01, -0.045); backO.scale.set(1.06, 1.1, 1.05); head.add(backO);
    } else if(kind === 'hoodie'){
      var capH = mesh(new THREE.SphereGeometry(1, 40, 28), M.hair);
      capH.scale.set(RX*1.12, RY*0.95, RZ*1.05); capH.position.set(0, 0.055, -0.035); head.add(capH);
      var fr = mesh(new THREE.SphereGeometry(1, 32, 20), M.hair);
      fr.scale.set(0.11, 0.045, 0.05); fr.position.set(0.02, 0.135, 0.085); fr.rotation.z = -0.2; head.add(fr);
      var backH = sphere(0.15, M.hair); backH.position.set(0, -0.01, -0.045); backH.scale.set(1.06, 1.1, 1.05); head.add(backH);
    } else if(kind === 'spiky'){
      var capS = mesh(new THREE.SphereGeometry(1, 40, 28), M.hair);
      capS.scale.set(RX*1.06, RY*0.9, RZ*1.03); capS.position.set(0, 0.05, -0.03); head.add(capS);
      var backS = sphere(0.15, M.hair); backS.position.set(0, -0.01, -0.04); backS.scale.set(1.02, 1.05, 1); head.add(backS);
      var up = new THREE.Vector3(0, 1, 0), rows = [[0,1],[0.42,6],[0.85,9],[1.25,11]], n = 0;
      rows.forEach(function(row){
        for(var i = 0; i < row[1]; i++){
          n++;
          var az = (i/row[1])*Math.PI*2 + row[0]*1.7, th = row[0];
          var dir = new THREE.Vector3(Math.sin(th)*Math.sin(az), Math.cos(th), Math.sin(th)*Math.cos(az));
          if(th > 1 && dir.z > 0.2 && Math.abs(dir.x) > 0.45) continue;
          var h = 0.085 + 0.035*Math.abs(Math.sin(n*12.9898)), r = 0.034 + 0.008*Math.abs(Math.sin(n*4.1));
          var g = new THREE.ConeGeometry(r, h, 10); g.translate(0, h/2, 0);
          var sp = mesh(g, M.hair);
          var p = new THREE.Vector3(dir.x*0.16, dir.y*0.165, dir.z*0.172);
          sp.position.set(p.x, p.y + 0.05, p.z - 0.03);
          var aim = dir.clone().add(new THREE.Vector3(Math.sin(n*7.3)*0.15, 0.55, 0.18)).normalize();
          sp.quaternion.setFromUnitVectors(up, aim);
          sp.position.addScaledVector(aim, -0.02);
          head.add(sp);
        }
      });
    } else {
      var capW = mesh(new THREE.SphereGeometry(1, 40, 28), M.hair);
      capW.scale.set(RX*1.13, RY*0.97, RZ*1.06); capW.position.set(0, 0.055, -0.035); head.add(capW);
      var backW = sphere(0.15, M.hair); backW.position.set(0, -0.01, -0.045); backW.scale.set(1.06, 1.1, 1.05); head.add(backW);
      var fall = mesh(new THREE.SphereGeometry(1, 32, 24), M.hair);
      fall.scale.set(RX*1.08, 0.27, 0.085); fall.position.set(0, -0.15, -0.115); head.add(fall);
      [-1,1].forEach(function(s){
        var lock = mesh(new THREE.SphereGeometry(1, 24, 20), M.hair);
        lock.scale.set(0.036, 0.17, 0.045); lock.position.set(0.152*s, -0.12, 0.015); lock.rotation.z = 0.05*s; head.add(lock);
      });
      var frW = mesh(new THREE.SphereGeometry(1, 32, 20), M.hair);
      frW.scale.set(0.115, 0.045, 0.05); frW.position.set(-0.02, 0.132, 0.082); frW.rotation.z = 0.22; head.add(frW);
    }

    /* eyes, brows, ears */
    [-1,1].forEach(function(s){
      var ear = sphere(woman ? 0.026 : 0.03, M.skinDark); ear.scale.set(0.5, 1, 0.7); ear.position.set(RX*s, -0.005, 0); head.add(ear);
      var ex = (woman ? 0.06 : 0.058)*s, ey = woman ? 0.016 : 0.02, ez = faceZ(ex, ey);
      var eye = new THREE.Group(); eye.position.set(ex, ey, ez - (woman ? 0.006 : 0.005));
      var w, ir, pu, gl;
      if(woman){
        eye.rotation.y = 0.3*s;
        w = mesh(new THREE.SphereGeometry(0.03, 24, 16), M.white); w.scale.set(1.25, 0.95, 0.4);
        ir = mesh(new THREE.SphereGeometry(0.018, 20, 14), M.iris); ir.scale.z = 0.4; ir.position.z = 0.0075;
        pu = mesh(new THREE.SphereGeometry(0.009, 16, 12), M.pupil); pu.scale.z = 0.4; pu.position.z = 0.012;
        gl = mesh(new THREE.SphereGeometry(0.0045, 10, 8), M.white); gl.position.set(0.007, 0.008, 0.016);
        var lash = new THREE.Mesh(new THREE.TorusGeometry(0.037, 0.0045, 6, 22, Math.PI), M.lash);
        lash.scale.y = 0.72; lash.position.set(0, 0.002, 0.006);
        var wing = mesh(new THREE.BoxGeometry(0.016, 0.005, 0.004), M.lash); wing.castShadow = false;
        wing.position.set(0.042*s, 0.008, 0.002); wing.rotation.z = 0.5*s;
        eye.add(lash, wing);
      } else {
        w = mesh(new THREE.SphereGeometry(0.028, 24, 16), M.white); w.scale.set(1.2, 0.75, 0.4);
        ir = mesh(new THREE.SphereGeometry(0.0135, 20, 14), M.iris); ir.scale.z = 0.4; ir.position.z = 0.0085;
        pu = mesh(new THREE.SphereGeometry(0.0065, 16, 12), M.pupil); pu.scale.z = 0.4; pu.position.z = 0.0125;
        gl = mesh(new THREE.SphereGeometry(0.003, 10, 8), M.white); gl.position.set(0.005, 0.005, 0.015);
      }
      [w, ir, pu, gl].forEach(function(x){ x.castShadow = false; });
      eye.add(w, ir, pu, gl); head.add(eye); rig.eyes.push(eye);

      var by = woman ? 0.072 : 0.064, brow;
      if(kind === 'oldman') brow = mesh(new THREE.BoxGeometry(0.062, 0.017, 0.015), M.hair);
      else if(woman) brow = mesh(new THREE.BoxGeometry(0.056, 0.007, 0.008), M.hair);
      else brow = mesh(new THREE.BoxGeometry(0.058, 0.011, 0.012), M.hair);
      brow.position.set(ex, by, faceZ(ex, by) + (woman ? 0.002 : 0.004));
      if(woman) brow.rotation.y = 0.3*s;
      brow.userData = {side:s, y:by}; brow.castShadow = false; head.add(brow); rig.brows.push(brow);
    });

    /* nose, mustache, wrinkles, mouth */
    if(kind === 'oldman'){
      var nose = sphere(0.026, M.skinDark); nose.scale.set(0.8, 1.25, 1); nose.position.set(0, -0.03, faceZ(0, -0.03) + 0.006); head.add(nose);
      [-1,1].forEach(function(s){
        var mu = sphere(0.02, M.hair); mu.castShadow = false;
        mu.scale.set(1.6, 0.6, 0.6); mu.rotation.z = -0.3*s;
        mu.position.set(0.024*s, -0.068, faceZ(0.024*s, -0.068) + 0.008); head.add(mu);
      });
      [0.1, 0.122].forEach(function(y){
        var wr = mesh(new THREE.BoxGeometry(0.055, 0.004, 0.006), M.line); wr.castShadow = false;
        wr.position.set(0, y, faceZ(0, y) - 0.001); head.add(wr);
      });
    } else if(woman){
      var noseW = sphere(0.016, M.skin); noseW.scale.set(0.8, 1.1, 0.9); noseW.position.set(0, -0.035, faceZ(0, -0.035) + 0.004); head.add(noseW);
    } else {
      var noseH = sphere(0.022, M.skinDark); noseH.scale.set(0.8, 1.25, 1); noseH.position.set(0, -0.03, faceZ(0, -0.03) + 0.006); head.add(noseH);
    }
    var mouthY = -0.094, mouthZ = faceZ(0, mouthY) + 0.004;
    var arcWrap = new THREE.Group(); arcWrap.position.set(0, mouthY, mouthZ);
    var arc = new THREE.Mesh(new THREE.TorusGeometry(0.036, 0.0065, 8, 24, Math.PI), M.lip);
    arc.rotation.z = Math.PI; arcWrap.add(arc); head.add(arcWrap); rig.arcWrap = arcWrap;
    var open = new THREE.Mesh(new THREE.SphereGeometry(0.028, 20, 14), M.mouth);
    open.position.set(0, mouthY - 0.012, mouthZ - 0.004); head.add(open); rig.open = open;
    if(woman){
      var lips = mesh(new THREE.SphereGeometry(0.02, 20, 14), M.lips); lips.castShadow = false;
      lips.scale.set(1.45, 0.55, 0.3); lips.position.set(0, mouthY - 0.012, mouthZ - 0.003); head.add(lips);
      var blushM = new THREE.MeshStandardMaterial({color:col(0xF07F96), roughness:0.9, transparent:true, opacity:0.38});
      [-1,1].forEach(function(s){
        var bl = new THREE.Mesh(new THREE.SphereGeometry(0.026, 18, 12), blushM);
        bl.scale.set(1, 0.7, 0.2); bl.position.set(0.088*s, -0.05, faceZ(0.088*s, -0.05) - 0.001); bl.rotation.y = 0.5*s; head.add(bl);
      });
    }

    /* arms */
    function arm(s){
      var sh = new THREE.Group(); sh.position.set((woman ? 0.215 : 0.25)*s, 0.40, 0); spine.add(sh);
      var el = new THREE.Group();
      if(woman){
        sh.add(capsule(0.048, 0.23, M.blouse));
        el.position.y = -0.23; sh.add(el);
        el.add(capsule(0.04, 0.2, M.skin));
        var cuffW = mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.03, 18), M.gold); cuffW.position.y = -0.005; el.add(cuffW);
        var bangle = mesh(new THREE.TorusGeometry(0.043, 0.007, 8, 20), M.gold); bangle.rotation.x = Math.PI/2; bangle.position.y = -0.185; el.add(bangle);
        var handW = sphere(0.048, M.skin); handW.scale.set(0.8, 1.1, 0.65); handW.position.y = -0.255; el.add(handW);
      } else {
        sh.add(capsule(0.058, 0.24, M.hoodie));
        el.position.y = -0.24; sh.add(el);
        el.add(capsule(0.052, 0.21, M.hoodie));
        var cuff = mesh(new THREE.CylinderGeometry(0.056, 0.056, 0.04, 18), M.hoodieDark); cuff.position.y = -0.21; el.add(cuff);
        var hand = sphere(0.058, M.skin); hand.scale.set(0.85, 1.1, 0.7); hand.position.y = -0.275; el.add(hand);
      }
      return {sh:sh, el:el};
    }
    if(woman) M.hoodie.vertexColors = true;
    J.armL = arm(1); J.armR = arm(-1);

    /* legs */
    function leg(s){
      var hip = new THREE.Group(); hip.position.set((woman ? 0.085 : 0.095)*s, 0, 0); root.add(hip);
      hip.add(capsule(woman ? 0.07 : 0.078, 0.36, M.jeans));
      var knee = new THREE.Group(); knee.position.y = -0.36; hip.add(knee);
      knee.add(capsule(woman ? 0.055 : 0.066, 0.34, M.jeans));
      var shoe = sphere(woman ? 0.062 : 0.07, M.shoe);
      if(woman){ shoe.scale.set(0.95, 0.55, 1.75); shoe.position.set(0, -0.39, 0.04); }
      else { shoe.scale.set(1, 0.62, 1.9); shoe.position.set(0, -0.385, 0.05); }
      knee.add(shoe);
      var sole = woman ? mesh(new THREE.BoxGeometry(0.1, 0.02, 0.2), M.sole) : mesh(new THREE.BoxGeometry(0.125, 0.025, 0.25), M.sole);
      sole.position.set(0, -0.425, woman ? 0.04 : 0.05); knee.add(sole);
      return {hip:hip, knee:knee};
    }
    J.legL = leg(1); J.legR = leg(-1);
    if(woman) rig.SK = buildSkirt(root);

    /* props held in the right hand (shown for phone, tea, book and snack actions) */
    var handY = woman ? -0.255 : -0.275, P = {};
    P.phone = new THREE.Group();
    var ph = mesh(new THREE.BoxGeometry(0.085, 0.17, 0.014), mat(0x2e323e, 0.3));      /* real-sized phone */
    var scr = new THREE.Mesh(new THREE.PlaneGeometry(0.077, 0.16), new THREE.MeshBasicMaterial({color:col(0x7fc8f5)}));
    scr.position.z = 0.0075; ph.add(scr);
    var camMod = mesh(new THREE.BoxGeometry(0.03, 0.034, 0.006), mat(0x15171d, 0.3));
    camMod.position.set(-0.022, 0.058, -0.009); ph.add(camMod);
    [[-0.028, 0.066], [-0.028, 0.05], [-0.016, 0.058]].forEach(function(q){
      var lens = new THREE.Mesh(new THREE.CylinderGeometry(0.0055, 0.0055, 0.004, 14), mat(0x050608, 0.1));
      lens.rotation.x = Math.PI/2; lens.position.set(q[0], q[1], -0.0125); ph.add(lens);
    });
    P.phone.add(ph);
    P.cup = new THREE.Group();
    var cup = mesh(new THREE.CylinderGeometry(0.032, 0.026, 0.07, 20), mat(0xf4f1ea, 0.4));
    var tea = new THREE.Mesh(new THREE.CircleGeometry(0.029, 20), mat(0xa8683a, 0.5)); tea.rotation.x = -Math.PI/2; tea.position.y = 0.03;
    var handle = mesh(new THREE.TorusGeometry(0.018, 0.005, 8, 16), mat(0xf4f1ea, 0.4)); handle.position.x = 0.035;
    P.cup.add(cup, tea, handle);
    P.book = new THREE.Group();
    var cover = mesh(new THREE.BoxGeometry(0.17, 0.22, 0.025), mat(0xc0392b, 0.6));
    var pages = mesh(new THREE.BoxGeometry(0.16, 0.21, 0.02), mat(0xfaf6ea, 0.8)); pages.position.z = 0.004;
    P.book.add(cover, pages);
    P.snack = mesh(new THREE.SphereGeometry(0.035, 16, 12), mat(0xe8b54a, 0.6));
    for(var pk in P){
      P[pk].position.set(0, handY - 0.03, 0.06); P[pk].visible = false; J.armR.el.add(P[pk]);
    }
    P.book.position.set(-0.06, handY - 0.02, 0.09); P.book.rotation.x = -Math.PI/2;
    rig.props = P;

    /* face effects: tears, sweat drop, anger mark, blush */
    var FX = {tears:[], sweat:null, anger:null, blush:[]};
    var tearM = new THREE.MeshStandardMaterial({color:col(0x6fc3f7), roughness:0.15, transparent:true, opacity:0.9});
    [-1,1].forEach(function(s){
      for(var i = 0; i < 2; i++){
        var tdrop = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 10), tearM); tdrop.scale.y = 1.4;
        tdrop.userData = {side:s, i:i}; tdrop.visible = false; head.add(tdrop); FX.tears.push(tdrop);
      }
    });
    FX.faceZ = faceZ; FX.eyeX = woman ? 0.06 : 0.058; FX.eyeY = woman ? 0.016 : 0.02;
    var sw = new THREE.Group();
    var swb = new THREE.Mesh(new THREE.SphereGeometry(0.02, 14, 12), tearM);
    var swt = new THREE.Mesh(new THREE.ConeGeometry(0.0195, 0.035, 14), tearM); swt.position.y = 0.024;
    sw.add(swb, swt); sw.position.set(RX*0.92, 0.1, 0.06); sw.visible = false; head.add(sw); FX.sweat = sw;
    var ang = new THREE.Group(), angM = new THREE.MeshBasicMaterial({color:col(0xe53935)});
    [[1,1],[1,-1],[-1,1],[-1,-1]].forEach(function(q){
      var bar = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.009, 0.004), angM);
      bar.position.set(q[0]*0.016, q[1]*0.016, 0); bar.rotation.z = q[0]*q[1] > 0 ? 0.6 : -0.6; ang.add(bar);
    });
    ang.position.set(RX*0.5, 0.105, faceZ(RX*0.5, 0.105) + 0.025); ang.visible = false; head.add(ang); FX.anger = ang;
    var blM = new THREE.MeshStandardMaterial({color:col(0xf06292), roughness:0.9, transparent:true, opacity:0.55});
    [-1,1].forEach(function(s){
      var bl = new THREE.Mesh(new THREE.SphereGeometry(0.027, 16, 10), blM);
      bl.scale.set(1.1, 0.6, 0.2); bl.position.set(0.09*s, -0.045, faceZ(0.09*s, -0.045)); bl.rotation.y = 0.5*s;
      bl.visible = false; head.add(bl); FX.blush.push(bl);
    });
    rig.fx = FX;
    return rig;
  }

  /* ---------------------------------------------------------------- sari skirt (follows the legs) */
  function buildSkirt(root){
    var SK = {rings:26, seg:48};
    var prof = [[0.118,0.14],[0.15,0.06],[0.17,-0.02],[0.17,-0.36],[0.19,-0.74]], pts = [];
    for(var i = 0; i <= SK.rings; i++){
      var y = 0.14 - 0.88*i/SK.rings, r = prof[prof.length-1][0];
      for(var k = 0; k < prof.length-1; k++){
        var a = prof[k], b = prof[k+1];
        if(y <= a[1] + 1e-9 && y >= b[1] - 1e-9){ r = a[0] + (b[0] - a[0])*(a[1] - y)/(a[1] - b[1]); break; }
      }
      pts.push(new THREE.Vector2(r, y));
    }
    var g = new THREE.LatheGeometry(pts, SK.seg, Math.PI, Math.PI*2);
    var pos = g.attributes.position, n = pos.count;
    var base = new Float32Array(n*3), cols = new Float32Array(n*3), wt = new Float32Array(n);
    var cS = col(0xC62845), cD = col(0x9C1B36), cG = col(0xE8B84A);
    for(var v = 0; v < n; v++){
      var xn = pos.getX(v), y2 = pos.getY(v), zn = pos.getZ(v), x = xn*1.1, z = zn*0.85;
      base[v*3] = x; base[v*3+1] = y2; base[v*3+2] = z;
      wt[v] = 0.5 + 0.5*zn/(Math.sqrt(xn*xn + zn*zn) || 1);
      var c = cS;
      if(z > 0 && Math.abs(x) < 0.075 && Math.floor(v/(SK.rings+1)) % 2 === 0 && y2 < 0.1) c = cD;
      if(y2 < -0.67) c = cG;
      cols[v*3] = c.r; cols[v*3+1] = c.g; cols[v*3+2] = c.b;
    }
    g.setAttribute('color', new THREE.BufferAttribute(cols, 3));
    SK.mesh = mesh(g, new THREE.MeshStandardMaterial({vertexColors:true, roughness:0.7, side:THREE.DoubleSide}));
    SK.mesh.frustumCulled = false; SK.base = base; SK.w = wt; SK.pos = pos; root.add(SK.mesh);
    return SK;
  }
  function sstep(a, b, x){ var t = Math.min(1, Math.max(0, (x - a)/(b - a))); return t*t*(3 - 2*t); }
  function legPt(d, th, tk, oz, out){
    var L = 0.36, ay, az;
    if(d <= 0){ ay = -d; az = 0; }
    else if(d <= L){ ay = -d*Math.cos(th); az = -d*Math.sin(th); }
    else { var t2 = th + tk, e = d - L; ay = -L*Math.cos(th) - e*Math.cos(t2); az = -L*Math.sin(th) - e*Math.sin(t2); }
    var a = th*sstep(0, 0.08, d) + tk*sstep(0.3, 0.42, d);
    out.y = ay - oz*Math.sin(a); out.z = az + oz*Math.cos(a);
  }
  var pa = {y:0,z:0}, pb = {y:0,z:0}, qa = {y:0,z:0}, qb = {y:0,z:0};
  function skirt(SK, cur){
    var b = SK.base, p = SK.pos, n = p.count;
    for(var v = 0; v < n; v++){
      var x = b[v*3], d = -b[v*3+1], z = b[v*3+2];
      legPt(d, cur.hipLx, cur.kneeLx, z, pa); legPt(d, cur.hipRx, cur.kneeRx, z, pb);
      legPt(d, cur.hipLx, cur.kneeLx, 0, qa); legPt(d, cur.hipRx, cur.kneeRx, 0, qb);
      var f = qa.z >= qb.z ? pa : pb, k = qa.z >= qb.z ? pb : pa, w = SK.w[v];
      p.setXYZ(v, x, k.y + (f.y - k.y)*w, k.z + (f.z - k.z)*w);
    }
    p.needsUpdate = true; SK.mesh.geometry.computeVertexNormals();
  }

  /* ---------------------------------------------------------------- poses */
  var MOODS = {
    happy:{curve:1,browTilt:0,browY:0.004,eyeOpen:1,mouthOpen:0,headX:0},
    neutral:{curve:0.12,browTilt:0,browY:0,eyeOpen:1,mouthOpen:0,headX:0},
    sad:{curve:-0.85,browTilt:-0.38,browY:0.002,eyeOpen:0.78,mouthOpen:0,headX:0.16},
    surprised:{curve:0.1,browTilt:0,browY:0.022,eyeOpen:1.28,mouthOpen:0.85,headX:-0.05},
    laughing:{curve:1,browTilt:-0.1,browY:0.008,eyeOpen:0.3,mouthOpen:0.5,headX:-0.06},
    sleepy:{curve:0.12,browTilt:-0.15,browY:-0.004,eyeOpen:0.12,mouthOpen:0,headX:0.12},
    worried:{curve:-0.35,browTilt:-0.32,browY:0.006,eyeOpen:1,mouthOpen:0,headX:0.06,fx:['sweat']},
    scared:{curve:-0.45,browTilt:-0.45,browY:0.016,eyeOpen:1.25,mouthOpen:0.35,headX:0.04,fx:['sweat']},
    crying:{curve:-0.9,browTilt:-0.45,browY:0.004,eyeOpen:0.3,mouthOpen:0.25,headX:0.18,fx:['tears']},
    embarrassed:{curve:0.45,browTilt:-0.2,browY:0.004,eyeOpen:0.75,mouthOpen:0,headX:0.14,fx:['blush','sweat']},
    confused:{curve:-0.12,browTilt:0.22,browY:0.008,eyeOpen:1,mouthOpen:0,headX:0,headZ:0.16},
    in_love:{curve:1,browTilt:-0.1,browY:0.01,eyeOpen:0.55,mouthOpen:0,headX:0.04,headZ:-0.08,fx:['blush']},
    thinking:{curve:0,browTilt:0.15,browY:0.006,eyeOpen:0.9,mouthOpen:0,headX:-0.1,headZ:0.1},
    disgusted:{curve:-0.7,browTilt:0.35,browY:-0.008,eyeOpen:0.6,mouthOpen:0.1,headX:0.02,headZ:-0.06},
    excited:{curve:1,browTilt:0,browY:0.02,eyeOpen:1.2,mouthOpen:0.4,headX:-0.04},
    proud:{curve:0.8,browTilt:0.05,browY:0.002,eyeOpen:0.7,mouthOpen:0,headX:-0.12},
    bored:{curve:-0.1,browTilt:-0.05,browY:-0.004,eyeOpen:0.55,mouthOpen:0,headX:0.1},
    angry:{curve:-0.6,browTilt:0.48,browY:-0.012,eyeOpen:0.72,mouthOpen:0,headX:0.04,fx:['anger']}
  };
  var KEYS = ['shLx','shLz','elLx','elLz','shRx','shRz','elRx','elRz','hipLx','kneeLx','hipRx','kneeRx',
              'headX','headY','headZ','bodyY','spineX','spineY','shRy','rootX','rootY','mouthOpen','curve','browTilt','browY','eyeOpen'];

  function pose(t, action, mood, mouth){
    var m = MOODS[mood] || MOODS.neutral, tg = {}, s = Math.sin, k;
    for(k = 0; k < KEYS.length; k++) tg[KEYS[k]] = 0;
    tg.shLz = 0.1; tg.shRz = -0.1;
    tg.curve = m.curve; tg.browTilt = m.browTilt; tg.browY = m.browY; tg.eyeOpen = m.eyeOpen;
    tg.mouthOpen = m.mouthOpen; tg.headX = m.headX; tg.headZ = m.headZ || 0;
    if(mood === 'laughing') tg.mouthOpen = 0.35 + 0.3*Math.abs(s(t*11));
    tg.bodyY = s(t*1.6)*0.004;
    tg.headY = s(t*0.5)*0.08;
    tg.shLx = s(t*1.2)*0.03; tg.shRx = -s(t*1.2)*0.03;
    var sitting = action.indexOf('sit') === 0 && action !== 'sit_sleep';

    if(action === 'wave'){
      tg.shRz = -2.5; tg.elRz = -0.5 + s(t*9)*0.45; tg.headZ = -0.08; tg.headY = 0;
    } else if(action === 'walk'){
      var p = t*5;
      tg.hipLx = -s(p)*0.45; tg.hipRx = s(p)*0.45;
      tg.kneeLx = Math.max(0, Math.cos(p))*0.85 + 0.05; tg.kneeRx = Math.max(0, -Math.cos(p))*0.85 + 0.05;
      tg.shLx = s(p)*0.4; tg.shRx = -s(p)*0.4; tg.elLx = -0.35; tg.elRx = -0.35;
      tg.bodyY = Math.abs(s(p))*0.016; tg.spineX = 0.05; tg.headY = 0;
    } else if(action === 'punch'){
      var q = (t*2.4) % 1;
      tg.hipLx = -0.25; tg.kneeLx = 0.3; tg.hipRx = 0.2; tg.kneeRx = 0.25; tg.bodyY = -0.02;
      tg.shLx = -0.7; tg.elLx = -1.9; tg.headY = 0;
      if(q < 0.4){ tg.shRx = -1.5; tg.elRx = -0.05; tg.spineY = 0.35; } else { tg.shRx = -0.7; tg.elRx = -1.9; tg.spineY = -0.1; }
    } else if(action === 'slap'){
      var sl = (t*1.3) % 1;
      tg.shRx = 0; tg.shRz = -1.45; tg.headY = 0;
      if(sl < 0.45){ tg.shRy = -0.5; tg.spineY = -0.3; } else { tg.shRy = 1.9; tg.spineY = 0.4; }
    } else if(action === 'sit' || sitting){
      tg.bodyY = -0.34 + s(t*1.6)*0.003;
      tg.hipLx = -1.5; tg.hipRx = -1.5; tg.kneeLx = 1.5; tg.kneeRx = 1.5;
      tg.shLx = -0.55; tg.shRx = -0.55; tg.elLx = -0.5; tg.elRx = -0.5; tg.shLz = 0.12; tg.shRz = -0.12;
      if(action === 'sit_phone' || action === 'sit_read'){ tg.elLx = tg.elRx = -1.2; tg.headX = 0.25; }
      if(action === 'sit_tea' || action === 'sit_eat'){ tg.elRx = -1.4 - 0.9*Math.pow(0.5 + 0.5*s(t*1.3), 6); }
    } else if(action === 'sleep' || action === 'sit_sleep'){
      tg.bodyY = -0.61; tg.rootX = -Math.PI/2; tg.rootY = 0.9;
      tg.shLx = 0; tg.shRx = 0; tg.shLz = 0.25; tg.shRz = -0.25;
      tg.headX = 0; tg.headY = 0; tg.browTilt = 0; tg.browY = 0; tg.curve = 0.12;
      tg.eyeOpen = 0.05; tg.mouthOpen = 0.1 + 0.08*(s(t*1.4) + 1);
    } else if(action === 'talk'){
      tg.shLx = -0.35; tg.shLz = 0.18; tg.elLx = -1.3 + s(t*3)*0.16;
      tg.headX = m.headX + s(t*2.2)*0.05; tg.headY = s(t*1.1)*0.1;
    } else if(action === 'point'){
      tg.shRx = -1.25; tg.shRz = -0.55; tg.elRx = -0.1 + 0.08*s(t*5); tg.headY = 0;
      tg.shLx = -0.35; tg.shLz = 0.18; tg.elLx = -1.3;
    } else if(action === 'cheer' || action === 'jump' || action === 'dance'){
      tg.shLz = 2.6 + 0.15*s(t*7); tg.shRz = -2.6 + 0.15*s(t*7); tg.elLz = 0.3; tg.elRz = -0.3;
      if(action === 'jump') tg.bodyY = Math.abs(s(t*4.5))*0.22;
      if(action === 'dance'){ tg.rootY = 0.35*s(t*3); tg.bodyY = Math.abs(s(t*6))*0.03; tg.hipLx = 0.2*s(t*6); tg.hipRx = -0.2*s(t*6); }
    } else if(action === 'think'){
      tg.shRx = -0.85; tg.shRz = 0.3; tg.elRx = -2.2; tg.headX = 0.06; tg.headZ = 0.08; tg.headY = 0.15;
      tg.shLx = -0.4; tg.elLx = -1.4; tg.elLz = -0.6;
    } else if(action === 'facepalm'){
      tg.shRx = -1.3; tg.shRz = 0.35; tg.elRx = -2.3; tg.headX = 0.18; tg.headY = 0;
    } else if(action === 'explain'){
      var e = 0.2*s(t*4.5);
      tg.shLx = tg.shRx = -0.7; tg.shLz = 0.35; tg.shRz = -0.35; tg.elLx = -0.9 + e; tg.elRx = -0.9 - e;
    } else if(action === 'clap'){
      var c = 0.15*Math.abs(s(t*9));
      tg.shLx = tg.shRx = -1.15; tg.shLz = -0.3 + c; tg.shRz = 0.3 - c; tg.elLx = tg.elRx = -0.5;
    } else if(action === 'shrug'){
      tg.shLz = 0.55; tg.shRz = -0.55; tg.elLx = tg.elRx = -1.5; tg.headZ = 0.12*s(t*3);
    } else if(action === 'arms_crossed'){
      tg.shLx = tg.shRx = -0.55; tg.elLx = tg.elRx = -1.8; tg.elLz = -1.1; tg.elRz = 1.1;
    } else if(action === 'stop'){
      tg.shRx = -1.45; tg.shRz = -0.15; tg.elRx = -1.25;
    } else if(action === 'thumbs_up' || action === 'ok_sign'){
      tg.shRx = -0.9; tg.elRx = -1.3; tg.shRz = -0.2;
    } else if(action === 'wipe_tears'){
      tg.shRx = -1.3; tg.shRz = 0.35; tg.elRx = -2.3 + 0.12*s(t*9); tg.headX = 0.15;
    } else if(action === 'hold_parcel'){
      tg.shLx = tg.shRx = -0.6; tg.elLx = tg.elRx = -1.0; tg.shLz = -0.15; tg.shRz = 0.15;
    } else if(action === 'hide_behind'){
      tg.shLx = tg.shRx = 0.55; tg.elLx = tg.elRx = -0.4; tg.shLz = 0.05; tg.shRz = -0.05; tg.headY = 0.2*s(t*3);
    } else if(action === 'throw'){
      if(t < 0.5){ tg.shRz = -2.6; tg.elRz = -0.8; tg.spineY = 0.3; } else { tg.shRx = -1.4; tg.shRz = -0.2; tg.spineY = -0.3; }
    } else if(action === 'look_around'){
      tg.headY = 0.55*s(t*1.6);
    } else if(action === 'phone_call'){
      tg.shRx = -0.55; tg.shRz = 0.2; tg.elRx = -2.55; tg.headZ = -0.08;
    } else if(action === 'use_phone' || action === 'read_book'){
      tg.shLx = tg.shRx = -0.45; tg.elLx = tg.elRx = -1.35; tg.headX = 0.25; tg.headY = 0;
    } else if(action === 'drink_tea' || action === 'eat'){
      tg.shRx = -0.45; tg.elRx = -1.4 - 0.9*Math.pow(0.5 + 0.5*s(t*1.3), 6);
    }
    if(mouth != null && action !== 'sleep' && action !== 'sit_sleep') tg.mouthOpen = Math.max(mood === 'surprised' ? 0.3 : 0, mouth);
    return tg;
  }

  function apply(rig, cur, blinkMul, rotY){
    var J = rig.J;
    J.armL.sh.rotation.set(cur.shLx, 0, cur.shLz); J.armL.el.rotation.set(cur.elLx, 0, cur.elLz);
    J.armR.sh.rotation.set(cur.shRx, cur.shRy, cur.shRz); J.armR.el.rotation.set(cur.elRx, 0, cur.elRz);
    J.legL.hip.rotation.x = cur.hipLx; J.legL.knee.rotation.x = cur.kneeLx;
    J.legR.hip.rotation.x = cur.hipRx; J.legR.knee.rotation.x = cur.kneeRx;
    J.head.rotation.set(cur.headX + rig.headBias, cur.headY, cur.headZ);
    J.spine.rotation.set(cur.spineX + rig.spineBias, cur.spineY, 0);
    rig.root.rotation.set(cur.rootX, cur.rootY + rotY, 0);
    rig.root.position.y = 0.80 + cur.bodyY;
    if(rig.SK) skirt(rig.SK, cur);
    rig.eyes.forEach(function(e){ e.scale.y = Math.max(0.05, cur.eyeOpen*blinkMul); });
    rig.brows.forEach(function(b){
      b.rotation.z = (cur.browTilt + rig.browBias)*b.userData.side;
      b.position.y = b.userData.y + cur.browY;
    });
    var c = cur.curve*0.6;
    if(Math.abs(c) < 0.06) c = c < 0 ? -0.06 : 0.06;
    rig.arcWrap.scale.y = c;
    var o = cur.mouthOpen;
    rig.open.visible = o > 0.04;
    rig.open.scale.set(0.9 + o*0.25, Math.max(0.05, o*0.85), 0.3);
  }

  var PROP_FOR = {use_phone:'phone', phone_call:'phone', sit_phone:'phone', drink_tea:'cup', sit_tea:'cup',
                  read_book:'book', sit_read:'book', eat:'snack', sit_eat:'snack'};
  function effects(rig, action, m, t){
    var want = PROP_FOR[action];
    for(var k in rig.props) rig.props[k].visible = (k === want);
    rig.props.phone.rotation.x = (action === 'use_phone' || action === 'sit_phone') ? Math.PI/2 : 0;   // look at the screen
    var on = {}; (m.fx || []).forEach(function(f){ on[f] = true; });
    var F = rig.fx;
    F.tears.forEach(function(d){
      d.visible = !!on.tears;
      if(!d.visible) return;
      var u = (t*0.9 + d.userData.i*0.5 + (d.userData.side > 0 ? 0.25 : 0)) % 1;
      var x = d.userData.side*(F.eyeX + 0.004 + 0.012*u), y = F.eyeY - 0.03 - 0.13*u;
      d.position.set(x, y, F.faceZ(x, y) + 0.008);
      d.material.opacity = 0.9*(1 - u*u);
    });
    F.sweat.visible = !!on.sweat; F.sweat.position.y = 0.1 - 0.012*((t*0.7) % 1);
    F.anger.visible = !!on.anger; F.anger.scale.setScalar(1 + 0.15*Math.sin(t*12));
    F.blush.forEach(function(b){ b.visible = !!on.blush; });
  }

  /* ---------------------------------------------------------------- render one picture
     o = {kind, action, mood, t, mouth, blink (0 open .. 1 shut), rotY, ppu (pixels per unit), below (pixels from feet to
     frame bottom, or null)}. Returns {png, w, h, ax, ay}: a transparent PNG and the pixel position of the feet. */
  var HW = 1.15, TOP = 1.25, BOT = 1.0;
  function render(o){
    if(!renderer) init();
    if(!CH[o.kind]) CH[o.kind] = build(o.kind);
    for(var k in CH) CH[k].root.visible = (k === o.kind);
    var rig = CH[o.kind];
    var cur = pose(o.t, o.action, o.mood, o.mouth);
    apply(rig, cur, 1 - 0.88*(o.blink || 0), o.rotY || 0);
    effects(rig, o.action, MOODS[o.mood] || MOODS.neutral, o.t);
    stool.visible = o.action === 'sit' || (o.action.indexOf('sit_') === 0 && o.action !== 'sit_sleep');

    var target = new THREE.Vector3(0, TARGET_Y, 0);
    camera.position.set(0, TARGET_Y + 10*Math.cos(PHI), 10*Math.sin(PHI));
    camera.lookAt(target);
    camera.updateMatrixWorld();
    var feet = new THREE.Vector3(0, 0, 0).applyMatrix4(camera.matrixWorldInverse);
    var bot = BOT;
    if(o.below != null) bot = Math.max(-TOP + 0.2, Math.min(BOT, -feet.y + o.below/o.ppu + 0.03));
    var W = Math.max(8, Math.min(4096, Math.round(2*HW*o.ppu)));
    var H = Math.max(8, Math.min(4096, Math.round((TOP + bot)*o.ppu)));
    camera.left = -HW; camera.right = HW; camera.top = TOP; camera.bottom = -bot;
    camera.updateProjectionMatrix();
    renderer.setSize(W, H, false);
    renderer.render(scene, camera);
    var ax = (feet.x + HW)/(2*HW)*W, ay = (TOP - feet.y)/(TOP + bot)*H;
    return {png: renderer.domElement.toDataURL('image/png'), w: W, h: H, ax: ax, ay: ay};
  }

  window.R3 = {render: render, kinds: Object.keys(MATS)};
})();
