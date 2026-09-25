const ICONS = {
  home: '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  chat: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-3.8-.9L3 20l1.05-3.9A8.4 8.4 0 0 1 3 11.5 8.5 8.5 0 0 1 11.5 3 8.5 8.5 0 0 1 21 11.5Z"/>',
  services: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  docs: '<path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 5v5h5"/><path d="M12 7v5l4 2"/>',
  saved: '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  mic: '<path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"/><path d="M19 11a7 7 0 0 1-14 0"/><path d="M12 18v3"/>',
  send: '<path d="m3 11 18-8-8 18-2-8-8-2Z"/>',
  bookmark: '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1Z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  research: '<path d="M9 3h6l1 4h3l-2 14H7L5 7h3l1-4Z"/><path d="M9 11h6M9 15h6"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  chevron: '<path d="m15 18-6-6 6-6"/>',
  feedback: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 8.4 8.4 0 0 1-3.8-.9L3 20l1.05-3.9A8.4 8.4 0 0 1 3 11.5 8.5 8.5 0 0 1 11.5 3 8.5 8.5 0 0 1 21 11.5Z"/><path d="M8.5 12h.01M12 12h.01M15.5 12h.01"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
};
function icon(name, cls){ return `<svg class="icon ${cls||''}" viewBox="0 0 24 24">${ICONS[name]||''}</svg>`; }

const NAV_MAIN = [
  { href: "index.html", label: "Home" },
  { href: "standards.html", label: "Standards" },
  { href: "services.html", label: "BIS Services" },
  { href: "assistant.html", label: "Ask ManakMitra" },
  { href: "resources.html", label: "Resources" },
  { href: "about.html", label: "About BIS" },
];

const SIDE_NAV = [
  { href: "dashboard.html", label: "Dashboard", icon: "home" },
  { href: "assistant.html", label: "Ask AI", icon: "chat" },
  { href: "research.html", label: "Research Centre", icon: "research" },
  { href: "standards.html", label: "Standards", icon: "search" },
  { href: "services.html", label: "BIS Services", icon: "services" },
  { href: "resources.html", label: "My Documents", icon: "docs" },
  { href: "history.html", label: "History", icon: "history" },
  { href: "saved.html", label: "Saved", icon: "saved" },
  { href: "feedback.html", label: "Feedback & Contact", icon: "feedback" },
];

function currentPage(){ return (location.pathname.split("/").pop() || "index.html"); }

function renderTopnav(){
  const mount = document.getElementById("site-topnav");
  if(!mount) return;
  const page = currentPage();
  mount.innerHTML = `
  <div class="container">
    <a href="index.html" class="brand">
      <span class="brand-mark">M</span>
      <span>ManakMitra<small>AI Assistant for Standards &amp; BIS</small></span>
    </a>
    <nav class="nav-links">
      ${NAV_MAIN.map(n => `<a href="${n.href}" class="${page===n.href?'is-active':''}">${n.label}</a>`).join("")}
    </nav>
    <div class="nav-right">
      <button class="icon-btn" id="theme-toggle" title="Toggle theme" aria-label="Toggle theme">${icon("moon")}</button>
      <button class="icon-btn" id="hamburger-btn" title="Menu" aria-label="Menu" style="display:none">${icon("menu")}</button>
      <a href="dashboard.html" class="userchip" id="user-chip">
        <span class="avatar">U</span>
        <span class="who"><b>Hi, User</b><span>Premium</span></span>
      </a>
    </div>
  </div>`;
}

function renderSidebar(activeHref, crumb){
  const mount = document.getElementById("site-sidebar");
  if(!mount) return;
  mount.innerHTML = `
    <div class="sidebar-controls">
      <span class="sidebar-section-label">Workspace</span>
      <button type="button" class="sidebar-toggle" id="sidebar-toggle" aria-label="Hide sidebar modules" title="Hide modules">
        ${icon("chevron")}
      </button>
    </div>
    <div class="sidebar-nav-items">
      ${SIDE_NAV.map(n => `<a href="${n.href}" class="sidenav-link ${activeHref===n.href?'is-active':''}">${icon(n.icon)}<span class="label-text">${n.label}</span></a>`).join("")}
    </div>
    <div class="sidebar-spacer"></div>
    <hr/>
    <div id="sidebar-auth-actions">
      <a href="settings.html" class="sidenav-link">${icon("settings")}<span class="label-text">Settings</span></a>
      <a href="#" class="sidenav-link" id="nav-login-link">${icon("logout")}<span class="label-text">Logout</span></a>
    </div>
  `;
  // The sidebar is rendered by each page's own DOMContentLoaded handler, which
  // runs after this file's handler, so wire it up here instead.
  initSidebarToggle();
  if(typeof refreshAuthUI === "function") refreshAuthUI();
}

