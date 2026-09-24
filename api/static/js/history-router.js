import { isAuthenticated } from "./api-client.js";

const routes = [];

function escapeRegex(segment) {
  return segment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function compile(pattern) {
  const normalized =
    pattern.length > 1 && pattern.endsWith("/") ? pattern.slice(0, -1) : pattern;
  const segments = normalized.split("/").filter(Boolean);
  const names = [];
  const parts = segments.map((segment) => {
    if (segment.startsWith(":")) {
      const name = segment.slice(1);
      names.push(name);
      return `(?<${name}>[^/]+)`;
    }
    return escapeRegex(segment);
  });
  const source = parts.length ? `/${parts.join("/")}` : "/";
  return { regex: new RegExp(`^${source}/?$`), names };
}

export function route(pattern, handler, options = {}) {
  const { regex, names } = compile(pattern);
  const entry = {
    pattern,
    regex,
    names,
    handler,
    requiresAuth: Boolean(options.requiresAuth),
    title: options.title,
  };
  routes.push(entry);
  return () => {
    const index = routes.indexOf(entry);
    if (index >= 0) routes.splice(index, 1);
  };
}

export function match(pathname) {
  const path =
    pathname.length > 1 && pathname.endsWith("/")
      ? pathname.slice(0, -1)
      : pathname;
  for (const entry of routes) {
    const m = path.match(entry.regex);
    if (m) return { route: entry, params: { ...(m.groups || {}) } };
  }
  return null;
}

function dispatch(pathname) {
  const found = match(pathname);
  if (!found) {
    window.dispatchEvent(
      new CustomEvent("router:nomatch", { detail: { path: pathname } })
    );
    return false;
  }
  if (found.route.requiresAuth && !isAuthenticated()) {
    const next = encodeURIComponent(pathname + window.location.search);
    navigate(`/login?next=${next}`, { replace: true });
    return false;
  }
  const query = Object.fromEntries(new URLSearchParams(window.location.search));
  if (found.route.title) {
    document.title = `${found.route.title} — MAI`;
  }
  try {
    found.route.handler({
      params: found.params,
      query,
      path: pathname,
      route: found.route,
    });
  } catch (error) {
    console.warn("[Router] handler failed for", pathname, error);
  }
  window.dispatchEvent(
    new CustomEvent("route:change", {
      detail: { path: pathname, params: found.params, query },
    })
  );
  return true;
}

export function navigate(to, options = {}) {
  const { replace = false, state = {} } = options;
  if (replace) window.history.replaceState(state, "", to);
  else window.history.pushState(state, "", to);
  dispatch(window.location.pathname);
}

export function back() {
  window.history.back();
}

export function currentPath() {
  return window.location.pathname;
}

export function start() {
  window.addEventListener("popstate", () => {
    dispatch(window.location.pathname);
  });
  return dispatch(window.location.pathname);
}

const HistoryRouter = {
  route,
  match,
  navigate,
  back,
  currentPath,
  start,
};

window.MaiHistoryRouter = HistoryRouter;

export default HistoryRouter;
