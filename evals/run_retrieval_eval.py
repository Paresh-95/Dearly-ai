#!/usr/bin/env python3
"""Compares dense, keyword and hybrid retrieval against a small, synthetic fixture dataset,
reporting Recall@K, Precision@K, MRR and latency for each mode. See evals/README.md before
reading the numbers this prints — in particular, whether a real embedding provider was
configured when it ran.

Usage (needs a running backend, e.g. `docker compose up -d db backend` or a local uvicorn):
    cd backend && uv run python ../evals/run_retrieval_eval.py [--base-url URL] [--k N]

Idempotent: reuses a fixed eval account and resets its one profile's memories each run, so
running it repeatedly does not accumulate duplicate data.
"""

import argparse
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
FIXTURES = json.loads((ROOT / "fixtures" / "sample_memories.json").read_text())
DATASET = json.loads((ROOT / "datasets" / "retrieval_queries.json").read_text())

EVAL_EMAIL = "retrieval-eval@example.com"
EVAL_PASSWORD = "retrieval-eval-password-123"
MODES = ["dense", "keyword", "hybrid"]


def authenticate(client: httpx.Client) -> None:
    r = client.post("/api/v1/auth/register", json={"email": EVAL_EMAIL, "password": EVAL_PASSWORD})
    if r.status_code == 409:
        r = client.post("/api/v1/auth/login", json={"email": EVAL_EMAIL, "password": EVAL_PASSWORD})
    r.raise_for_status()
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


def reset_profile(client: httpx.Client) -> str:
    """Reuses the eval account's one profile across runs (there is no profile-delete
    endpoint), clearing its memories first so each run starts from the same clean state."""
    profiles = client.get("/api/v1/profiles").json()["items"]
    existing = next((p for p in profiles if p["name"] == FIXTURES["profile"]["name"]), None)
    if existing is None:
        return client.post("/api/v1/profiles", json=FIXTURES["profile"]).json()["id"]

    profile_id = existing["id"]
    items = client.get(
        "/api/v1/memories", params={"person_profile_id": profile_id, "limit": 100}
    ).json()["items"]
    for m in items:
        client.delete(f"/api/v1/memories/{m['id']}")
    return profile_id


def seed_memories(client: httpx.Client, profile_id: str) -> dict[str, str]:
    key_to_id: dict[str, str] = {}
    for m in FIXTURES["memories"]:
        body = {
            "person_profile_id": profile_id,
            "title": m["title"],
            "description": m["description"],
            "status": "awaiting_review",
            "category": m["category"],
            "date_text": m["date_text"],
            "location": m["location"],
            "people": m["people"],
        }
        created = client.post("/api/v1/memories", json=body)
        created.raise_for_status()
        memory_id = created.json()["id"]
        client.post(f"/api/v1/memories/{memory_id}/approve").raise_for_status()
        key_to_id[m["key"]] = memory_id
    return key_to_id


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float | None:
    if not relevant:
        return None
    hits = len(set(retrieved[:k]) & set(relevant))
    return hits / len(relevant)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float | None:
    if not relevant:
        return None
    top = retrieved[:k]
    return (len(set(top) & set(relevant)) / len(top)) if top else 0.0


def mrr(retrieved: list[str], relevant: list[str]) -> float | None:
    if not relevant:
        return None
    for i, mid in enumerate(retrieved, start=1):
        if mid in relevant:
            return 1.0 / i
    return 0.0


