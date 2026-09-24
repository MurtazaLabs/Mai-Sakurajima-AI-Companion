import { login, register, me, api, isAuthenticated, logout, redirectToLogin } from "./api-client.js";
import { announce } from "./accessibility.js";

const form = document.getElementById("login-form");
const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const submitBtn = document.getElementById("submit-btn");
const errorEl = document.getElementById("login-error");
const statusEl = document.getElementById("login-status");
const modeToggle = document.getElementById("mode-toggle");
const switchPrompt = document.getElementById("switch-prompt");
const hintEl = document.getElementById("password-hint");
const titleEl = document.getElementById("login-title");

let mode = "login";

const params = new URLSearchParams(window.location.search);
const nextPath = sanitizeNext(params.get("next"));

function sanitizeNext(value) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/";
  return value;
}

function setMode(m) {
  mode = m;
  submitBtn.textContent = m === "login" ? "Sign in" : "Create account";
  switchPrompt.textContent = m === "login" ? "New to MAI?" : "Already have an account?";
  modeToggle.textContent = m === "login" ? "Create an account" : "Sign in";
  passwordEl.autocomplete = m === "login" ? "current-password" : "new-password";
  hintEl.hidden = m === "login";
  titleEl.textContent = m === "login" ? "Welcome back" : "Create your account";
  errorEl.hidden = true;
  statusEl.hidden = true;
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
  announce(message, true);
}

function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const username = usernameEl.value.trim();
  const password = passwordEl.value;

  if (!username || !password) {
    showError("Username and password are required.");
    return;
  }
  if (mode === "register" && password.length < 6) {
    showError("Password must be at least 6 characters.");
    return;
  }

  submitBtn.disabled = true;
  const originalText = submitBtn.textContent;
  submitBtn.textContent = mode === "login" ? "Signing in…" : "Creating account…";

  try {
    if (mode === "register") {
      await register(username, password);
    } else {
      await login(username, password);
    }

    statusEl.hidden = false;
    statusEl.textContent = "Signed in — verifying session…";

    const [user, status] = await Promise.all([
      me({ redirectOnFail: false }).catch(() => null),
      api.get("/api/status").catch(() => null),
    ]);

    const displayName = user && user.username && user.username !== "anonymous"
      ? user.username
      : username;

    announce(`Signed in as ${displayName}`);
    statusEl.textContent = `API verified — opening MAI…`;
    await delay(400);
    window.location.href = nextPath;
  } catch (error) {
    statusEl.hidden = true;
    if (mode === "register" && error?.status === 409) {
      showError("That username is already taken.");
    } else {
      showError(error?.message || "Sign in failed. Check your connection and try again.");
    }
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

modeToggle.addEventListener("click", () => setMode(mode === "login" ? "register" : "login"));

(async () => {
  if (!isAuthenticated()) return;
  try {
    const user = await me({ redirectOnFail: false });
    if (user && user.username && user.username !== "anonymous") {
      announce(`Resuming session for ${user.username}`);
      await delay(200);
      window.location.href = nextPath;
    }
  } catch {
    logout();
  }
})();