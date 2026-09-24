const listeners = new Map();

export function on(type, handler) {
  if (typeof handler !== "function") return () => {};
  let set = listeners.get(type);
  if (!set) {
    set = new Set();
    listeners.set(type, set);
  }
  set.add(handler);
  return () => off(type, handler);
}

export function once(type, handler) {
  const unsubscribe = on(type, (event) => {
    unsubscribe();
    handler(event);
  });
  return unsubscribe;
}

export function off(type, handler) {
  const set = listeners.get(type);
  if (!set) return;
  set.delete(handler);
  if (set.size === 0) listeners.delete(type);
}

export function emit(type, detail) {
  const set = listeners.get(type);
  if (!set) return;
  for (const handler of [...set]) {
    try {
      handler({ type, detail, timestamp: Date.now() });
    } catch (error) {
      console.warn("[EventBus] handler failed for", type, error);
    }
  }
}

export function clear(type) {
  if (type === undefined) listeners.clear();
  else listeners.delete(type);
}

export const EventBus = { on, once, off, emit, clear };

window.MaiEventBus = EventBus;

export default EventBus;
