(function () {
  var input = document.getElementById("id_q");
  var box = document.getElementById("q-suggest");
  if (!input || !box || !window.SUGGEST_URL) return;

  var timer = null;
  var current = -1;

  function hide() {
    box.classList.remove("open");
    box.innerHTML = "";
    current = -1;
  }

  function items() {
    return box.querySelectorAll(".suggest-item");
  }

  function highlight(idx) {
    var list = items();
    list.forEach(function (el, i) { el.classList.toggle("active", i === idx); });
    if (list[idx]) list[idx].scrollIntoView({ block: "nearest" });
  }

  function fetchSuggestions(term) {
    fetch(window.SUGGEST_URL + "?q=" + encodeURIComponent(term), {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) { return res.text(); })
      .then(function (html) {
        box.innerHTML = html;
        current = -1;
        box.classList.toggle("open", items().length > 0);
      })
      .catch(function () { /* silent: suggestions are best-effort */ });
  }

  input.addEventListener("input", function () {
    var term = input.value.trim();
    clearTimeout(timer);
    if (term.length < 2) {
      hide();
      return;
    }
    timer = setTimeout(function () { fetchSuggestions(term); }, 250);
  });

  input.addEventListener("keydown", function (e) {
    var list = items();
    if (!list.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      current = Math.min(current + 1, list.length - 1);
      highlight(current);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      current = Math.max(current - 1, 0);
      highlight(current);
    } else if (e.key === "Enter" && current >= 0) {
      e.preventDefault();
      list[current].click();
    } else if (e.key === "Escape") {
      hide();
    }
  });

  document.addEventListener("click", function (e) {
    if (!box.contains(e.target) && e.target !== input) hide();
  });
})();
