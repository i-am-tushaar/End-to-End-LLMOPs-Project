# Application Operations Evaluation Report

## 1. Overview

This report documents the repeated-run operational evaluation of the End-to-End LLMOps RAG application.

**Evaluation module:** `evaluation/application/operations/evaluate_operations.py`  
**Dataset:** `evaluation/datasets/application_operations_eval.json`  
**Output:** `evaluation/reports/application_operations_results.json`  
**Execution command:**

```bash
uv run python -m evaluation.application.operations.evaluate_operations
```

The evaluator uses the existing `ConversationalRAG` application and a configured FAISS index. Each of the five dataset questions is executed three times, producing 15 request attempts.

## 2. Objectives

The operations evaluation measures whether the RAG application can execute requests successfully and how long those requests take. It records:

- Total requests and successful/failed invocations
- Success rate and error rate
- Average latency, P50, P95, and P99 latency
- Total evaluation duration and throughput
- Per-question and per-attempt latency, responses, and errors
- Cost-tracking status

Operational metrics are distinct from answer-quality and safety metrics. A request can complete successfully while returning an unhelpful answer such as `I don't know.`

## 3. Evaluation setup

| Setting | Value |
|---|---|
| Dataset test cases | 5 |
| Repetitions per question | 3 |
| Expected and completed requests | 15 |
| LLM provider/model logged by application | Groq / `openai/gpt-oss-20b` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Retrieval strategy | MMR |
| `k` | 3 |
| `fetch_k` | 10 |
| `lambda_mult` | 0.5 |
| Execution mode | Sequential |
| FAISS index | `faiss_index/session_20261026_215230_88296173` |
| Cost tracking | Not measured |

The RAG application and retriever are initialized before request timing begins. Per-request latency measures the `rag.invoke(...)` call, including retrieval and generation. The evaluation is sequential, not a concurrent load test.

## 4. Results from the repeated-run evaluation

**Run date:** 28 October 2026, based on the application log timestamps.

| Metric | Actual result |
|---|---:|
| Total requests | 15 |
| Successful invocations | 15 |
| Failed invocations | 0 |
| Success rate | 100.00% |
| Error rate | 0.00% |
| Average latency | 2,730.62 ms |
| P50 latency | 1,986.95 ms |
| P95 latency | 5,773.69 ms |
| P99 latency | 9,614.73 ms |
| Total request-loop duration | Approximately 40.96 seconds |
| Throughput | 0.366 successful requests/second |
| API cost | Not measured |

The latency percentiles are calculated over successful request latencies. The sample is small, so P95 and P99 should be treated as preliminary estimates, not production service-level guarantees.

## 5. Initial baseline versus repeated-run evaluation

An earlier single-run evaluation executed five requests. Its recorded results were:

| Metric | Initial 5-request baseline | Repeated-run evaluation |
|---|---:|---:|
| Requests | 5 | 15 |
| Successful invocations | 5 | 15 |
| Failed invocations | 0 | 0 |
| Success rate | 100.00% | 100.00% |
| Average latency | 1,711.86 ms | 2,730.62 ms |
| P95 latency | 2,317.98 ms | 5,773.69 ms |
| Throughput | 0.584 requests/second | 0.366 requests/second |
| API cost | Not measured | Not measured |

### How to interpret the comparison

The repeated-run evaluation improves the **depth of measurement**, because each question is tested three times rather than once. It does **not** demonstrate a performance improvement.

The repeated-run average latency and P95 are higher than the initial baseline. These runs are not a controlled before-and-after performance experiment: they contain different numbers of requests, and the repeated-run log includes Groq HTTP `429 Too Many Requests` responses followed by retries. The final invocation succeeded, but the retries contributed to the observed latency. Do not describe the higher latency as a regression caused by a code change without a controlled comparison.

## 6. What was implemented

### 6.1 Repeated-run execution

Each dataset question is invoked three times, for 15 attempts in total. This exposes some run-to-run variation that a single execution per question cannot show.

### 6.2 Per-attempt recording

The JSON report records individual attempts, including the case ID, repeat number, question, success status, latency, answer, and error details where applicable.

### 6.3 Aggregate and per-case metrics

The evaluator calculates request-level success/error rates and latency statistics, and stores per-question summaries so that slow or unreliable cases can be investigated.

### 6.4 Report persistence

The report is written to:

`evaluation/reports/application_operations_results.json`

This makes the results available for inspection, comparison, and future regression runs.

### 6.5 Initialization correction

The first execution failed because `ConversationalRAG` requires a `session_id`. The initialization was updated to supply a session ID, after which the evaluator initialized the LLM, loaded the embedding model and FAISS retriever, and completed all 15 request attempts.

## 7. Observations and limitations

1. **All 15 invocations completed without an unhandled request exception.** This supports a 100% technical success rate for this run only; it does not guarantee reliability under other conditions.
2. **Some answers were `I don't know.`** In particular, the log shows this response for repeated attempts of `ops_003` and `ops_004`. Those requests were counted as technically successful because the RAG invocation returned without raising an exception. Their answer quality must be assessed by application-quality and RAG evaluation metrics.
3. **Rate limiting affected latency.** The log shows two HTTP 429 responses and retries during the third attempt for `ops_005`. The overall request eventually succeeded, with a measured latency of 10,574.99 ms for that attempt.
4. **Small sample size.** Fifteen requests are enough for an initial smoke/performance check, not for dependable tail-latency estimates.
5. **Sequential-only testing.** This evaluation does not test concurrent traffic, throughput under load, saturation, or maximum capacity.
6. **Cost is unknown.** No token usage or provider billing data was captured. Cost must remain “not measured” until actual usage is collected.
7. **No automatic performance improvement is claimed.** Repeating requests improves observability of variation; it does not itself optimize the application.

## 8. Recommended next steps

1. Run the evaluation several times under comparable conditions and preserve each report as a timestamped historical artifact so trends can be compared.
2. Record token usage and provider/model pricing, where available, before reporting estimated API cost.
3. Add a separate load test with controlled concurrency if the goal is to measure behavior under multiple simultaneous users.
4. Investigate the `I don't know.` responses using retrieval diagnostics and the quality evaluation suite.
5. Consider explicitly tracking empty answers and refusal/unknown answers separately from technical request failures.
6. Add operational thresholds only after establishing a representative baseline and defining the intended service-level objectives.
7. Rerun unit tests and the existing quality, toxicity, and leakage evaluations after changes to shared RAG code.

## 9. Interview explanation

> “I built an application-level operations evaluator for my RAG application. It runs every question in a JSON evaluation dataset three times and records per-request latency, technical success or failure, and response details. It calculates average latency, P50, P95, P99, error rate, and throughput, then saves both per-case and aggregate results to JSON. In this run, all 15 invocations completed successfully, average latency was 2.73 seconds, and throughput was 0.366 requests per second. Groq rate-limit retries affected one request, and some successful invocations returned ‘I don't know,’ so I treat operational reliability separately from answer quality. Cost remains unmeasured because I have not yet captured actual token usage.”

## 10. Conclusion

The repeated-run operations evaluation is implemented and completed successfully for the current five-case dataset. The result is a more detailed preliminary operational baseline, not evidence of improved latency or production readiness. Further controlled runs, token-cost tracking, answer-quality checks, and load testing are needed for stronger conclusions.
