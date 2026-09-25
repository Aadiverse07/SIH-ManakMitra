const MM_API_BASE = window.MM_API_BASE || "http://localhost:8000";

let STANDARDS = [];
let SERVICES = [];
let FAQS = [];
let LABS = [];
let CERT_STEPS = [];

/* The browser throws a bare TypeError ("Failed to fetch" / "NetworkError" /
 * "Load failed") when it can't even reach the server — wrong port, backend
 * not started, no internet, CORS block, etc. That's different from the
 * backend responding with an error, so it gets its own, clearer message
 * instead of the raw browser text leaking into the UI. */
function mmIsNetworkError(err) {
  return err instanceof TypeError || /failed to fetch|networkerror|load failed|network request failed/i.test(err?.message || "");
}
function mmNetworkErrorMessage(context) {
  return `Can't reach the ManakMitra server at ${MM_API_BASE}${context ? ` to ${context}` : ""}. Make sure the backend is running and reachable, then try again.`;
}

async function mmApiGet(path) {
  let res;
  try {
    res = await fetch(`${MM_API_BASE}${path}`);
  } catch (err) {
    throw mmIsNetworkError(err) ? new Error(mmNetworkErrorMessage()) : err;
  }
  if (!res.ok) throw new Error(`${path} responded ${res.status}`);
  return res.json();
}

