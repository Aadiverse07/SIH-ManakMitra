const MM_ALLOWED_EMAIL_DOMAINS = ["gmail.com", "outlook.com", "aol.com", "yahoo.com", "icloud.com"];
const MM_FREE_QUERY_LIMIT = 3;

// SECURITY: this must be the Supabase anon/public key only. Never hardcode a
// service_role key here — it would give every visitor full, RLS-bypassing
// admin access to the database. See js/config.js for where these are set.
const MM_SUPABASE_URL = window.MM_SUPABASE_URL || "";
const MM_SUPABASE_ANON_KEY = window.MM_SUPABASE_ANON_KEY || "";
let MM_AUTH_CONFIGURED = !!(MM_SUPABASE_URL && MM_SUPABASE_ANON_KEY && window.supabase);

let sb = null;
if(MM_AUTH_CONFIGURED){
  try {
    sb = window.supabase.createClient(MM_SUPABASE_URL, MM_SUPABASE_ANON_KEY);
  } catch(err){
    // Newer supabase-js versions refuse to run with a secret/service_role key
    // in the browser. Use the anon/public key in js/config.js instead.
    console.error("ManakMitra: Supabase client failed to initialise -- check MM_SUPABASE_ANON_KEY is the anon/public key.", err);
    MM_AUTH_CONFIGURED = false;
  }
}

function mmEscape(s){
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}

function mmToE164(tenDigit){ return "+91" + String(tenDigit || "").trim(); }
function mmFromE164(phone){ return String(phone || "").replace(/^\+91/, ""); }

let mmCurrentUser = null;

function mapSupabaseUser(user){
  if(!user) return null;
  const provider = user.phone ? "phone" : "email";
  return {
    id: user.id,
    name: user.user_metadata?.full_name || (user.email ? user.email.split("@")[0] : "User"),
    email: user.email || "",
    phone: mmFromE164(user.phone || ""),
    provider,
  };
}

async function getAccessToken(){
  if(!MM_AUTH_CONFIGURED) return null;
  const { data } = await sb.auth.getSession();
  return data?.session?.access_token || null;
}

function getCurrentUser(){ return mmCurrentUser; }
function isLoggedIn(){ return !!mmCurrentUser; }

const mmAuthReady = (async () => {
  if(!MM_AUTH_CONFIGURED) return;
  const { data } = await sb.auth.getSession();
  mmCurrentUser = mapSupabaseUser(data?.session?.user);
  refreshAuthUI();
})();

if(MM_AUTH_CONFIGURED){
  sb.auth.onAuthStateChange((event, session) => {
    mmCurrentUser = mapSupabaseUser(session?.user);
    localStorage.removeItem("mm-query-count");
    refreshAuthUI();
    if(event === "SIGNED_IN" && session?.user) mmLogLoginEvent(session.user);
  });
}

async function mmLogLoginEvent(user){
  if(!MM_AUTH_CONFIGURED) return;
  try {
    const provider = user.phone ? "phone" : "email";
    await sb.from("login_events").insert({ user_id: user.id, provider });
  } catch(err){
    console.warn("ManakMitra: couldn't record login event", err);
  }
}

async function doLogout(){
  if(MM_AUTH_CONFIGURED) await sb.auth.signOut();
  mmCurrentUser = null;
  refreshAuthUI();
  if(typeof showToast === "function") showToast("Logged out");
}

function emailDomainOk(email){
  const m = /@([^@\s]+)$/.exec(String(email || "").trim());
  return !!m && MM_ALLOWED_EMAIL_DOMAINS.includes(m[1].toLowerCase());
}
function phoneOk(phone){ return /^[6-9]\d{9}$/.test(String(phone || "").trim()); }

const MM_ALREADY_REGISTERED_MSG = "Try again — an account is already associated with this email/number.";
const MM_PHONE_ALREADY_REGISTERED_MSG = "Account is already registered with this number";

async function mmCheckAvailability({ email, phone } = {}){
  const base = window.MM_API_BASE || "";
  if(!base || (!email && !phone)) return { email_taken: false, phone_taken: false };
  try {
    const params = new URLSearchParams();
    if(email) params.set("email", email);
    if(phone) params.set("phone", phone);
    const res = await fetch(`${base}/auth/availability?${params.toString()}`);
    if(!res.ok) return { email_taken: false, phone_taken: false };
    return await res.json();
  } catch(err){
    console.warn("ManakMitra: availability check failed", err);
    return { email_taken: false, phone_taken: false };
  }
}

