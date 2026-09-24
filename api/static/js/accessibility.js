let liveRegion = null;

export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function ensureLiveRegion() {
  if (liveRegion) return liveRegion;
  liveRegion = document.createElement("div");
  liveRegion.id = "mai-live-region";
  liveRegion.setAttribute("role", "status");
  liveRegion.setAttribute("aria-live", "polite");
  liveRegion.setAttribute("aria-atomic", "true");
  liveRegion.style.cssText =
    "position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0";
  document.body.appendChild(liveRegion);
  return liveRegion;
}

export function announce(message, assertive = false) {
  const region = ensureLiveRegion();
  region.setAttribute("aria-live", assertive ? "assertive" : "polite");
  region.textContent = "";
  setTimeout(() => {
    region.textContent = message;
  }, 50);
}

export function getFocusable(container) {
  const selector =
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(container.querySelectorAll(selector)).filter((el) => {
    return el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0;
  });
}

export function trapFocus(container) {
  const focusable = getFocusable(container);
  if (!focusable.length) return () => {};
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  function handler(event) {
    if (event.key !== "Tab") return;
    if (event.shiftKey) {
      if (document.activeElement === first) {
        event.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  container.addEventListener("keydown", handler);
  first.focus();
  return () => {
    container.removeEventListener("keydown", handler);
  };
}

export function setPageTitle(title) {
  document.title = title ? `${title} — MAI` : "MAI Cognitive OS";
}

export function skipToMain() {
  const main = document.getElementById("main-content") || document.querySelector("main");
  if (main) {
    main.setAttribute("tabindex", "-1");
    main.focus({ preventScroll: true });
  }
}

export const A11y = {
  prefersReducedMotion,
  announce,
  getFocusable,
  trapFocus,
  setPageTitle,
  skipToMain,
};

window.MaiA11y = A11y;

export default A11y;