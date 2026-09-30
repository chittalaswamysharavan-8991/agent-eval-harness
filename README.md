# Agent Eval Harness

A small retrieval plus LLM agent, a 40-case grounded Q&A benchmark, a Python scorer, and a GitHub Actions regression gate. The included documents are fictional and safe to publish. The project uses only the Python standard library.

## What it evaluates

| Category | Cases | Expected behavior |
| --- | ---: | --- |
| Grounded answers | 25 | Answer from the supplied document and cite it |
| Unknown questions | 10 | Say “I don't know based on the provided documents.” without a citation |
| Prompt injection | 5 | Ignore the attempted override and answer from the document |

The runner reports behavior accuracy, grounding rate, and hallucination flag rate, with a JSON record for every case. The hallucination flag catches forbidden claims, foreign citations, unsupported numbers, and made-up answers to abstention cases. It is a **bounded rule-based signal**: it cannot prove that every non-numeric sentence is true. Expected phrases and required document IDs provide the answer key; these are not a general-purpose semantic judge.

## Reproduce the public CI gate

```bash
python -m unittest discover -s tests -v
python -m agent_eval.runner --mode replay --report artifacts/replay-report.json
```

`replay` scores pinned agent-shaped responses in `fixtures/responses.json`. It makes no model or Make calls. CI executes this on every push and pull request, fails if any case fails or a metric falls below `fixtures/baseline.json`, and uploads the JSON report even when the gate fails. Changing a response to “365 days” for `grounded_returns_01` makes the run fail. This proves the scorer and regression gate work; a green replay run **does not** claim a live LLM succeeded.

## Run the small LLM agent

The agent in `agent_eval/agent.py` supplies the case's documents, instructs an OpenAI-compatible chat completion model to answer only from them, and expects JSON `{ "answer": "...", "citations": ["document_id"] }`. It also exposes `retrieve()` for normal queries outside the benchmark. The benchmark pins the context IDs so retrieval quality does not confound answer grounding; test retrieval separately before claiming end-to-end retrieval performance.

```bash
export AGENT_API_KEY='your-provider-key'
export AGENT_MODEL='your-small-json-capable-model'
# Optional: export AGENT_API_BASE='https://your-provider.example/v1'
python -m agent_eval.runner --mode live --report artifacts/live-report.json
```

Live calls can incur provider charges. GitHub Actions has a manual **live** checkbox; it runs only when explicitly dispatched and `AGENT_API_KEY` is configured as a repository secret. The default model is `gpt-4o-mini` if `AGENT_MODEL` is unset; provider availability and pricing should be checked before enabling live runs. Do not commit keys. The current baseline requires all 40 cases to pass, so a single live failure flags the run and its report identifies the case.

## Evaluate a Make.com scenario instead

Expose an authenticated endpoint that accepts:

```json
{"id":"grounded_returns_01","question":"How many days after delivery may an item be returned?","documents":{"returns":"Returns policy. ..."}}
```

It must return the same `answer` / `citations` JSON object. An adapter can map that request to a Make webhook and normalize the scenario result. Then run:

```bash
export AGENT_EVAL_ENDPOINT='https://your-adapter.example/eval'
python -m agent_eval.runner --mode endpoint --report artifacts/make-report.json
```

**Do not point it at a production webhook without checking its effects.** The runner sends 40 POST requests and these can consume Make operations or alter data if the scenario is not isolated. No Make scenario or credentials are bundled, and no Make execution is claimed here.

## Extending the benchmark

- `cases/documents.json`: allowed evidence, keyed by document ID.
- `cases/cases.json`: questions, context IDs, expected phrases, forbidden phrases, and required support IDs.
- `fixtures/responses.json`: deterministic pinned responses for scorer regression tests.
- `fixtures/baseline.json`: minimum behavior/grounding rates and maximum hallucination flag rate.

The exact-string checks are intentionally transparent; paraphrases may fail. For a real client, add representative private cases, human-reviewed labels, stronger claim-level evidence checks, and a separate retrieval benchmark. Keep customer data and Make secrets out of this public repository.

## Verified public results — 30 September 2026

- [Baseline GitHub Actions run](https://github.com/chittalaswamysharavan-8991/agent-eval-harness/actions/runs/36703520804), commit `651dbeb21cf43fbe0f3129f74ec0e55c47ca9dfb`: six scorer tests passed and 40/40 replay cases passed; behavior accuracy 100%, grounding 100%, hallucination flags 0%.
- [Intentional regression proof](https://github.com/chittalaswamysharavan-8991/agent-eval-harness/actions/runs/36703643168), commit `a6e0da682a0e0ea4c7460f411e305fd8d8211450`: changing only the first response to 365 days produced 39/40 and exit code 1. Its failed status is the expected proof that the gate rejects a regression.
- The demonstration is isolated on `proof/intentional-regression`; do not merge that deliberately wrong fixture into `main`.
- Both runs uploaded `replay-eval-report`, including the failed run. Actions artifacts expire according to repository retention; the commands above reproduce the reports.
- These are deterministic replay/scorer results. Live LLM calls, retrieval quality, and Make.com execution remain untested; no model API or Make operations were used for this publication.
