import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from agent_eval.scoring import score_case, summary


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(mode, cases, docs, fixtures, endpoint=None):
    results = []
    for case in cases:
        if mode == "replay":
            output = fixtures[case["id"]]
        elif mode == "live":
            from agent_eval.agent import answer
            output = answer(case["question"], docs, case["context_ids"])
        else:
            payload = json.dumps({"id": case["id"], "question": case["question"],
                                  "documents": {k: docs[k] for k in case["context_ids"]}}).encode()
            request = urllib.request.Request(endpoint, payload, {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=45) as response:
                output = json.load(response)
        results.append(score_case(case, output, docs))
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate a grounded agent")
    parser.add_argument("--mode", choices=["replay", "live", "endpoint"], default="replay")
    parser.add_argument("--endpoint", default=os.environ.get("AGENT_EVAL_ENDPOINT"))
    parser.add_argument("--baseline", type=Path, default=ROOT / "fixtures" / "baseline.json")
    parser.add_argument("--report", type=Path, default=ROOT / "report.json")
    args = parser.parse_args()
    if args.mode == "endpoint" and not args.endpoint:
        parser.error("--endpoint or AGENT_EVAL_ENDPOINT is required")
    docs = load(ROOT / "cases" / "documents.json")
    cases = load(ROOT / "cases" / "cases.json")
    fixtures = load(ROOT / "fixtures" / "responses.json") if args.mode == "replay" else {}
    results = run(args.mode, cases, docs, fixtures, args.endpoint)
    metrics = summary(results)
    report = {"mode": args.mode, "metrics": metrics, "cases": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    baseline = load(args.baseline)
    failures = [r for r in results if not r["passed"]]
    regressions = [k for k, direction in [("behavior_accuracy", "min"), ("grounding_rate", "min"),
                                           ("hallucination_flag_rate", "max")]
                   if (metrics[k] < baseline[k] if direction == "min" else metrics[k] > baseline[k])]
    print(f"{args.mode}: {metrics['passed']}/{metrics['total']} passed; behavior={metrics['behavior_accuracy']:.1%}; "
          f"grounding={metrics['grounding_rate']:.1%}; hallucination flags={metrics['hallucination_flag_rate']:.1%}")
    for result in failures:
        print(result["id"] + ": " + "; ".join(result["reasons"]))
    if regressions:
        print("Regressed metrics: " + ", ".join(regressions), file=sys.stderr)
    print("Report: " + str(args.report))
    return 1 if failures or regressions else 0


if __name__ == "__main__":
    sys.exit(main())
