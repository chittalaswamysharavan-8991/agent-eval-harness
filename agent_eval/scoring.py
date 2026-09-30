import re


def norm(value):
    return " ".join(value.casefold().split())


def score_case(case, output, docs):
    answer = str(output.get("answer", ""))
    citations = output.get("citations", [])
    if not isinstance(citations, list):
        citations = []
    citations = [c for c in citations if isinstance(c, str)]
    allowed = set(case["context_ids"])
    valid_citations = set(citations) & allowed
    invalid = sorted(set(citations) - allowed)
    expected = case["expected"]
    abstain = norm(answer).startswith("i don't know based on the provided documents")
    reasons = []
    if expected["behavior"] == "abstain":
        behavior_ok = abstain and not citations
        if not behavior_ok:
            reasons.append("expected an uncited abstention")
    else:
        missing = [s for s in expected["must_contain"] if norm(s) not in norm(answer)]
        behavior_ok = not abstain and not missing
        if missing:
            reasons.append("missing expected answer: " + ", ".join(missing))
        if abstain:
            reasons.append("abstained on an answerable case")
    forbidden = [s for s in expected.get("must_not_contain", []) if norm(s) in norm(answer)]
    if forbidden:
        reasons.append("forbidden assertion: " + ", ".join(forbidden))
    if invalid:
        reasons.append("unknown/out-of-context citations: " + ", ".join(invalid))
    required = set(expected.get("support_ids", []))
    grounding_ok = (not required or bool(required & valid_citations)) and not invalid
    if not grounding_ok:
        reasons.append("missing required source citation")

    # Check numeric claims against cited evidence. This is a narrow, deterministic
    # hallucination indicator, not a semantic proof that every sentence is supported.
    source = " ".join(docs[c] for c in valid_citations)
    answer_numbers = set(re.findall(r"(?<!\w)\d+(?:\.\d+)?(?:%|\b)", answer))
    source_numbers = set(re.findall(r"(?<!\w)\d+(?:\.\d+)?(?:%|\b)", source))
    unsupported_numbers = sorted(answer_numbers - source_numbers) if not abstain else []
    if unsupported_numbers:
        reasons.append("numbers absent from cited evidence: " + ", ".join(unsupported_numbers))
    hallucination_flag = bool(forbidden or invalid or unsupported_numbers or (expected["behavior"] == "abstain" and not abstain))
    passed = behavior_ok and grounding_ok and not hallucination_flag
    return {"id": case["id"], "passed": passed, "behavior_ok": behavior_ok,
            "grounding_ok": grounding_ok, "hallucination_flag": hallucination_flag,
            "reasons": reasons, "answer": answer, "citations": citations}


def summary(results):
    count = len(results)
    return {"total": count, "passed": sum(r["passed"] for r in results),
            "behavior_accuracy": sum(r["behavior_ok"] for r in results) / count,
            "grounding_rate": sum(r["grounding_ok"] for r in results) / count,
            "hallucination_flag_rate": sum(r["hallucination_flag"] for r in results) / count}