function mmFriendlyAuthError(message){
  const msg = String(message || "");
  if(/unsupported phone provider/i.test(msg)){
    return "Phone sign-in isn't set up on this project yet (no SMS provider configured). This needs the project owner to enable Phone auth under Supabase Dashboard \u2192 Authentication \u2192 Sign In / Providers \u2192 Phone, with an SMS provider (e.g. MSG91, Twilio) connected -- please use Email instead for now.";
  }
  return msg;
}

function mmQueryCount(){ return parseInt(localStorage.getItem("mm-query-count") || "0", 10); }

function mmRegisterQuery(){
  if(isLoggedIn()) return true;
  const count = mmQueryCount();
  if(count >= MM_FREE_QUERY_LIMIT){
    openAuthModal("login", "Login to continue using ManakAiAssistant");
    return false;
  }
  localStorage.setItem("mm-query-count", String(count + 1));
  return true;
}

let authState = { mode: "login", tab: "email", reason: "", busy: false };

function ensureAuthModalMounted(){
  if(document.getElementById("auth-modal")) return;
  const wrap = document.createElement("div");
  wrap.className = "modal-backdrop";
  wrap.id = "auth-modal";
  wrap.innerHTML = `<div class="modal-box auth-box"><span class="modal-close" id="auth-modal-close">\u2715</span><div id="auth-modal-body"></div></div>`;
  document.body.appendChild(wrap);
  document.getElementById("auth-modal-close").addEventListener("click", closeAuthModal);
  wrap.addEventListener("click", e => { if(e.target.id === "auth-modal") closeAuthModal(); });
}

function openAuthModal(mode, reason){
  ensureAuthModalMounted();
  authState = { mode: mode || "login", tab: "email", reason: reason || "", busy: false };
  renderAuthModal();
  document.getElementById("auth-modal").classList.add("show");
}
function closeAuthModal(){
  const m = document.getElementById("auth-modal");
  if(m) m.classList.remove("show");
}

function authBodyHtml(){
  const s = authState;
  const isSignup = s.mode === "signup";

  const banner = s.reason ? `<div class="auth-banner">${mmEscape(s.reason)}</div>` : "";
  const configWarning = MM_AUTH_CONFIGURED ? "" : `<div class="auth-banner">Auth isn't configured yet -- set MM_SUPABASE_URL / MM_SUPABASE_ANON_KEY (see the top of js/auth.js).</div>`;

  const panel = `
    <form class="auth-panel" id="auth-email-form" novalidate>
      ${isSignup ? `<div><label class="label">Full name</label><div class="field"><input required id="auth-name" placeholder="Your name" autocomplete="name"></div></div>` : ""}
      <div><label class="label">Email</label><div class="field"><input required type="email" id="auth-email" placeholder="you@gmail.com" autocomplete="email"></div></div>
      <div><label class="label">Password</label><div class="field"><input required type="password" id="auth-password" placeholder="••••••••" minlength="6" autocomplete="${isSignup?'new-password':'current-password'}"></div></div>
      ${isSignup ? `<div><label class="label">Confirm password</label><div class="field"><input required type="password" id="auth-password2" placeholder="••••••••" autocomplete="new-password"></div></div>` : ""}
      <p class="auth-note">Accepted domains: ${MM_ALLOWED_EMAIL_DOMAINS.join(", ")}</p>
      <div class="auth-error" id="auth-email-error"></div>
      <button type="submit" class="btn btn-primary" style="width:100%;" ${s.busy?"disabled":""}>${isSignup ? "Create account" : "Log in"}</button>
    </form>`;


  const switchLine = isSignup
    ? `<p class="auth-switch">Already have an account? <a href="#" id="auth-switch-link">Log in</a></p>`
    : `<p class="auth-switch">New user? <a href="#" id="auth-switch-link">Create your account here</a></p>`;

  return `
    <div class="auth-head">
      <div class="brand" style="justify-content:center; margin-bottom:8px;"><span class="brand-mark">M</span><span class="mm-shimmer-text">ManakMitra</span></div>
      <h2 class="auth-title" id="auth-title-text">${isSignup ? "Create your account" : "Welcome back"}</h2>
      <p class="muted auth-sub">${isSignup ? "Sign up to unlock unlimited ManakAiAssistant queries." : "Log in to keep chatting with ManakAiAssistant."}</p>
    </div>
    ${configWarning}
    ${banner}
    ${panel}
    ${switchLine}
  `;
}

