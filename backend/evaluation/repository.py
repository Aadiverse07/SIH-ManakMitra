from __future__ import annotations
from typing import Any
from backend.app.database.client import supabase

def save_report(report):
    row={
      "id":report.run_id,"environment":report.environment,
      "dataset_version":"phase15-v1","started_at":report.started_at,"finished_at":report.finished_at,
      "dataset_size":report.dataset_size,"passed":report.passed,"failed":report.failed,
      "metrics":report.metrics,"regression":report.regression}
    supabase.table("evaluation_runs").upsert(row,on_conflict="id").execute()
    payload=[]
    for r in report.cases:
        payload.append({"run_id":report.run_id,"case_id":r.case_id,"passed":r.passed,
          "retrieval":r.retrieval,"grounding":r.grounding,"citation":r.citation,
          "version":r.version,"context":r.context,"answer_quality":r.answer_quality,
          "hallucination":r.hallucination,"latency_ms":r.latency_ms,"error":r.error})
    if payload: supabase.table("evaluation_results").upsert(payload,on_conflict="run_id,case_id").execute()
    return report.run_id

def list_runs(limit:int=20):
    return supabase.table("evaluation_runs").select("*").order("started_at",desc=True).limit(min(max(limit,1),100)).execute().data or []

def get_run(run_id:str):
    run=supabase.table("evaluation_runs").select("*").eq("id",run_id).limit(1).execute().data
    if not run: return None
    results=supabase.table("evaluation_results").select("*").eq("run_id",run_id).order("case_id").execute().data or []
    run[0]["cases"]=results
    return run[0]
