(() => {
  const root = document.documentElement;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const pageCleanups = [];
  let navigationController;

  const copy = () => root.lang.startsWith("en")
    ? {
        dark: "Switch to dark theme",
        light: "Switch to light theme",
        currentPhase: "Current phase",
        loadingAudit: "Loading the latest audit data…",
        auditUnavailable: "The latest audit data is temporarily unavailable.",
        auditedOn: "Automated audit run on"
      }
    : {
        dark: "Attiva il tema scuro",
        light: "Attiva il tema chiaro",
        currentPhase: "Fase corrente",
        loadingAudit: "Caricamento dell’ultimo audit…",
        auditUnavailable: "I dati dell’ultimo audit non sono temporaneamente disponibili.",
        auditedOn: "Audit automatico eseguito il"
      };

  const registerCleanup = (cleanup) => pageCleanups.push(cleanup);

  const bindWindow = (type, listener, options) => {
    addEventListener(type, listener, options);
    registerCleanup(() => removeEventListener(type, listener, options));
  };

  const cleanupPage = () => {
    while (pageCleanups.length) pageCleanups.pop()();
  };

  const initTheme = () => {
    const toggle = document.querySelector(".theme-toggle");
    let saved;
    try { saved = localStorage.getItem("theme"); } catch {}

    const apply = (theme) => {
      root.dataset.theme = theme;
      if (!toggle) return;
      const labels = copy();
      const next = theme === "dark" ? "light" : "dark";
      toggle.setAttribute("aria-label", labels[next]);
      toggle.setAttribute("title", labels[next]);
      toggle.firstElementChild.textContent = theme === "dark" ? "☀" : "☾";
    };

    apply(saved === "dark" || saved === "light"
      ? saved
      : (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

    toggle?.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      try { localStorage.setItem("theme", next); } catch {}
      apply(next);
    });
  };

  const initTimelines = () => {
    document.querySelectorAll(".interactive-timeline").forEach((timeline) => {
      const rail = timeline.querySelector(".timeline-rail");
      const live = timeline.querySelector("[aria-live]");
      if (!rail || !live) return;

      const links = [...rail.querySelectorAll('a[href^="#"]')];
      const steps = links.map((link) => document.getElementById(link.hash.slice(1)));
      if (!links.length || steps.some((step) => !step)) return;

      let active = -1;
      let scheduled = false;
      const setActive = (index) => {
        if (index < 0 || index === active) return;
        active = index;
        steps.forEach((step, i) => step.classList.toggle("is-active", i === index));
        links.forEach((link, i) => i === index
          ? link.setAttribute("aria-current", "step")
          : link.removeAttribute("aria-current"));
        rail.style.setProperty("--timeline-progress", `${index / (steps.length - 1) * 80}%`);
        const label = links[index].querySelector("strong").textContent.trim();
        live.textContent = `${copy().currentPhase}: ${label}`;
      };

      const update = () => {
        scheduled = false;
        const sticky = timeline.querySelector(".timeline-scroll-sticky");
        const visibleTop = sticky ? sticky.getBoundingClientRect().bottom : 0;
        let best = active < 0 ? 0 : active;
        let bestVisible = 0;
        steps.forEach((step, index) => {
          const rect = step.getBoundingClientRect();
          const visible = Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, visibleTop));
          if (visible > bestVisible) [best, bestVisible] = [index, visible];
        });
        setActive(best);
      };

      const schedule = () => {
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(update);
      };

      const activateHash = () => {
        const index = links.findIndex((link) => link.hash === location.hash);
        if (index >= 0) setActive(index);
        schedule();
      };

      links.forEach((link, index) => link.addEventListener("click", () => setActive(index)));
      bindWindow("hashchange", activateHash);
      bindWindow("scroll", schedule, { passive: true });
      bindWindow("resize", schedule);

      if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver(schedule, { threshold: [0, .25, .5, .75, 1] });
        steps.forEach((step) => observer.observe(step));
        registerCleanup(() => observer.disconnect());
      }

      activateHash();
    });
  };

  const initAudit = () => {
    const panel = document.querySelector("[data-lighthouse-audit]");
    if (!panel) return;

    const status = panel.querySelector("[data-audit-status]");
    if (status) status.textContent = copy().loadingAudit;

    fetch("/data/lighthouse.json", { cache: "no-store", headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!data?.profiles?.mobile || !data?.profiles?.desktop || !data?.auditedAt) {
          throw new Error("Incomplete audit data");
        }

        panel.querySelectorAll("[data-audit-profile]").forEach((profileElement) => {
          const profile = data.profiles[profileElement.dataset.auditProfile];
          if (!profile) return;
          profileElement.querySelectorAll("[data-audit-score]").forEach((scoreElement) => {
            const value = profile[scoreElement.dataset.auditScore];
            scoreElement.textContent = Number.isFinite(value) ? String(value) : "—";
          });
        });

        const date = new Date(data.auditedAt);
        const formatted = new Intl.DateTimeFormat(root.lang.startsWith("en") ? "en-GB" : "it-IT", {
          dateStyle: "long",
          timeStyle: "short",
          timeZone: "Europe/Rome"
        }).format(date);
        const time = panel.querySelector("time[data-audit-date]");
        if (time) {
          time.dateTime = data.auditedAt;
          time.textContent = formatted;
        }
        if (status) status.textContent = `${copy().auditedOn} ${formatted}.`;
      })
      .catch(() => {
        if (status) status.textContent = copy().auditUnavailable;
      });
  };

  const syncHead = (nextDocument) => {
    document.title = nextDocument.title;
    const selectors = [
      'meta[name="description"]',
      'link[rel="canonical"]',
      'link[rel="alternate"][hreflang="it-IT"]',
      'link[rel="alternate"][hreflang="en"]',
      'meta[property="og:title"]',
      'meta[property="og:description"]',
      'meta[property="og:url"]',
      'meta[property="og:image"]',
      'meta[property="og:image:alt"]',
      'meta[name="twitter:title"]',
      'meta[name="twitter:description"]',
      'meta[name="twitter:image"]',
      'meta[name="twitter:image:alt"]'
    ];

    selectors.forEach((selector) => {
      const current = document.head.querySelector(selector);
      const next = nextDocument.head.querySelector(selector);
      if (!current || !next) return;
      [...next.attributes].forEach((attribute) => current.setAttribute(attribute.name, attribute.value));
    });
  };

  const translatedHash = (hash, targetPath) => {
    if (targetPath.startsWith("/en/") && hash === "#licenze") return "#licenses";
    if (!targetPath.startsWith("/en/") && hash === "#licenses") return "#licenze";
    return hash;
  };

  const navigateWithoutReload = async (target, { push = true, scrollPosition = scrollY } = {}) => {
    navigationController?.abort();
    navigationController = new AbortController();
    root.setAttribute("aria-busy", "true");

    try {
      const response = await fetch(target.pathname + target.search, {
        signal: navigationController.signal,
        headers: { "X-Requested-With": "language-switch" }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const nextDocument = new DOMParser().parseFromString(await response.text(), "text/html");
      const nextBody = document.importNode(nextDocument.body, true);
      nextBody.querySelectorAll('script[src="/site.js"]').forEach((script) => script.remove());

      const swap = () => {
        const previousUrl = location.href;
        const previousScroll = scrollY;
        cleanupPage();
        syncHead(nextDocument);
        root.lang = nextDocument.documentElement.lang;
        root.dir = nextDocument.documentElement.dir || "";
        document.body.replaceWith(nextBody);

        if (push) {
          history.replaceState({ ...(history.state || {}), scrollPosition: previousScroll }, "", previousUrl);
          history.pushState({ languagePage: true, scrollPosition }, "", target.href);
        }

        initPage();
        requestAnimationFrame(() => scrollTo({ top: scrollPosition, left: 0, behavior: "auto" }));
      };

      if (document.startViewTransition && !reduceMotion.matches) {
        await document.startViewTransition(swap).finished;
      } else {
        swap();
      }
    } catch (error) {
      if (error.name !== "AbortError") location.assign(target.href);
    } finally {
      root.removeAttribute("aria-busy");
    }
  };

  const initLanguageSwitch = () => {
    const link = document.querySelector(".site-controls a[hreflang]");
    if (!link) return;

    link.addEventListener("click", (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = new URL(link.href, location.href);
      target.hash = translatedHash(location.hash, target.pathname);
      event.preventDefault();
      navigateWithoutReload(target, { scrollPosition: scrollY });
    });
  };

  const initSectionNavigation = () => {
    document.querySelectorAll('.site-nav a[href^="#"], .wordmark[href^="#"]').forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const target = document.getElementById(link.hash.slice(1));
        if (!target) return;

        event.preventDefault();
        if (location.hash !== link.hash) {
          history.pushState({
            ...(history.state || {}),
            languagePage: true,
            scrollPosition: Math.max(0, target.offsetTop)
          }, "", link.hash);
        }
        target.scrollIntoView({
          behavior: reduceMotion.matches ? "auto" : "smooth",
          block: "start"
        });
      });
    });
  };

  const initLegalDialogs = () => {
    const dialogs = [...document.querySelectorAll("dialog.legal-dialog")];
    if (!dialogs.length) return;

    document.querySelectorAll("[data-dialog-target]").forEach((trigger) => {
      const dialog = document.getElementById(trigger.dataset.dialogTarget);
      if (!(dialog instanceof HTMLDialogElement)) return;
      trigger.addEventListener("click", () => {
        dialog.showModal();
        root.classList.add("modal-open");
      });
    });

    dialogs.forEach((dialog) => {
      dialog.querySelector("[data-dialog-close]")?.addEventListener("click", () => dialog.close());
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
      });
      dialog.addEventListener("cancel", () => root.classList.remove("modal-open"));
      dialog.addEventListener("close", () => root.classList.remove("modal-open"));
    });
  };

  const initPage = () => {
    root.classList.add("js");
    initTheme();
    initTimelines();
    initAudit();
    initLanguageSwitch();
    initSectionNavigation();
    initLegalDialogs();
  };

  addEventListener("popstate", (event) => {
    navigateWithoutReload(new URL(location.href), {
      push: false,
      scrollPosition: event.state?.scrollPosition ?? 0
    });
  });

  history.replaceState({ ...(history.state || {}), languagePage: true, scrollPosition: scrollY }, "", location.href);
  initPage();
})();