function renderAuthModal(){
  document.getElementById("auth-modal-body").innerHTML = authBodyHtml();
  if(typeof mmRevealText === "function") mmRevealText(document.getElementById("auth-title-text"));
  bindAuthModalEvents();
}

function mmAuthFail(elId, message){
  authState.busy = false;
  const el = document.getElementById(elId);
  if(el) el.textContent = message;
  const btn = document.querySelector("#auth-modal button[type=submit]");
  if(btn) btn.disabled = false;
}

function bindAuthModalEvents(){
  document.getElementById("auth-switch-link")?.addEventListener("click", e => {
    e.preventDefault();
    authState.mode = authState.mode === "login" ? "signup" : "login";
    renderAuthModal();
  });

  document.getElementById("auth-email-form")?.addEventListener("submit", async e => {
    e.preventDefault();
    if(!MM_AUTH_CONFIGURED){ mmAuthFail("auth-email-error", "Auth isn't configured yet -- see js/auth.js."); return; }
    const errEl = document.getElementById("auth-email-error");
    errEl.textContent = "";
    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value;

    if(!emailDomainOk(email)){
      errEl.textContent = `Please use an email ending in ${MM_ALLOWED_EMAIL_DOMAINS.join(", ")}.`;
      return;
    }

    authState.busy = true;
    e.target.querySelector("button[type=submit]").disabled = true;

    if(authState.mode === "signup"){
      const name = document.getElementById("auth-name").value.trim();
      const password2 = document.getElementById("auth-password2").value;
      if(!name){ mmAuthFail("auth-email-error", "Please enter your name."); return; }
      if(password.length < 6){ mmAuthFail("auth-email-error", "Password must be at least 6 characters."); return; }
      if(password !== password2){ mmAuthFail("auth-email-error", "Passwords do not match."); return; }

      const { email_taken } = await mmCheckAvailability({ email });
      if(email_taken){ mmAuthFail("auth-email-error", MM_ALREADY_REGISTERED_MSG); return; }

      const { data, error } = await sb.auth.signUp({
        email, password,
        options: { data: { full_name: name } },
      });
      if(error){ mmAuthFail("auth-email-error", mmFriendlyAuthError(error.message)); return; }
      if(data.user && Array.isArray(data.user.identities) && data.user.identities.length === 0){
        mmAuthFail("auth-email-error", MM_ALREADY_REGISTERED_MSG);
        return;
      }
      if(!data.session){
        authState.busy = false;
        closeAuthModal();
        if(typeof showToast === "function") showToast(`Check ${email} for a confirmation link to finish creating your account.`);
        return;
      }
      closeAuthModal();
      if(typeof showToast === "function") showToast(`Account created -- welcome, ${name}!`);
    } else {
      const { error } = await sb.auth.signInWithPassword({ email, password });
      if(error){ mmAuthFail("auth-email-error", mmFriendlyAuthError(error.message)); return; }
      closeAuthModal();
      if(typeof showToast === "function") showToast(`Welcome back!`);
    }
  });


}

let mmOtpPending = null; // { verify, resend, resolve }

function ensureOtpModalMounted(){
  if(document.getElementById("otp-modal")) return;
  const wrap = document.createElement("div");
  wrap.className = "modal-backdrop";
  wrap.id = "otp-modal";
  wrap.innerHTML = `
    <div class="modal-box">
      <span class="modal-close" id="otp-modal-close">\u2715</span>
      <h3 style="margin:0 0 6px;">Verify it's you</h3>
      <p class="muted" id="otp-modal-msg" style="font-size:13.3px; line-height:1.6;"></p>
      <div class="field" style="margin:14px 0 6px;"><input id="otp-modal-input" maxlength="6" inputmode="numeric" placeholder="6-digit code"></div>
      <div class="auth-error" id="otp-modal-error"></div>
      <button class="btn btn-primary" style="width:100%; margin-top:6px;" id="otp-modal-verify">Verify</button>
      <button class="btn btn-ghost btn-sm" style="width:100%; margin-top:8px;" id="otp-modal-resend">Resend code</button>
    </div>`;
  document.body.appendChild(wrap);
  document.getElementById("otp-modal-close").addEventListener("click", () => closeOtpModal(false));
  wrap.addEventListener("click", e => { if(e.target.id === "otp-modal") closeOtpModal(false); });

  document.getElementById("otp-modal-verify").addEventListener("click", async () => {
    if(!mmOtpPending) return;
    const code = document.getElementById("otp-modal-input").value.trim();
    const errEl = document.getElementById("otp-modal-error");
    errEl.textContent = "";
    const btn = document.getElementById("otp-modal-verify");
    btn.disabled = true;
    const { ok, error } = await mmOtpPending.verify(code);
    btn.disabled = false;
    if(ok) closeOtpModal(true);
    else errEl.textContent = error || "Incorrect code. Please try again.";
  });

  document.getElementById("otp-modal-resend").addEventListener("click", async () => {
    if(!mmOtpPending?.resend) return;
    const { error } = await mmOtpPending.resend();
    if(typeof showToast === "function") showToast(error ? error.message : "A new code has been sent.");
  });
}