function mmShowLoadError(containerId, label) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="card" style="padding:26px; text-align:center;">
      <p class="muted" style="font-size:13.5px; margin:0;">
        Couldn't load ${label} right now — check your connection and try again.
      </p>
    </div>`;
}

const MM_LOADERS = {
  standards: async () => { STANDARDS = await mmApiGet("/standards"); },
  services: async () => { SERVICES = await mmApiGet("/services"); },
  faqs: async () => { FAQS = await mmApiGet("/faqs"); },
  labs: async () => { LABS = await mmApiGet("/labs"); },
  cert_steps: async () => { CERT_STEPS = await mmApiGet("/cert-steps"); },
};

async function mmLoadData(keys) {
  const failed = {};
  await Promise.all(
    keys.map(async (key) => {
      const loader = MM_LOADERS[key];
      if (!loader) { console.error(`Unknown data key: ${key}`); return; }
      try {
        await loader();
      } catch (err) {
        console.error(`Failed to load ${key} from ${MM_API_BASE}`, err);
        failed[key] = true;
      }
    })
  );
  return failed;
}

async function mmSearchStandards(q, category) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category && category !== "all") params.set("category", category);
  const qs = params.toString();
  return mmApiGet(`/search${qs ? `?${qs}` : ""}`).then(r => r.results || []);
}

async function mmGetLicense(number) {
  return mmApiGet(`/licenses/${encodeURIComponent(number)}`);
}

async function mmChat(message, conversationId = null, metadata = {}) {
  let accessToken = null;
  try {
    if (window.MM_AUTH && typeof MM_AUTH.getAccessToken === "function") {
      accessToken = await MM_AUTH.getAccessToken();
    }
  } catch (_) {}
  let res;
  try {
    res = await fetch(`${MM_API_BASE}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { "Authorization": `Bearer ${accessToken}` } : {})
      },
      body: JSON.stringify({
        message,
        ...(conversationId ? { conversation_id: conversationId } : {}),
        ...(metadata && metadata.language ? { language: metadata.language } : {}),
        ...(metadata && metadata.input_type ? { input_type: metadata.input_type } : {}),
      }),
    });
  } catch (err) {
    throw mmIsNetworkError(err) ? new Error(mmNetworkErrorMessage("chat")) : err;
  }
  if (!res.ok) {
    let detail = `/chat responded ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}


async function mmApiAuthRequest(path, options = {}) {
  let accessToken = null;
  try {
    if (window.MM_AUTH && typeof MM_AUTH.getAccessToken === "function") {
      accessToken = await MM_AUTH.getAccessToken();
    }
  } catch (_) {}
  if (!accessToken) throw new Error("Please sign in to manage documents.");
  let res;
  try {
    res = await fetch(`${MM_API_BASE}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        "Authorization": `Bearer ${accessToken}`,
      },
    });
  } catch (err) {
    throw mmIsNetworkError(err) ? new Error(mmNetworkErrorMessage()) : err;
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const body = await res.json(); if(body?.detail) detail = typeof body.detail === "string" ? body.detail : (body.detail.message || detail); } catch (_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function mmListDocuments() { return mmApiAuthRequest("/documents"); }
async function mmUploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return mmApiAuthRequest("/documents/upload", { method: "POST", body: form });
}
async function mmGetDocument(id) { return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}`); }
async function mmGetDocumentPages(id) { return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}/pages`); }
async function mmSearchDocument(id, q) {
  return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}/search?q=${encodeURIComponent(q)}`);
}
async function mmProcessDocument(id) {
  return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}/process`, { method: "POST" });
}
async function mmGetStructuredDocument(id) { return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}/structured`); }
async function mmGetStandardGraph(number, relationshipType=null) {
  const qs = relationshipType ? `?relationship_type=${encodeURIComponent(relationshipType)}` : "";
  return mmApiGet(`/graph/standards/${encodeURIComponent(number)}${qs}`);
}
async function mmGetDocumentGraph(id) { return mmApiAuthRequest(`/graph/documents/${encodeURIComponent(id)}`); }
async function mmSearchStructuredDocument(id, q, entity="all") {
  return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}/structured/search?q=${encodeURIComponent(q)}&entity=${encodeURIComponent(entity)}`);
}
async function mmDeleteDocument(id) {
  return mmApiAuthRequest(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

window.MM_DATA = {
  load: mmLoadData,
  searchStandards: mmSearchStandards,
  getLicense: mmGetLicense,
  chat: mmChat,
  showLoadError: mmShowLoadError,
  apiGet: mmApiGet,
  listDocuments: mmListDocuments,
  uploadDocument: mmUploadDocument,
  getDocument: mmGetDocument,
  getDocumentPages: mmGetDocumentPages,
  searchDocument: mmSearchDocument,
  processDocument: mmProcessDocument,
  getStructuredDocument: mmGetStructuredDocument,
  searchStructuredDocument: mmSearchStructuredDocument,
  getStandardGraph: mmGetStandardGraph,
  getDocumentGraph: mmGetDocumentGraph,
  deleteDocument: mmDeleteDocument,
};

async function mmCertificationRequest(path, options = {}) {
  let accessToken = null;
  try {
    if (window.MM_AUTH && typeof MM_AUTH.getAccessToken === "function") {
      accessToken = await MM_AUTH.getAccessToken();
    }
  } catch (_) {}
  if (!accessToken) throw new Error("Please sign in to start a certification application.");
  let res;
  try {
    res = await fetch(`${MM_API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
        "Authorization": `Bearer ${accessToken}`,
      },
    });
  } catch (err) {
    if (mmIsNetworkError(err)) {
      const wrapped = new Error(mmNetworkErrorMessage("save your certification application"));
      wrapped.isNetworkError = true;
      throw wrapped;
    }
    throw err;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.detail || `Request failed (${res.status})`);
  return body;
}

/* Local draft fallback: used only when the ManakMitra backend can't be
 * reached, so a certification application in progress isn't blocked or lost
 * while the server is down. Local drafts get an id prefixed "local-" and are
 * kept in this browser only, per MM_CERT_LOCAL_KEY, until the server is back. */
const MM_CERT_LOCAL_KEY = "mm-certification-applications-local";

function mmCertLocalList() {
  try {
    const raw = JSON.parse(localStorage.getItem(MM_CERT_LOCAL_KEY) || "[]");
    return Array.isArray(raw) ? raw : [];
  } catch (_) { return []; }
}
function mmCertLocalSave(list) {
  try { localStorage.setItem(MM_CERT_LOCAL_KEY, JSON.stringify(list)); } catch (_) {}
}
function mmCertLocalId() {
  return "local-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
}
function mmCertLocalNumber() {
  const d = new Date();
  const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
  const rand = Math.random().toString(16).slice(2, 8).toUpperCase();
  return `MM-BIS-${ymd}-${rand}`;
}

async function mmListCertificationApplications() {
  try {
    return await mmCertificationRequest("/certification-applications");
  } catch (err) {
    if (!err.isNetworkError) throw err;
    return mmCertLocalList().sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  }
}
async function mmCreateCertificationApplication(payload) {
  try {
    return await mmCertificationRequest("/certification-applications", { method: "POST", body: JSON.stringify(payload) });
  } catch (err) {
    if (!err.isNetworkError) throw err;
    const now = new Date().toISOString();
    const record = { ...payload, id: mmCertLocalId(), application_number: mmCertLocalNumber(), created_at: now, updated_at: now, _local: true };
    const list = mmCertLocalList(); list.unshift(record); mmCertLocalSave(list);
    if (typeof showToast === "function") showToast("Server unreachable — saved this draft locally on this device instead.");
    return record;
  }
}
async function mmUpdateCertificationApplication(id, payload) {
  if (String(id).startsWith("local-")) {
    const list = mmCertLocalList();
    const idx = list.findIndex(a => a.id === id);
    const updated = { ...(idx > -1 ? list[idx] : {}), ...payload, id, updated_at: new Date().toISOString() };
    if (idx > -1) list[idx] = updated; else list.unshift(updated);
    mmCertLocalSave(list);
    return updated;
  }
  try {
    return await mmCertificationRequest(`/certification-applications/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) });
  } catch (err) {
    if (!err.isNetworkError) throw err;
    const now = new Date().toISOString();
    const record = { ...payload, id: mmCertLocalId(), application_number: payload.application_number || mmCertLocalNumber(), created_at: now, updated_at: now, _local: true };
    const list = mmCertLocalList(); list.unshift(record); mmCertLocalSave(list);
    if (typeof showToast === "function") showToast("Server unreachable — continuing on a local draft saved to this device.");
    return record;
  }
}
async function mmEmailCertificationApplication(id) {
  if (String(id).startsWith("local-")) {
    return { sent: false, message: "This draft is only saved locally (the ManakMitra server was unreachable), so it can't be emailed yet. Try again once the server is back up." };
  }
  try {
    return await mmCertificationRequest(`/certification-applications/${encodeURIComponent(id)}/email`, { method: "POST", body: JSON.stringify({}) });
  } catch (err) {
    if (err.isNetworkError) return { sent: false, message: err.message };
    throw err;
  }
}

