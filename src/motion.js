/* Scroll reveal, a brass cursor, pointer light, and an occasional shooting star.
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
    var cards = ".tech-card, .plate, .work-card, .press-card, .cover, .photo, .still";
    var hotSelector = cards + ", a, button, .portrait, .logo-chip, summary";

    document.addEventListener("pointermove", function (event) {
      if (event.pointerType === "touch") return;
      tx = event.clientX;
      ty = event.clientY;
      cursor.classList.add("is-on");
      root.classList.add("cursor-on");
      var target = event.target && event.target.closest ? event.target.closest(hotSelector) : null;
      var nextHot = !!target;
      if (nextHot !== hot) {
        hot = nextHot;
        root.classList.toggle("is-hot", hot);
      }
      var card = event.target && event.target.closest ? event.target.closest(cards) : null;
      if (card) {
        var box = card.getBoundingClientRect();
        if (box.width && box.height) {
          card.style.setProperty("--lx", ((event.clientX - box.left) / box.width * 100) + "%");
          card.style.setProperty("--ly", ((event.clientY - box.top) / box.height * 100) + "%");
        }
      }
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
      var links = host.querySelectorAll(".hero-actions a");
      for (var n = 0; n < links.length; n++) {
        var link = links[n];
        var linkBox = link.getBoundingClientRect();
        var dx = event.clientX - (linkBox.left + linkBox.width / 2);
        var dy = event.clientY - (linkBox.top + linkBox.height / 2);
        var dist = Math.hypot(dx, dy);
        if (!dist || dist > 96) {
          link.style.removeProperty("--pull-x");
          link.style.removeProperty("--pull-y");
          continue;
        }
        var force = (1 - dist / 96) * 9;
        link.style.setProperty("--pull-x", (dx / dist * force).toFixed(2) + "px");
        link.style.setProperty("--pull-y", (dy / dist * force).toFixed(2) + "px");
      }
    });

    document.documentElement.addEventListener("mouseleave", function () {
      cursor.classList.remove("is-on");
      root.classList.remove("cursor-on");
    });

    function frame() {
      rx += (tx - rx) * 0.2;
      ry += (ty - ry) * 0.2;
      dot.style.transform = "translate3d(" + tx + "px," + ty + "px,0) translate(-50%, -50%)";
      ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0) translate(-50%, -50%)";
      window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }
})();