function openOtpModal({ message, verify, resend }){
  return new Promise(resolve => {
    ensureOtpModalMounted();
    document.getElementById("otp-modal-msg").textContent = message || "";
    document.getElementById("otp-modal-input").value = "";
    document.getElementById("otp-modal-error").textContent = "";
    document.getElementById("otp-modal").classList.add("show");
    mmOtpPending = { verify, resend, resolve };
  });
}
function closeOtpModal(verified){
  document.getElementById("otp-modal").classList.remove("show");
  const pending = mmOtpPending;
  mmOtpPending = null;
  if(pending) pending.resolve(verified);
}

async function mmLogProfileChange(field, oldValue, newValue){
  if(!MM_AUTH_CONFIGURED || !mmCurrentUser) return;
  try {
    await sb.from("profile_change_history").insert({
      user_id: mmCurrentUser.id,
      field,
      old_value: field === "password" ? null : (oldValue ?? null),
      new_value: field === "password" ? null : (newValue ?? null),
    });
  } catch(err){
    console.warn("ManakMitra: couldn't record profile change history", err);
  }
}

async function mmUpdateName(name){
  if(!MM_AUTH_CONFIGURED) return { error: "Auth isn't configured." };
  const oldName = mmCurrentUser?.name;
  const { data, error } = await sb.auth.updateUser({ data: { full_name: name } });
  if(!error){
    mmCurrentUser = mapSupabaseUser(data.user);
    mmLogProfileChange("name", oldName, name);
  }
  return { error: error?.message };
}

async function mmUpdateEmail(newEmail){
  if(!MM_AUTH_CONFIGURED) return { error: "Auth isn't configured." };
  const { email_taken } = await mmCheckAvailability({ email: newEmail });
  if(email_taken) return { error: MM_ALREADY_REGISTERED_MSG };
  const { error } = await sb.auth.updateUser({ email: newEmail });
  return { error: error ? mmFriendlyAuthError(error.message) : undefined };
}
async function mmVerifyEmailChange(newEmail, token){
  const oldEmail = mmCurrentUser?.email;
  const { data, error } = await sb.auth.verifyOtp({ email: newEmail, token, type: "email_change" });
  if(!error){
    mmCurrentUser = mapSupabaseUser(data.user);
    mmLogProfileChange("email", oldEmail, newEmail);
  }
  return { ok: !error, error: error?.message };
}

async function mmUpdatePhone(newTenDigitPhone){
  if(!MM_AUTH_CONFIGURED) return { error: "Auth isn't configured." };
  const { phone_taken } = await mmCheckAvailability({ phone: newTenDigitPhone });
  if(phone_taken) return { error: MM_ALREADY_REGISTERED_MSG };
  const { error } = await sb.auth.updateUser({ phone: mmToE164(newTenDigitPhone) });
  return { error: error ? mmFriendlyAuthError(error.message) : undefined };
}
async function mmVerifyPhoneChange(newTenDigitPhone, token){
  const oldPhone = mmCurrentUser?.phone;
  const { data, error } = await sb.auth.verifyOtp({ phone: mmToE164(newTenDigitPhone), token, type: "phone_change" });
  if(!error){
    mmCurrentUser = mapSupabaseUser(data.user);
    mmLogProfileChange("phone", oldPhone, newTenDigitPhone);
  }
  return { ok: !error, error: error?.message };
}

