// Public browser configuration only. NEVER put service-role or LLM secrets here.
//
// SECURITY: MM_SUPABASE_ANON_KEY must be the Supabase *anon/public* key
// (Project Settings -> API -> "anon public"), never the service_role key.
// The service_role key bypasses Row Level Security and must stay on the
// backend only (see backend/.env.example / SUPABASE_SERVICE_ROLE_KEY).
// No key is hardcoded here — set window.MM_SUPABASE_URL and
// window.MM_SUPABASE_ANON_KEY before this script loads (e.g. from a
// non-committed config include) or auth features will simply stay disabled.
window.MM_API_BASE = "https://sih-manakmitra-2.onrender.com";
window.MM_SUPABASE_URL = "https://swzbglmhifrtbwswpzxs.supabase.co";
window.MM_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN3emJnbG1oaWZydGJ3c3dwenhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3MTMwNTQsImV4cCI6MjEwNDI4OTA1NH0.p3q2YwiBmd3YRvZ-12SoXIFTqKqkjzxFHdCQQV6Hmd4";
// Set the two values above (e.g. via a non-committed config include, or by
// templating this file at deploy time) using your Supabase project's URL
// and *anon/public* key only. Never paste a "sb_secret_..." key here.
