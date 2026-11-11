/* Scroll reveal, a brass cursor, golden liquid-glass light, and an occasional shooting star.
   If this file does not run, the page stays visible.
   Reduced motion and coarse pointers never get the cursor or the pointer effects. */
(function () {
  var reduce = false;
  var fine = false;
  try {
    reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    fine = window.matchMedia("(any-pointer: fine)").matches || window.matchMedia("(any-hover: hover)").matches;
  } catch (err) {
    reduce = false;
    fine = false;
  }
  if (reduce) return;

  var hero = document.querySelector(".hero");
  setupReveal();
  if (hero) {
    setupSky(hero);
    setupReplay(hero);
  }
  setupDepth();
  if (fine) setupPointer(hero);

  function setupReveal() {
    if (!("IntersectionObserver" in window)) return;
    var nodes = document.querySelectorAll(".reveal");
    if (!nodes.length) return;

    var pending = [];
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var parent = node.parentElement;
      var order = 0;
      if (parent) {
        for (var c = 0; c < parent.children.length; c++) {
          var child = parent.children[c];
          if (!child.classList || !child.classList.contains("reveal")) continue;
          if (child === node) break;
          order += 1;
        }
      }
      node.style.setProperty("--reveal-delay", Math.min(order, 4) * 80 + "ms");
      var rect = node.getBoundingClientRect();
      if (rect.bottom > 0 && rect.top < window.innerHeight * 0.92) {
        node.classList.add("is-in");
      } else {
        pending.push(node);
      }
    }

    if (pending.length) {
      var io = new IntersectionObserver(function (entries) {
        for (var j = 0; j < entries.length; j++) {
          if (!entries[j].isIntersecting) continue;
          entries[j].target.classList.add("is-in");
          io.unobserve(entries[j].target);
        }
      }, { rootMargin: "0px 0px -6% 0px", threshold: 0.16 });
      for (var k = 0; k < pending.length; k++) io.observe(pending[k]);
    }

    document.documentElement.classList.add("reveal-ready");
  }

  function setupDepth() {
    var hosts = document.querySelectorAll(".hero, .band");
    var cubes = [];
    for (var i = 0; i < hosts.length; i++) {
      var depth = document.createElement("div");
      depth.className = "depth";
      depth.setAttribute("aria-hidden", "true");
      var cube = document.createElement("div");
      cube.className = "depth-cube";
      for (var face = 0; face < 6; face++) cube.appendChild(document.createElement("span"));
      depth.appendChild(cube);
      hosts[i].appendChild(depth);
      cubes.push(cube);
    }
    document.addEventListener("visibilitychange", function () {
      var state = document.hidden ? "paused" : "running";
      for (var c = 0; c < cubes.length; c++) cubes[c].style.animationPlayState = state;
    });
  }

  function spawnStar(host) {
    var star = document.createElement("span");
    star.className = "star";
    star.setAttribute("aria-hidden", "true");
    star.style.top = (4 + Math.random() * 18) + "%";
    star.style.setProperty("--star-angle", (-12 - Math.random() * 14) + "deg");
    star.style.setProperty("--star-from", (2 + Math.random() * 8) + "vh");
    star.style.setProperty("--star-mid", (10 + Math.random() * 8) + "vh");
    star.style.setProperty("--star-to", (-4 + Math.random() * 8) + "vh");
    host.appendChild(star);
    star.addEventListener("animationend", function () {
      if (star.parentNode) star.parentNode.removeChild(star);
    });
  }

  function setupSky(host) {
    window.setTimeout(function () { spawnStar(host); }, 1100);
    function later() {
      var wait = 8000 + Math.random() * 8000;
      window.setTimeout(function () {
        spawnStar(host);
        later();
      }, wait);
    }
    later();
  }

  function setupReplay(host) {
    var button = host.querySelector(".replay");
    if (!button) return;
    document.documentElement.classList.add("has-motion");
    button.addEventListener("click", function () {
      var anims = host.getAnimations({ subtree: true });
      for (var i = 0; i < anims.length; i++) {
        var anim = anims[i];
        if (anim.timeline && anim.timeline !== document.timeline) continue;
        try {
          anim.currentTime = 0;
          anim.play();
        } catch (err) {
          continue;
        }
      }
      spawnStar(host);
    });
  }

  function createGlass() {
    var canvas = document.createElement("canvas");
    canvas.className = "glass";
    canvas.setAttribute("aria-hidden", "true");
    var gl = canvas.getContext("webgl", {
      alpha: true,
      premultipliedAlpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: "low-power"
    });
    var gpu = gl ? linkGlass(gl) : null;
    if (!gpu) gl = null;
    var cpu = gl ? null : canvas.getContext("2d", { alpha: true });
    var host = null;
    var face = false;
    var quiet = 0;
    var rect = null;
    var px = 0;
    var py = 0;
    var targetX = 0.5;
    var targetY = 0.5;
    var bodyX = 0.5;
    var bodyY = 0.5;
    var specX = 0.5;
    var specY = 0.5;
    var sheenX = 0.5;
    var sheenY = 0.5;
    var sheenVx = 0;
    var sheenVy = 0;
    var want = 0;
    var strength = 0;
    var time = 0;
    var sizedW = 0;
    var sizedH = 0;

    function place(next, clientX, clientY) {
      px = clientX;
      py = clientY;
      if (next === host) {
        want = host ? 1 : 0;
        return;
      }
      if (!next) {
        want = 0;
        return;
      }
      if (host && canvas.parentNode === host) host.removeChild(canvas);
      host = next;
      face = host.classList.contains("portrait-frame");
      quiet = host.matches(".portrait-frame, .photo-frame, .still-media") ? 1 : 0;
      var media = host.matches(".photo-frame, .still-media, .portrait-frame");
      var light = host.matches(".logo-chip:not(.on-dark), .chips li, .tagline li, .plate, .press-card, .cover, .school, .cert, .honor, .note, .talk, .quote, .seal, .role, .company, .timeline li, summary");
      canvas.classList.toggle("is-over", media);
      canvas.classList.toggle("is-face", face);
      canvas.classList.toggle("is-light", !media && light);
      host.appendChild(canvas);
      var box = host.getBoundingClientRect();
      var enter = local(box, clientX, clientY);
      targetX = bodyX = specX = sheenX = enter.x;
      targetY = bodyY = specY = sheenY = enter.y;
      sheenVx = 0;
      sheenVy = 0;
      rect = box;
      sizedW = 0;
      sizedH = 0;
      want = 1;
    }

    function leave() {
      want = 0;
    }

    function local(box, clientX, clientY) {
      var x = box.width ? (clientX - box.left) / box.width : 0.5;
      var y = box.height ? (clientY - box.top) / box.height : 0.5;
      if (x < 0) x = 0;
      if (x > 1) x = 1;
      if (y < 0) y = 0;
      if (y > 1) y = 1;
      return { x: x, y: y };
    }

    function resize(box) {
      var maxEdge = gl ? 440 : 180;
      var scale = Math.min(1.15, maxEdge / Math.max(box.width, box.height, 1));
      var w = Math.max(2, Math.round(box.width * scale));
      var h = Math.max(2, Math.round(box.height * scale));
      if (w === sizedW && h === sizedH) return;
      sizedW = w;
      sizedH = h;
      canvas.width = w;
      canvas.height = h;
      if (gl) gl.viewport(0, 0, w, h);
    }

    function step(dt) {
      if (host && want) {
        rect = host.getBoundingClientRect();
        if (rect.width > 1 && rect.height > 1) {
          var point = local(rect, px, py);
          targetX = point.x;
          targetY = point.y;
          resize(rect);
        }
      }
      var follow = 1 - Math.exp(-7 * dt);
      var snap = 1 - Math.exp(-18 * dt);
      bodyX += (targetX - bodyX) * follow;
      bodyY += (targetY - bodyY) * follow;
      specX += (targetX - specX) * snap;
      specY += (targetY - specY) * snap;
      sheenVx += ((targetX - sheenX) * 34 - sheenVx * 16) * dt;
      sheenVy += ((targetY - sheenY) * 34 - sheenVy * 16) * dt;
      sheenX += sheenVx * dt;
      sheenY += sheenVy * dt;
      strength += (want - strength) * (1 - Math.exp(-9 * dt));
      if (want || strength > 0.004) time += dt;
      if (!want && strength < 0.01 && host) {
        if (canvas.parentNode === host) host.removeChild(canvas);
        host = null;
        rect = null;
        strength = 0;
      }
    }

    function draw() {
      if (!host || strength < 0.004 || !sizedW) return false;
      var portrait = quiet;
      if (gl) {
        gpu.draw(sizedW, sizedH, bodyX, bodyY, sheenX, sheenY, specX, specY, time, strength, portrait);
      } else if (cpu) {
        paintGlassCpu(cpu, sizedW, sizedH, bodyX, bodyY, sheenX, sheenY, specX, specY, time, strength, portrait);
      }
      return strength > 0.004;
    }

    return { place: place, leave: leave, step: step, draw: draw };
  }

  function linkGlass(gl) {
    var vert = compile(gl, gl.VERTEX_SHADER, [
      "attribute vec2 aPos;",
      "void main(){ gl_Position = vec4(aPos, 0.0, 1.0); }"
    ].join("\n"));
    var frag = compile(gl, gl.FRAGMENT_SHADER, [
      "precision mediump float;",
      "uniform vec2 uRes;",
      "uniform vec2 uBody;",
      "uniform vec2 uSheen;",
      "uniform vec2 uSpec;",
      "uniform float uTime;",
      "uniform float uStrength;",
      "uniform float uPortrait;",
      "void main(){",
      "  vec2 uv = gl_FragCoord.xy / uRes;",
      "  uv.y = 1.0 - uv.y;",
      "  float aspect = uRes.x / max(uRes.y, 1.0);",
      "  vec2 p = (uv - 0.5) * vec2(aspect, 1.0);",
      "  vec2 body = (uBody - 0.5) * vec2(aspect, 1.0);",
      "  vec2 sheen = (uSheen - 0.5) * vec2(aspect, 1.0);",
      "  vec2 spec = (uSpec - 0.5) * vec2(aspect, 1.0);",
      "  vec2 db = p - body;",
      "  float sd = length(db);",
      "  float sheenD = length(p - sheen);",
      "  float pool = exp(-sd * sd * 2.2);",
      "  float sheet = exp(-sheenD * sheenD * 0.95);",
      "  vec2 dir = sd > 0.0008 ? db / sd : vec2(0.0);",
      "  vec2 bent = p - dir * (0.045 * exp(-sd * 2.2));",
      "  float sdBent = length(bent - body);",
      "  float lens = exp(-pow(sdBent - 0.22, 2.0) * 28.0);",
      "  float ndv = clamp(1.0 - smoothstep(0.05, 0.55, sd), 0.0, 1.0);",
      "  float fresnel = 0.18 + 0.82 * pow(1.0 - ndv, 5.0);",
      "  float rim = smoothstep(0.12, 0.28, sd) * (1.0 - smoothstep(0.28, 0.55, sd));",
      "  float rimLight = rim * fresnel;",
      "  vec2 edge = abs(uv - 0.5) * 2.0;",
      "  float edgeF = pow(clamp(max(edge.x, edge.y), 0.0, 1.0), 5.0);",
      "  float edgeLit = edgeF * exp(-sd * 1.1) * 0.55;",
      "  vec3 L = normalize(vec3(spec.x - p.x, spec.y - p.y, 0.42));",
      "  float ndh = clamp(normalize(L + vec3(0.0, 0.0, 1.0)).z, 0.0, 1.0);",
      "  float specTight = pow(ndh, 64.0) * (1.0 - uPortrait);",
      "  float specWide = pow(ndh, 8.0);",
      "  float opd = exp(-sheenD * 2.4) * 22.0 + uTime * 0.55;",
      "  vec3 film = vec3(0.5 + 0.5 * cos(opd * 1.15), 0.5 + 0.5 * cos(opd * 0.92 + 0.7), 0.5 + 0.5 * cos(opd * 1.55 + 1.8));",
      "  film.g *= 0.82;",
      "  film.b *= 0.28;",
      "  float w1 = sin(sdBent * 28.0 - uTime * 0.65 + sin(p.x * 6.0 + uTime * 0.2) * 1.3);",
      "  float w2 = sin(dot(bent, vec2(11.0, -8.0)) + sd * 6.0 + uTime * 0.4);",
      "  float caustic = pow(clamp(w1 * w2, 0.0, 1.0), 1.15) * exp(-sd * 1.35);",
      "  caustic *= 1.0 - uPortrait * 0.75;",
      "  float rings = smoothstep(0.55, 0.92, 0.5 + 0.5 * cos(sheenD * 42.0 - uTime * 0.9));",
      "  rings *= sheet * (1.0 - uPortrait);",
      "  vec3 deep = vec3(0.62, 0.38, 0.10);",
      "  vec3 brass = vec3(0.886, 0.710, 0.416);",
      "  vec3 cream = vec3(0.98, 0.86, 0.52);",
      "  vec3 col = brass * (0.55 + pool * 0.45);",
      "  col = mix(col, deep, clamp(rimLight, 0.0, 1.0) * 0.55);",
      "  col = mix(col, film, clamp(sheet, 0.0, 1.0) * 0.42);",
      "  col = mix(col, cream, clamp(specTight * 0.7 + specWide * 0.18 + caustic * 0.35 + rings * 0.4 + lens * 0.28, 0.0, 0.72));",
      "  col = min(col, vec3(0.98, 0.86, 0.55));",
      "  float alpha = pool * 0.62 + sheet * 0.34 + rimLight * 0.5 + specTight * 0.16;",
      "  alpha += specWide * 0.1 + caustic * 0.22 + lens * 0.24 + edgeLit * 0.3 + rings * 0.28;",
      "  alpha *= uStrength * mix(1.0, 0.28, uPortrait);",
      "  alpha = clamp(alpha, 0.0, mix(0.62, 0.2, uPortrait));",
      "  gl_FragColor = vec4(col, alpha);",
      "}"
    ].join("\n"));
    if (!vert || !frag) return null;
    var program = gl.createProgram();
    gl.attachShader(program, vert);
    gl.attachShader(program, frag);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
    gl.useProgram(program);
    var buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var at = gl.getAttribLocation(program, "aPos");
    gl.enableVertexAttribArray(at);
    gl.vertexAttribPointer(at, 2, gl.FLOAT, false, 0, 0);
    var loc = {
      res: gl.getUniformLocation(program, "uRes"),
      body: gl.getUniformLocation(program, "uBody"),
      sheen: gl.getUniformLocation(program, "uSheen"),
      spec: gl.getUniformLocation(program, "uSpec"),
      time: gl.getUniformLocation(program, "uTime"),
      strength: gl.getUniformLocation(program, "uStrength"),
      portrait: gl.getUniformLocation(program, "uPortrait")
    };
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    return {
      draw: function (w, h, bodyX, bodyY, sheenX, sheenY, specX, specY, time, strength, portrait) {
        gl.useProgram(program);
        gl.uniform2f(loc.res, w, h);
        gl.uniform2f(loc.body, bodyX, bodyY);
        gl.uniform2f(loc.sheen, sheenX, sheenY);
        gl.uniform2f(loc.spec, specX, specY);
        gl.uniform1f(loc.time, time);
        gl.uniform1f(loc.strength, strength);
        gl.uniform1f(loc.portrait, portrait);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      }
    };
  }

  function compile(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  function paintGlassCpu(ctx, w, h, bodyX, bodyY, sheenX, sheenY, specX, specY, time, strength, portrait) {
    var image = ctx.createImageData(w, h);
    var data = image.data;
    var aspect = w / Math.max(h, 1);
    var gain = strength * (portrait ? 0.28 : 1);
    var i = 0;
    for (var y = 0; y < h; y++) {
      var v = 1 - (y + 0.5) / h;
      for (var x = 0; x < w; x++) {
        var u = (x + 0.5) / w;
        var px = (u - 0.5) * aspect;
        var py = v - 0.5;
        var bx = (bodyX - 0.5) * aspect;
        var by = bodyY - 0.5;
        var dx = px - bx;
        var dy = py - by;
        var sd = Math.sqrt(dx * dx + dy * dy);
        var sx = px - (sheenX - 0.5) * aspect;
        var sy = py - (sheenY - 0.5);
        var sheenD = Math.sqrt(sx * sx + sy * sy);
        var pool = Math.exp(-sd * sd * 2.2);
        var sheet = Math.exp(-sheenD * sheenD * 0.95);
        var dirx = sd > 0.0008 ? dx / sd : 0;
        var diry = sd > 0.0008 ? dy / sd : 0;
        var bend = 0.045 * Math.exp(-sd * 2.2);
        var bentx = px - dirx * bend;
        var benty = py - diry * bend;
        var sdx = bentx - bx;
        var sdy = benty - by;
        var sdBent = Math.sqrt(sdx * sdx + sdy * sdy);
        var lens = Math.exp(-Math.pow(sdBent - 0.22, 2) * 28);
        var ndv = 1 - smooth(0.05, 0.55, sd);
        var fresnel = 0.18 + 0.82 * Math.pow(1 - ndv, 5);
        var rimIn = smooth(0.12, 0.28, sd);
        var rimOut = 1 - smooth(0.28, 0.55, sd);
        var rimLight = rimIn * rimOut * fresnel;
        var edge = Math.max(Math.abs(u - 0.5) * 2, Math.abs(v - 0.5) * 2);
        if (edge > 1) edge = 1;
        var edgeLit = Math.pow(edge, 5) * Math.exp(-sd * 1.1) * 0.55;
        var lx = ((specX - 0.5) * aspect) - px;
        var ly = (specY - 0.5) - py;
        var lz = 0.42;
        var llen = Math.sqrt(lx * lx + ly * ly + lz * lz) || 1;
        lx /= llen; ly /= llen; lz /= llen;
        var hx = lx;
        var hy = ly;
        var hz = lz + 1;
        var hlen = Math.sqrt(hx * hx + hy * hy + hz * hz) || 1;
        var ndh = hz / hlen;
        if (ndh < 0) ndh = 0;
        var specTight = Math.pow(ndh, 64) * (1 - portrait);
        var specWide = Math.pow(ndh, 8);
        var opd = Math.exp(-sheenD * 2.4) * 22 + time * 0.55;
        var filmR = 0.5 + 0.5 * Math.cos(opd * 1.15);
        var filmG = (0.5 + 0.5 * Math.cos(opd * 0.92 + 0.7)) * 0.82;
        var filmB = (0.5 + 0.5 * Math.cos(opd * 1.55 + 1.8)) * 0.28;
        var w1 = Math.sin(sdBent * 28 - time * 0.65 + Math.sin(px * 6 + time * 0.2) * 1.3);
        var w2 = Math.sin(bentx * 11 + benty * -8 + sd * 6 + time * 0.4);
        var caustic = Math.pow(Math.max(0, w1 * w2), 1.15) * Math.exp(-sd * 1.35);
        caustic *= 1 - portrait * 0.75;
        var rings = smooth(0.55, 0.92, 0.5 + 0.5 * Math.cos(sheenD * 42 - time * 0.9));
        rings *= sheet * (1 - portrait);
        var mixSpec = specTight * 0.7 + specWide * 0.18 + caustic * 0.35 + rings * 0.4 + lens * 0.28;
        if (mixSpec > 0.72) mixSpec = 0.72;
        if (mixSpec < 0) mixSpec = 0;
        var filmMix = sheet * 0.42;
        if (filmMix > 1) filmMix = 1;
        var rimMix = rimLight * 0.55;
        if (rimMix > 1) rimMix = 1;
        var br = 0.886 * (0.55 + pool * 0.45);
        var bgc = 0.710 * (0.55 + pool * 0.45);
        var bb = 0.416 * (0.55 + pool * 0.45);
        var r = br * (1 - rimMix) + 0.62 * rimMix;
        var g = bgc * (1 - rimMix) + 0.38 * rimMix;
        var b = bb * (1 - rimMix) + 0.10 * rimMix;
        r = r * (1 - filmMix) + filmR * filmMix;
        g = g * (1 - filmMix) + filmG * filmMix;
        b = b * (1 - filmMix) + filmB * filmMix;
        r = r * (1 - mixSpec) + 0.98 * mixSpec;
        g = g * (1 - mixSpec) + 0.86 * mixSpec;
        b = b * (1 - mixSpec) + 0.52 * mixSpec;
        if (r > 0.98) r = 0.98;
        if (g > 0.86) g = 0.86;
        if (b > 0.55) b = 0.55;
        var alpha = pool * 0.62 + sheet * 0.34 + rimLight * 0.5 + specTight * 0.16;
        alpha += specWide * 0.1 + caustic * 0.22 + lens * 0.24 + edgeLit * 0.3 + rings * 0.28;
        alpha *= gain;
        if (alpha > (portrait ? 0.2 : 0.62)) alpha = portrait ? 0.2 : 0.62;
        if (alpha < 0) alpha = 0;
        data[i] = Math.max(0, Math.min(255, r * 255));
        data[i + 1] = Math.max(0, Math.min(255, g * 255));
        data[i + 2] = Math.max(0, Math.min(255, b * 255));
        data[i + 3] = alpha * 255;
        i += 4;
      }
    }
    ctx.putImageData(image, 0, 0);
  }

  function smooth(edge0, edge1, value) {
    var t = (value - edge0) / (edge1 - edge0);
    if (t < 0) t = 0;
    if (t > 1) t = 1;
    return t * t * (3 - 2 * t);
  }

  function setupPointer(host) {
    var root = document.documentElement;
    root.classList.add("has-pointer");
    var cursor = document.createElement("div");
    cursor.className = "cursor";
    cursor.setAttribute("aria-hidden", "true");
    var ring = document.createElement("span");
    ring.className = "cursor-ring";
    var dot = document.createElement("span");
    dot.className = "cursor-dot";
    cursor.appendChild(ring);
    cursor.appendChild(dot);
    document.body.appendChild(cursor);

    var tx = 0;
    var ty = 0;
    var rx = 0;
    var ry = 0;
    var hot = false;
    var glass = createGlass();
    var items = ".logo-chip, .chips li, .tagline li, .proof li, .tech-card, .plate, .work-card, .press-card, .cover, .honor, .school, .cert, .seal, .note, .talk, .role, .company, .timeline li, .quote, .photo-frame, .still-media, .portrait-frame, .replay, button, .hero-actions a, summary";
    var running = false;
    var lastNow = 0;
    var pulled = null;

    function setPull(el, x, y) {
      if (pulled && pulled !== el) {
        pulled.style.removeProperty("--pull-x");
        pulled.style.removeProperty("--pull-y");
        pulled.classList.remove("is-pulled");
        pulled = null;
      }
      if (!el || el.classList.contains("portrait-frame")) return;
      var box = el.getBoundingClientRect();
      if (!box.width || !box.height) return;
      var dx = x - (box.left + box.width / 2);
      var dy = y - (box.top + box.height / 2);
      var dist = Math.hypot(dx, dy) || 1;
      var limit = Math.min(6, Math.max(box.width, box.height) * 0.06);
      var force = Math.min(limit, dist * 0.12);
      el.style.setProperty("--pull-x", (dx / dist * force).toFixed(2) + "px");
      el.style.setProperty("--pull-y", (dy / dist * force).toFixed(2) + "px");
      el.classList.add("is-pulled");
      pulled = el;
    }

    document.addEventListener("pointermove", function (event) {
      if (event.pointerType === "touch") return;
      tx = event.clientX;
      ty = event.clientY;
      cursor.classList.add("is-on");
      root.classList.add("cursor-on");
      var surface = event.target && event.target.closest ? event.target.closest(items) : null;
      var nextHot = !!surface;
      if (nextHot !== hot) {
        hot = nextHot;
        root.classList.toggle("is-hot", hot);
      }
      glass.place(surface, event.clientX, event.clientY);
      setPull(surface, event.clientX, event.clientY);
      kick();
      if (!host) return;
      var heroBox = host.getBoundingClientRect();
      var inside = event.clientX >= heroBox.left && event.clientX <= heroBox.right && event.clientY >= heroBox.top && event.clientY <= heroBox.bottom;
      if (!inside || !heroBox.width || !heroBox.height) {
        host.style.removeProperty("--shift-x");
        host.style.removeProperty("--shift-y");
        var portrait = host.querySelector(".portrait");
        if (portrait) {
          portrait.style.removeProperty("--tilt-x");
          portrait.style.removeProperty("--tilt-y");
        }
      } else {
        var px = (event.clientX - heroBox.left) / heroBox.width - 0.5;
        var py = (event.clientY - heroBox.top) / heroBox.height - 0.5;
        host.style.setProperty("--shift-x", (px * 14).toFixed(2) + "px");
        host.style.setProperty("--shift-y", (py * 8).toFixed(2) + "px");
        var frame = host.querySelector(".portrait");
        if (frame) {
          frame.style.setProperty("--tilt-x", (-py * 3.2).toFixed(2) + "deg");
          frame.style.setProperty("--tilt-y", (px * 4).toFixed(2) + "deg");
        }
      }
    });

    document.documentElement.addEventListener("mouseleave", function () {
      cursor.classList.remove("is-on");
      root.classList.remove("cursor-on");
      glass.leave();
      setPull(null, 0, 0);
      kick();
    });

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) kick();
    });

    function kick() {
      if (running || document.hidden) return;
      running = true;
      lastNow = 0;
      window.requestAnimationFrame(tick);
    }

    function tick(now) {
      if (document.hidden) {
        running = false;
        return;
      }
      var dt = lastNow ? Math.min(0.05, (now - lastNow) / 1000) : 0.016;
      lastNow = now;
      rx += (tx - rx) * 0.2;
      ry += (ty - ry) * 0.2;
      dot.style.transform = "translate3d(" + tx + "px," + ty + "px,0) translate(-50%, -50%)";
      ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0) translate(-50%, -50%)";
      glass.step(dt);
      var drawing = glass.draw();
      var cursorMoving = Math.abs(tx - rx) > 0.3 || Math.abs(ty - ry) > 0.3;
      if (cursor.classList.contains("is-on") || cursorMoving || drawing) {
        window.requestAnimationFrame(tick);
      } else {
        running = false;
      }
    }
  }
})();