async function mmChangePassword(currentPassword, newPassword){
  if(!MM_AUTH_CONFIGURED) return { error: "Auth isn't configured." };
  const user = getCurrentUser();
  if(!user?.email) return { error: "Password changes require an email-based account." };
  const { error: reauthError } = await sb.auth.signInWithPassword({ email: user.email, password: currentPassword });
  if(reauthError) return { error: "Current password is incorrect." };
  const { error } = await sb.auth.updateUser({ password: newPassword });
  if(!error) mmLogProfileChange("password", null, null);
  return { error: error?.message };
}

async function mmSaveChatMessage(role, content, conversationId = null){
  if(!MM_AUTH_CONFIGURED || !mmCurrentUser) return;
  try {
    // Phase 14: tag the row with conversation_id so the backend's
    // conversation-context lookup (filtered by conversation_id) can find it.
    // Rows saved without it are invisible to context resolution.
    const row = { user_id: mmCurrentUser.id, role, content };
    if(conversationId) row.conversation_id = conversationId;
    await sb.from("chat_messages").insert(row);
  } catch(err){
    console.warn("ManakMitra: couldn't save chat message", err);
  }
}

async function mmGetChatHistory(limit = 100){
  if(!MM_AUTH_CONFIGURED || !mmCurrentUser) return [];
  try {
    const { data, error } = await sb
      .from("chat_messages")
      .select("role, content, created_at")
      .eq("user_id", mmCurrentUser.id)
      .order("created_at", { ascending: false })
      .limit(limit);
    if(error) throw error;
    return (data || []).reverse();
  } catch(err){
    console.warn("ManakMitra: couldn't load chat history", err);
    return [];
  }
}

function refreshAuthUI(){
  const user = getCurrentUser();
  const chip = document.getElementById("user-chip");
  if(chip){
    const avatar = chip.querySelector(".avatar");
    const who = chip.querySelector(".who");
    if(user){
      chip.setAttribute("href", "settings.html");
      if(avatar) avatar.textContent = (user.name || "U").trim().charAt(0).toUpperCase();
      if(who) who.innerHTML = `<b>Hi, ${mmEscape((user.name || "User").split(" ")[0])}</b><span>Signed in</span>`;
    } else {
      chip.setAttribute("href", "#");
      if(avatar) avatar.textContent = "?";
      if(who) who.innerHTML = `<b>Guest</b><span>Log in</span>`;
    }
  }

  const actions = document.getElementById("sidebar-auth-actions");
  if(actions){
    const onSettings = typeof currentPage === "function" && currentPage() === "settings.html";
    const settingsLink = `<a href="settings.html" class="sidenav-link ${onSettings ? "is-active" : ""}">${typeof icon === "function" ? icon("settings") : ""}<span class="label-text">Settings</span></a>`;
    actions.innerHTML = user
      ? `${settingsLink}<a href="#" class="sidenav-link" id="nav-logout-link">${typeof icon === "function" ? icon("logout") : ""}<span class="label-text">Logout</span></a>`
      : `${settingsLink}<a href="#" class="sidenav-link" id="nav-login-link">${typeof icon === "function" ? icon("logout") : ""}<span class="label-text">Log in</span></a>`;
    document.getElementById("nav-logout-link")?.addEventListener("click", e => { e.preventDefault(); doLogout(); });
    document.getElementById("nav-login-link")?.addEventListener("click", e => { e.preventDefault(); openAuthModal("login"); });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  refreshAuthUI();
  document.getElementById("user-chip")?.addEventListener("click", e => {
    if(!isLoggedIn()){ e.preventDefault(); openAuthModal("login"); }
  });
});

window.MM_AUTH = {
  ready: mmAuthReady,
  isLoggedIn,
  getCurrentUser,
  getAccessToken,
  openAuthModal,
  closeAuthModal,
  logout: doLogout,
  registerQuery: mmRegisterQuery,
  openOtpModal,
  updateName: mmUpdateName,
  updateEmail: mmUpdateEmail,
  verifyEmailChange: mmVerifyEmailChange,
  updatePhone: mmUpdatePhone,
  verifyPhoneChange: mmVerifyPhoneChange,
  changePassword: mmChangePassword,
  saveChatMessage: mmSaveChatMessage,
  getChatHistory: mmGetChatHistory,
  emailDomainOk,
  phoneOk,
  checkAvailability: mmCheckAvailability,
  ALLOWED_EMAIL_DOMAINS: MM_ALLOWED_EMAIL_DOMAINS,
};
