#!/usr/bin/env node
// One-off migration: loads frontend/js/data.js and inserts it into the
// Postgres tables created by database/migrations/0001_init.sql.
//
// Usage:
//   cd database/scripts
//   npm install
//   cp ../../backend/.env.example .env   # fill in SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY
//   node migrate_data_js.js

const fs = require("fs");
const path = require("path");
const vm = require("vm");
require("dotenv").config();
const { createClient } = require("@supabase/supabase-js");

const DATA_JS_PATH = path.resolve(__dirname, "../../frontend/js/data.js");

function loadDataJs() {
  const code = fs.readFileSync(DATA_JS_PATH, "utf8");
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { filename: DATA_JS_PATH });
  const required = ["STANDARDS", "SERVICES", "FAQS", "LABS", "CERT_STEPS", "LICENSES"];
  const exported = vm.runInContext(`({ ${required.join(", ")} })`, sandbox, {
    filename: DATA_JS_PATH,
  });
  for (const name of required) {
    if (!Array.isArray(exported[name])) {
      throw new Error(`Expected ${DATA_JS_PATH} to define a top-level array called ${name}`);
    }
  }
  return exported;
}

function mapStandard(s) {
  return {
    is_number: s.number,
    title: s.title,
    description: s.desc || null,
    category: s.category || null,
    dept: s.dept || null,
    status: s.status || "Active",
    reaffirmed: s.reaffirmed ?? null,
    language: s.language || null,
    knowledge_status: "official_verified",
    source: "BIS public standards metadata / Know Your Standards",
    source_url: "https://www.services.bis.gov.in/",
  };
}

function mapService(sv) {
  return {
    id: sv.id,
    name: sv.name,
    summary: sv.summary || null,
    detail: sv.detail || null,
    icon: sv.icon || null,
    knowledge_status: "official_verified",
    source: "BIS public information used for the ManakMitra curated seed",
    source_url: "https://www.bis.gov.in/",
  };
}

function mapFaq(f) {
  return {
    question: f.q, answer: f.a, category: f.category || null,
    knowledge_status: "official_verified",
    source: "BIS public information used for the ManakMitra curated seed",
    source_url: "https://www.bis.gov.in/",
  };
}

function mapLab(l) {
  return {
    name: l.name, city: l.city || null, scope: l.scope || null, status: l.status || "Recognised",
    knowledge_status: "official_verified",
    source: "BIS public information used for the ManakMitra curated seed",
    source_url: "https://www.bis.gov.in/",
  };
}

function mapCertStep(s) {
  return {
    step: s.step, title: s.title, detail: s.detail || null,
    knowledge_status: "official_verified",
    source: "BIS public information used for the ManakMitra curated seed",
    source_url: "https://www.bis.gov.in/",
  };
}

function mapLicense(l) {
  return {
    license_number: l.license_number,
    holder_name: l.holder_name,
    product_or_standard: l.product_or_standard || null,
    status: l.status || "active",
    valid_until: l.valid_until || null,
    knowledge_status: "demonstration_mock",
    source: "ManakMitra demonstration seed — fictional license records",
  };
}

async function upsert(supabase, table, rows, conflictKey) {
  if (!rows.length) {
    console.log(`  (skip) ${table}: nothing to insert`);
    return;
  }

  if (conflictKey) {
    const { error, data } = await supabase.from(table).upsert(rows, { onConflict: conflictKey }).select("id");
    if (error) throw new Error(`${table} upsert failed: ${error.message}`);
    console.log(`  ✓ ${table}: upserted ${data?.length ?? rows.length} row(s)`);
    return;
  }

  const { count, error: countErr } = await supabase.from(table).select("*", { count: "exact", head: true });
  if (countErr) throw new Error(`${table} count check failed: ${countErr.message}`);
  if (count > 0) {
    console.log(`  (skip) ${table}: already has ${count} row(s) — not re-inserting`);
    return;
  }
  const { error, data } = await supabase.from(table).insert(rows).select("id");
  if (error) throw new Error(`${table} insert failed: ${error.message}`);
  console.log(`  ✓ ${table}: inserted ${data?.length ?? rows.length} row(s)`);
}

async function main() {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY. Copy backend/.env.example to scripts/.env and fill it in.");
    process.exit(1);
  }

  console.log(`Reading ${DATA_JS_PATH} ...`);
  const { STANDARDS, SERVICES, FAQS, LABS, CERT_STEPS, LICENSES } = loadDataJs();
  console.log(
    `  found ${STANDARDS.length} standards, ${SERVICES.length} services, ${FAQS.length} faqs, ${LABS.length} labs, ${CERT_STEPS.length} cert steps, ${LICENSES.length} licenses`
  );

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, { auth: { persistSession: false } });

  console.log("Migrating into Supabase...");
  await upsert(supabase, "standards", STANDARDS.map(mapStandard), "is_number");
  await upsert(supabase, "services", SERVICES.map(mapService), "id");
  await upsert(supabase, "faqs", FAQS.map(mapFaq), null);
  await upsert(supabase, "labs", LABS.map(mapLab), null);
  await upsert(supabase, "cert_steps", CERT_STEPS.map(mapCertStep), "step");
  await upsert(supabase, "licenses", LICENSES.map(mapLicense), "license_number");

  console.log("\nDone. js/data.js was left untouched in the repo as a seed/fallback reference.");
}

main().catch((err) => {
  console.error("Migration failed:", err.message);
  process.exit(1);
});
