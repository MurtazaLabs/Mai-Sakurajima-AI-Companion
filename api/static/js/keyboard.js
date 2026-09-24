const bindings = new Map();
let nextId = 1;

function parseCombo(combo) {
  const parts = combo
    .toLowerCase()
    .split("+")
    .map((part) => part.trim())
    .filter(Boolean);
  const parsed = { mod: false, ctrl: false, meta: false, alt: false, shift: false, key: "" };
  for (const part of parts) {
    if (part === "mod") parsed.mod = true;
    else if (part === "ctrl" || part === "control") parsed.ctrl = true;
    else if (part === "meta" || part === "cmd" || part === "command") parsed.meta = true;
    else if (part === "alt" || part === "option") parsed.alt = true;
    else if (part === "shift") parsed.shift = true;
    else parsed.key = part;
  }
  return parsed;
}

function normalizeKey(event) {
  const key = (event.key || "").toLowerCase();
  if (key === " ") return "space";
  return key;
}

function keysMatch(binding, event) {
  const key = normalizeKey(event);
  const bindingKey = binding.key;
  const keyMatches =
    bindingKey === key ||
    (bindingKey === "escape" && key === "esc") ||
    (bindingKey === "esc" && key === "escape");
  if (!keyMatches) return false;

  if (binding.mod) {
    if (!(event.ctrlKey || event.metaKey)) return false;
  } else {
    if (event.ctrlKey !== binding.ctrl) return false;
    if (event.metaKey !== binding.meta) return false;
  }
  if (event.altKey !== binding.alt) return false;
  if (event.shiftKey !== binding.shift) return false;
  return true;
}

function isTypingTarget(target) {
  if (!target || !(target instanceof Element)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

export function register(combo, handler, options = {}) {
  const id = nextId++;
  bindings.set(id, {
    ...parseCombo(combo),
    combo,
    handler,
    description: options.description || "",
    allowInInput: Boolean(options.allowInInput),
    preventDefault: options.preventDefault !== false,
  });
  return () => bindings.delete(id);
}

export function unregister(id) {
  bindings.delete(id);
}

export function list() {
  return [...bindings.values()].map((binding) => ({
    combo: binding.combo,
    description: binding.description,
  }));
}

export function formatCombo(combo) {
  const isApple = /mac|iphone|ipad|ipod/i.test(
    navigator.platform || navigator.userAgent || ""
  );
  return combo
    .split("+")
    .map((part) => {
      const p = part.trim().toLowerCase();
      if (p === "mod") return isApple ? "⌘" : "Ctrl";
      if (p === "ctrl") return isApple ? "⌃" : "Ctrl";
      if (p === "meta" || p === "cmd") return isApple ? "⌘" : "Win";
      if (p === "alt") return isApple ? "⌥" : "Alt";
      if (p === "shift") return isApple ? "⇧" : "Shift";
      return p.length === 1 ? p.toUpperCase() : p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(isApple ? "" : " + ");
}

function onKeyDown(event) {
  const typing = isTypingTarget(event.target);
  for (const binding of bindings.values()) {
    if (typing && !binding.allowInInput) continue;
    if (!keysMatch(binding, event)) continue;
    if (binding.preventDefault) event.preventDefault();
    try {
      binding.handler(event);
    } catch (error) {
      console.warn("[Keyboard] handler failed for", binding.combo, error);
    }
    return;
  }
}

document.addEventListener("keydown", onKeyDown);

export const KeyboardShortcuts = { register, unregister, list, formatCombo };

window.MaiKeyboard = KeyboardShortcuts;

export default KeyboardShortcuts;
