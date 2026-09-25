"""Run Phase 15 evaluation locally.

This command is intentionally dependency-injected: production credentials and
BIS data are never embedded in the dataset. Use a project-specific adapter when
running against a live environment.
"""
from __future__ import annotations
import json
from .runner import load_dataset

def main():
    # A live adapter is deliberately not guessed. The CLI validates the dataset
    # and prints its shape; CI/integration environments should inject a pipeline.
    cases=load_dataset()
    print(json.dumps({"phase":"15","dataset_cases":len(cases),"case_ids":[c.id for c in cases]},indent=2))

if __name__=="__main__":
    main()
