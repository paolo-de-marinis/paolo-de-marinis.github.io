(() => {
  const root = document.documentElement;
  const toggle = document.querySelector(".theme-toggle");
  const labels = root.lang === "en"
    ? { dark: "Switch to dark theme", light: "Switch to light theme" }
    : { dark: "Attiva il tema scuro", light: "Attiva il tema chiaro" };
  let saved;
  try { saved = localStorage.getItem("theme"); } catch {}

  const apply = (theme) => {
    root.dataset.theme = theme;
    if (!toggle) return;
    const next = theme === "dark" ? "light" : "dark";
    toggle.setAttribute("aria-label", labels[next]);
    toggle.setAttribute("title", labels[next]);
    toggle.firstElementChild.textContent = theme === "dark" ? "☀" : "☾";
  };

  root.classList.add("js");
  apply(saved === "dark" || saved === "light"
    ? saved
    : (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  toggle?.addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", next); } catch {}
    apply(next);
  });
})();
