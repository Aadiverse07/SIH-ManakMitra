// Public browser configuration only. NEVER put service-role or LLM secrets here.
//
// SECURITY: MM_SUPABASE_ANON_KEY must be the Supabase *anon/public* key
// (Project Settings -> API -> "anon public"), never the service_role key.
// The service_role key bypasses Row Level Security and must stay on the
// backend only (see backend/.env.example / SUPABASE_SERVICE_ROLE_KEY).
// No key is hardcoded here — set window.MM_SUPABASE_URL and
// window.MM_SUPABASE_ANON_KEY before this script loads (e.g. from a
// non-committed config include) or auth features will simply stay disabled.
window.MM_API_BASE = window.MM_API_BASE || "http://localhost:8000";
window.MM_SUPABASE_URL = window.MM_SUPABASE_URL || "";
window.MM_SUPABASE_ANON_KEY = window.MM_SUPABASE_ANON_KEY || "";
// Set the two values above (e.g. via a non-committed config include, or by
// templating this file at deploy time) using your Supabase project's URL
// and *anon/public* key only. Never paste a "sb_secret_..." key here.
