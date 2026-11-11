/* Scroll reveal for elements marked .reveal.
   If this file does not run, those elements stay visible. */
(function () {
  var reduce = false;
  try {
    reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (err) {
    reduce = false;
  }
  if (reduce || !("IntersectionObserver" in window)) return;

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
})();
