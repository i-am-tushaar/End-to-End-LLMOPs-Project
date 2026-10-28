# LLMOps Evaluation Framework

This directory contains the evaluation framework for the End-to-End LLMOps RAG application. Evaluations are organized into component, pipeline, and application levels.

## 1. Evaluation architecture

```text
evaluation/
├── README.md
├── adapters/
│   └── project_adapter.py
├── component/
│   └── evaluate_retriever.py
├── pipeline/
│   └── evaluate_rag_triad.py
├── application/
│   ├── quality/
│   │   └── evaluate_quality.py
│   ├── safety/
│   │   ├── evaluate_toxicity.py
│   │   └── evaluate_leakage.py
│   └── operations/
│       └── evaluate_operations.py
├── datasets/
│   ├── application_quality_eval.json
│   ├── application_toxicity_eval.json
│   ├── application_leakage_eval.json
│   └── application_operations_eval.json
└── reports/
    ├── application_quality_results.json
    ├── application_toxicity_results.json
    ├── application_leakage_results.json
    ├── application_operations_results.json
    ├── APPLICATION_OPERATIONS_EVALUATION_REPORT.md
    └── [other evaluation reports]
```

Keep only filenames that exist in your local project and adjust paths if your actual names differ.

## 2. Evaluation levels

| Level | Purpose | Example metrics |
|---|---|---|
| Component | Evaluate the retriever independently | Contextual precision, contextual recall |
| Pipeline | Evaluate retrieval and generation together | Contextual relevancy, faithfulness, answer relevancy |
| Application — Quality | Assess response quality | Correctness, completeness, style, answer relevancy, faithfulness, groundedness |
| Application — Safety | Check unsafe outputs and sensitive-information leakage | Toxicity, prompt/document leakage, PII leakage |
| Application — Operations | Measure runtime behavior | Success/error rate, average latency, P50/P95/P99, throughput |

Operational success is not the same as answer quality. A request can finish without an exception and still return `I don't know.`

## 3. How to run evaluations

Run commands from the repository root, `End-to-End-LLMOPs-Project`.

```bash
# Component-level: retriever
uv run python -m evaluation.component.evaluate_retriever

# Pipeline-level: RAG Triad
uv run python -m evaluation.pipeline.evaluate_rag_triad

# Application-level: quality
uv run python -m evaluation.application.quality.evaluate_quality

# Application-level: toxicity
uv run python -m evaluation.application.safety.evaluate_toxicity

# Application-level: leakage
uv run python -m evaluation.application.safety.evaluate_leakage

# Application-level: operations
uv run python -m evaluation.application.operations.evaluate_operations

# Regression/unit tests
uv run pytest tests/ -v
```

Verify each module path against the Python filenames in your checkout. If a command reports `No module named ...`, update it to match your actual package/file structure.

## 4. Datasets and reports

- `datasets/` contains the input test cases used by evaluation modules.
- `reports/` contains machine-readable JSON outputs and human-readable Markdown reports.
- JSON files preserve detailed results for analysis; Markdown reports explain methods, results, limitations, and next steps.

After running an evaluator, check its terminal summary and confirm that the output report was written successfully. Do not manually copy scores into this README unless you verify them against the latest report.

## 5. Current operational evaluation snapshot

The repeated-run operations run on 28 October 2026 executed five dataset questions three times each, for 15 requests.

| Metric | Recorded result |
|---|---:|
| Requests | 15 |
| Successful invocations | 15 |
| Failed invocations | 0 |
| Success rate | 100.00% |
| Average latency | 2,730.62 ms |
| P50 latency | 1,986.95 ms |
| P95 latency | 5,773.69 ms |
| P99 latency | 9,614.73 ms |
| Throughput | 0.366 requests/second |
| API cost | Not measured |

These are results from one small, sequential run—not a production performance guarantee. Groq rate-limit responses and retries affected one request's latency. Some invocations returned `I don't know.` and still counted as technically successful because no exception was raised. See `reports/APPLICATION_OPERATIONS_EVALUATION_REPORT.md` for details.

Update this snapshot only after running a new evaluation and verifying its output.

## 6. Validation checklist

- [ ] Run all evaluation modules and verify their JSON reports.
- [ ] Run the unit/regression test suite.
- [ ] Confirm metrics match actual execution outputs.
- [ ] Document dataset sizes and evaluation limitations.
- [ ] Capture actual token usage before reporting API cost.
- [ ] Use larger samples and controlled concurrent-load tests before making production latency or capacity claims.
- [ ] Update this README when module paths, datasets, metrics, or reports change.

## 7. Recommended workflow

1. Update or add test cases in `datasets/`.
2. Run the relevant evaluation module.
3. Inspect the terminal output and generated JSON report.
4. Update the corresponding Markdown report with verified results.
5. Run relevant unit/regression tests after code changes.
6. Update this central README if the structure, commands, or latest result snapshot changed.

## 8. Interview summary

> “I organized evaluation into component, pipeline, and application levels. Component evaluation measures retriever performance, pipeline evaluation measures the RAG Triad, and application evaluation covers quality, safety, and operations. Each evaluation uses a dataset and writes structured results, while Markdown reports explain the methodology, findings, and limitations. This makes evaluation repeatable, traceable, and easier to maintain.”