Object.assign(window.MM_DATA, {
  listCertificationApplications: mmListCertificationApplications,
  createCertificationApplication: mmCreateCertificationApplication,
  updateCertificationApplication: mmUpdateCertificationApplication,
  emailCertificationApplication: mmEmailCertificationApplication,
});

async function mmResearchRequest(path, options = {}) {
  let accessToken = null;
  try { if (window.MM_AUTH && typeof MM_AUTH.getAccessToken === "function") accessToken = await MM_AUTH.getAccessToken(); } catch (_) {}
  if (!accessToken) throw new Error("Please sign in to use Research Centre.");
  let res;
  try {
    res = await fetch(`${MM_API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}), "Authorization": `Bearer ${accessToken}` },
    });
  } catch (err) {
    throw mmIsNetworkError(err) ? new Error(mmNetworkErrorMessage("run this research task")) : err;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body?.detail === "string" ? body.detail : `Research request failed (${res.status})`);
  return body;
}
async function mmRunResearch(payload) { return mmResearchRequest("/research/run", { method:"POST", body: JSON.stringify(payload) }); }
async function mmCompareStandards(payload) { return mmResearchRequest("/research/compare", { method:"POST", body: JSON.stringify(payload) }); }
async function mmListResearch() { return mmResearchRequest("/research"); }
async function mmGetResearch(id) { return mmResearchRequest(`/research/${encodeURIComponent(id)}`); }
async function mmDeleteResearch(id) {
  return mmResearchRequest(`/research/${encodeURIComponent(id)}`, { method:"DELETE" });
}
Object.assign(window.MM_DATA, { runResearch: mmRunResearch, compareStandards: mmCompareStandards, listResearch: mmListResearch, getResearch: mmGetResearch, deleteResearch: mmDeleteResearch });