def run_mode(client: httpx.Client, profile_id: str, case: dict, mode: str, k: int) -> dict:
    body = {"person_profile_id": profile_id, "query": case["query"], "mode": mode, "limit": k}
    if case.get("category"):
        body["category"] = case["category"]
    response = client.post("/api/v1/retrieval/search", json=body)
    response.raise_for_status()
    data = response.json()
    return {
        "retrieved_ids": [item["memory_id"] for item in data["items"]],
        "latency_ms": data["diagnostics"]["took_ms"],
        "dense_error": data["diagnostics"].get("dense_error"),
    }


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def print_report(output: dict, out_path: Path) -> None:
    print("\n=== Retrieval evaluation ===")
    print(
        f"{output['n_cases']} query cases "
        f"({output['n_no_answer_cases']} with no expected answer, reported separately)"
    )
    if output["dense_error_observed"]:
        print(f"\n⚠ Dense search reported an error on at least one query: "
              f"{output['dense_error_observed']}")
        print("  The dense/hybrid numbers below do NOT reflect a real embedding provider.")
        print("  Set MC_OPENAI_API_KEY on the backend and re-run for a meaningful comparison.")

    header = (
        f"{'mode':<10}{'recall@k':>10}{'precision@k':>13}{'mrr':>8}{'mean ms':>10}{'p95 ms':>10}"
    )
    print(f"\n{header}")
    for mode, s in output["summary"].items():
        print(
            f"{mode:<10}{_fmt(s['recall_at_k']):>10}{_fmt(s['precision_at_k']):>13}"
            f"{_fmt(s['mrr']):>8}{s['latency_ms_mean']:>10.2f}{s['latency_ms_p95']:>10.2f}"
        )

    print("\nNo-answer / injection-style cases (not scored by Recall/Precision/MRR):")
    for row in output["no_answer_cases"]:
        hybrid = row["hybrid"]
        top = hybrid["retrieved_ids"][0] if hybrid["retrieved_ids"] else None
        print(f"  [{row['id']}] top hybrid result: {top or '(none)'}")

    print(f"\nFull results written to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8100")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        authenticate(client)
        profile_id = reset_profile(client)
        key_to_id = seed_memories(client, profile_id)

        per_mode = {m: {"recall": [], "precision": [], "mrr": [], "latency": []} for m in MODES}
        rows: list[dict] = []
        no_answer_rows: list[dict] = []
        dense_error_observed: str | None = None

        for case in DATASET["cases"]:
            relevant_ids = [key_to_id[k] for k in case["relevant_keys"]]
            case_result = {"id": case["id"], "query": case["query"]}
            for mode in MODES:
                result = run_mode(client, profile_id, case, mode, args.k)
                case_result[mode] = result
                dense_error_observed = dense_error_observed or result["dense_error"]
                per_mode[mode]["latency"].append(result["latency_ms"])
                if relevant_ids:
                    rids = result["retrieved_ids"]
                    per_mode[mode]["recall"].append(recall_at_k(rids, relevant_ids, args.k))
                    per_mode[mode]["precision"].append(precision_at_k(rids, relevant_ids, args.k))
                    per_mode[mode]["mrr"].append(mrr(result["retrieved_ids"], relevant_ids))
            rows.append(case_result)
            if not relevant_ids:
                no_answer_rows.append(case_result)

        summary = {
            mode: {
                "recall_at_k": round(statistics.mean(m["recall"]), 3) if m["recall"] else None,
                "precision_at_k": (
                    round(statistics.mean(m["precision"]), 3) if m["precision"] else None
                ),
                "mrr": round(statistics.mean(m["mrr"]), 3) if m["mrr"] else None,
                "latency_ms_mean": round(statistics.mean(m["latency"]), 2),
                "latency_ms_p95": round(
                    sorted(m["latency"])[max(int(len(m["latency"]) * 0.95) - 1, 0)], 2
                ),
                "n_queries_with_relevance_judgments": len(m["recall"]),
            }
            for mode, m in per_mode.items()
        }

        output = {
            "generated_at": datetime.now(UTC).isoformat(),
            "k": args.k,
            "n_cases": len(DATASET["cases"]),
            "n_no_answer_cases": len(no_answer_rows),
            "dense_error_observed": dense_error_observed,
            "summary": summary,
            "no_answer_cases": no_answer_rows,
            "cases": rows,
        }

        results_dir = ROOT / "results"
        results_dir.mkdir(exist_ok=True)
        out_path = results_dir / f"retrieval_eval_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
        out_path.write_text(json.dumps(output, indent=2, default=str))
        print_report(output, out_path)


if __name__ == "__main__":
    main()