function renderFooter(){
  const mount = document.getElementById("site-footer");
  if(!mount) return;
  mount.innerHTML = `
  <div class="container">
    <div class="footer-grid">
      <div>
        <div class="brand" style="margin-bottom:14px;">
          <span class="brand-mark">M</span>
          <span>ManakMitra<small>AI Assistant for Standards &amp; BIS</small></span>
        </div>
        <p class="muted" style="font-size:13.3px; line-height:1.6; max-width:320px;">
          An independent, AI-powered companion for exploring Indian Standards and Bureau of Indian Standards (BIS) services — built as a concept UI, not an official BIS product.
        </p>
      </div>
      <div>
        <h4>Explore</h4>
        <a href="standards.html">Standards Search</a>
        <a href="services.html">BIS Services</a>
        <a href="certification.html">Product Certification</a>
        <a href="assistant.html">Ask ManakMitra</a>
      </div>
      <div>
        <h4>Resources</h4>
        <a href="resources.html">FAQs</a>
        <a href="resources.html#labs">Recognised Labs</a>
        <a href="about.html">About BIS</a>
        <a href="resources.html#downloads">Downloads</a>
      </div>
      <div>
        <h4>Contact</h4>
        <a href="#">Manak Bhawan, 9 Bahadur Shah Zafar Marg, New Delhi 110002</a>
        <a href="#">bis-hq@bis.gov.in</a>
        <a href="#">1800-11-3005 (Toll free)</a>
        <a href="feedback.html">Feedback &amp; Contact form</a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© 2026 ManakMitra — concept interface, not affiliated with the Government of India.</span>
      <span>Made for demonstration · Data is illustrative</span>
    </div>
  </div>`;
}

function initTheme(){
  const saved = localStorage.getItem("mm-theme");
  const isLight = saved ? saved === "light" : true;
  if(isLight) document.documentElement.classList.add("light");
  const btn = document.getElementById("theme-toggle");
  if(!btn) return;
  btn.innerHTML = document.documentElement.classList.contains("light") ? icon("moon") : icon("sun");
  btn.addEventListener("click", () => {
    const isLight = document.documentElement.classList.toggle("light");
    localStorage.setItem("mm-theme", isLight ? "light" : "dark");
    btn.innerHTML = isLight ? icon("moon") : icon("sun");
  });
}

function initMobileNav(){
  const hb = document.getElementById("hamburger-btn");
  const links = document.querySelector(".nav-links");
  if(!hb || !links) return;
  function sync(){
    if(window.innerWidth <= 980){ hb.style.display = "flex"; }
    else { hb.style.display = "none"; links.classList.remove("mobile-open"); }
  }
  window.addEventListener("resize", sync); sync();
  hb.addEventListener("click", () => {
    const open = links.classList.toggle("mobile-open");
    if(open){
      Object.assign(links.style, { display:"flex", flexDirection:"column", position:"absolute", top:"var(--topbar-h)", left:"0", right:"0", background:"var(--surface-solid)", padding:"14px 20px", borderBottom:"1px solid var(--border)" });
      hb.innerHTML = icon("x");
    } else {
      links.style.display = "none"; hb.innerHTML = icon("menu");
    }
  });
}

function initSidebarToggle(){
  const sidebar = document.getElementById("site-sidebar");
  const btn = document.getElementById("sidebar-toggle");
  if(!sidebar || !btn) return;
  const key = "mm-sidebar-collapsed";
  const apply = collapsed => {
    sidebar.classList.toggle("is-collapsed", collapsed);
    btn.setAttribute("aria-expanded", String(!collapsed));
    btn.setAttribute("aria-label", collapsed ? "Show sidebar modules" : "Hide sidebar modules");
    btn.title = collapsed ? "Show modules" : "Hide modules";
    btn.innerHTML = icon("chevron");
  };
  apply(localStorage.getItem(key) === "1");
  btn.addEventListener("click", () => {
    const collapsed = !sidebar.classList.contains("is-collapsed");
    localStorage.setItem(key, collapsed ? "1" : "0");
    apply(collapsed);
  });
}

function showToast(msg){
  let t = document.querySelector(".toast");
  if(!t){ t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2600);
}

document.addEventListener("DOMContentLoaded", () => {
  renderTopnav();
  renderFooter();
  initTheme();
  initMobileNav();
});
