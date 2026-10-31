# LLMOps Evaluation Framework

## 1. Introduction

This directory contains the evaluation framework for the End-to-End LLMOps RAG application.

The framework evaluates the application at three levels:

1. **Component-Level Evaluation:** Evaluates the retriever and generator independently.
2. **Pipeline-Level Evaluation:** Evaluates the complete RAG workflow using RAG Triad metrics.
3. **Application-Level Evaluation:** Evaluates application quality, safety, and operational performance.

The objective is to make evaluation systematic, repeatable, measurable, and easier to debug. The framework uses evaluation datasets, DeepEval metrics, a Groq-powered LLM judge where configured, and structured evaluation reports.

The main entry point is `evaluation/runners/run_all_evaluations.py`, which orchestrates the complete evaluation workflow.

---

## 2. Evaluation Folder Structure

```text
evaluation/
│
├── __init__.py
│
├── component/
│   ├── __init__.py
│   ├── evaluate_retriever.py
│   ├── evaluate_generator.py
│   └── evals_component.py
│
├── pipeline/
│   ├── __init__.py
│   └── evaluate_rag_triad.py
│
├── application/
│   ├── __init__.py
│   ├── evals_application.py
│   │
│   ├── quality/
│   │   ├── __init__.py
│   │   └── evaluate_quality.py
│   │
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── evals_safety.py
│   │   ├── evaluate_leakage.py
│   │   ├── evaluate_toxicity.py
│   │   ├── evaluate_scope.py
│   │   └── evaluate_safety.py
│   │
│   └── operations/
│       ├── __init__.py
│       └── evaluate_operations.py
│
├── judges/
│   └── groq_judge.py
│
├── datasets/
│   ├── retriever_goldens.json
│   ├── faithfulness_dataset.json
│   ├── correctness_goldens.json
│   ├── leakage_goldens.json
│   ├── scope_goldens.json
│   └── toxicity_goldens.json
│
├── docs/
│   ├── application_leakage_evaluation_report.md
│   ├── application_operations_evaluation_report.md
│   ├── application_quality_evaluation_report.md
│   ├── application_safety_results.md
│   ├── application_scope_results.md
│   ├── application_toxicity_evaluation_report.md
│   ├── generator_evaluation_report.md
│   ├── rag_triad_evaluation_report.md
│   └── retriever_evaluation_report.md
│
├── reports/
│   ├── [evaluation JSON results]
│   └── [other generated evaluation reports]
│
└── runners/
    ├── __init__.py
    ├── run_all_evaluations.py
    └── README.md
```

The tree shows the current organization discussed for this project. Keep it synchronized with the actual files in your local checkout. There is no `adapters/` directory in this architecture.

### Folder responsibilities

| Folder | Responsibility |
|---|---|
| `component/` | Evaluates the retriever and generator independently. |
| `pipeline/` | Evaluates the complete RAG pipeline. |
| `application/quality/` | Evaluates application response quality. |
| `application/safety/` | Evaluates leakage, toxicity, scope adherence, and application safety. |
| `application/operations/` | Measures runtime and operational performance. |
| `judges/` | Contains the LLM judge implementation used by applicable evaluation modules. |
| `datasets/` | Stores evaluation test cases and golden datasets. |
| `docs/` | Contains human-readable Markdown documentation and result explanations for individual evaluations. |
| `reports/` | Stores generated machine-readable results, such as JSON evaluation outputs. |
| `runners/` | Contains scripts that orchestrate multiple evaluation modules. |

---

## 3. Evaluation Documentation: `docs/`

The `docs/` folder contains a separate Markdown document for explaining the methodology, metrics, results, observations, and limitations of individual evaluations.

These documents are intended for developers, reviewers, and anyone who wants to understand how a particular evaluation works without reading the implementation first.

### Documentation files

| Documentation file | What it explains |
|---|---|
| `retriever_evaluation_report.md` | Retriever evaluation approach, retrieval metrics, results, and observations. |
| `generator_evaluation_report.md` | Generator evaluation approach, response-quality metrics, results, and observations. |
| `rag_triad_evaluation_report.md` | End-to-end RAG Triad evaluation, including contextual relevancy, faithfulness, and answer relevancy. |
| `application_quality_evaluation_report.md` | Application-level response quality evaluation and its findings. |
| `application_leakage_evaluation_report.md` | Leakage evaluation, including prompt, course-content, and PII leakage checks. |
| `application_toxicity_evaluation_report.md` | Toxicity evaluation methodology and results. |
| `application_scope_results.md` | Scope adherence evaluation, including in-scope and out-of-scope behavior. |
| `application_safety_results.md` | Application safety evaluation and its findings. |
| `application_operations_evaluation_report.md` | Operational evaluation methodology, performance metrics, results, and limitations. |

**How to use the docs folder:**

1. Open the Markdown document corresponding to the evaluation you want to understand.
2. Review its evaluation objective and methodology.
3. Review the metrics, test cases, and thresholds documented there.
4. Compare the reported results with the latest generated files in `reports/`.
5. Update the relevant document when the evaluation implementation or verified results change.

The Markdown files in `docs/` explain the evaluations. They are not necessarily generated automatically. Update them only after checking the actual evaluation code and latest output.

---

## 4. Evaluation Workflow at a Glance

```text
                  run_all_evaluations.py
                            |
              -----------------------------
              |             |             |
           Component      Pipeline     Application
              |             |             |
        evals_component  evaluate_rag_triad  evals_application
              |                           |
        -------------             ---------------------
        |           |             |         |         |
     Retriever   Generator     Quality   Safety   Operations
                                          |           |
                                     evals_safety  evaluate_operations
                                          |
                               -----------------------
                               |      |       |       |
                            Leakage Toxicity Scope Application
                                                    Safety
```

The main orchestrator runs three stages sequentially:

1. Component-level runner.
2. Pipeline-level evaluator.
3. Application-level runner.

Each level manages its own evaluation modules. The evaluation modules generate or update their corresponding results in `reports/`, while the explanatory Markdown documents are maintained in `docs/`.

---

## 5. Component-Level Evaluation

### 5.1 Definition

Component-level evaluation measures individual RAG components independently. It helps identify whether retrieval or generation is responsible for poor end-to-end performance.

**Component runner:** `evaluation.component.evals_component`

It executes:

- `evaluate_retriever.py`
- `evaluate_generator.py`

### 5.2 Retriever evaluation

**Module:** `evaluation.component.evaluate_retriever`

The retriever finds and returns document chunks relevant to a user's query. Retriever evaluation measures whether the retrieved context contains the information needed to answer the query.

**Important metrics**

| Metric | What it measures |
|---|---|
| Contextual Precision | Whether relevant retrieved context is ranked above irrelevant context. |
| Contextual Recall | Whether the retrieved context contains the information needed to answer the question. |
| Retrieval Relevance | Whether retrieved documents are relevant to the user's query, if implemented by the evaluator. |

**Common failures and possible improvements**

| Failure | Possible reason | Possible improvement |
|---|---|---|
| Low Contextual Precision | Irrelevant chunks are retrieved or ranked too highly. | Tune retrieval parameters, improve metadata filtering, or add reranking. |
| Low Contextual Recall | Relevant information is missing from retrieved chunks. | Review document parsing, chunk size, overlap, embeddings, and `top_k`. |
| Poor retrieval relevance | Query and document representations do not match well. | Review query preprocessing, embedding model, and retrieval strategy. |

Detailed explanation: `docs/retriever_evaluation_report.md`

### 5.3 Generator evaluation

**Module:** `evaluation.component.evaluate_generator`

The generator uses retrieved context and the user's query to produce an answer. Generator evaluation checks the quality and reliability of those answers.

**Important metrics**

| Metric | What it measures |
|---|---|
| Faithfulness | Whether the answer is supported by the supplied context. |
| Answer Relevancy | Whether the answer addresses the user's question. |
| Answer Correctness | Whether the answer matches the expected answer, where a reference answer is available. |

**Common failures and possible improvements**

| Failure | Possible reason | Possible improvement |
|---|---|---|
| Low Faithfulness | The model adds claims not supported by the context. | Improve grounding instructions and context handling. |
| Low Answer Relevancy | The response does not directly answer the query. | Improve prompt instructions and query handling. |
| Low Correctness | The answer conflicts with the reference answer. | Check context quality, model behavior, and reference data. |

Detailed explanation: `docs/generator_evaluation_report.md`

### 5.4 Component runner

**Module:** `evaluation.component.evals_component`

This runner:

1. Executes the retriever evaluation.
2. Executes the generator evaluation.
3. Records each process's return code and execution duration.
4. Displays a consolidated component-level summary.
5. Returns a nonzero exit code if a child evaluation fails.

Run component evaluations:

```bash
uv run python -m evaluation.component.evals_component
```

Run an individual component when debugging:

```bash
uv run python -m evaluation.component.evaluate_retriever
uv run python -m evaluation.component.evaluate_generator
```

---

## 6. Pipeline-Level Evaluation

### 6.1 Definition

Pipeline-level evaluation measures the complete RAG workflow by evaluating the relationship between retrieved context, the user's query, and the generated answer.

It helps determine whether retrieval and generation work together to produce relevant, contextually supported answers.

**Module:** `evaluation.pipeline.evaluate_rag_triad`

### 6.2 RAG Triad metrics

| Metric | What it measures | Typical issue when the score is low |
|---|---|---|
| Contextual Relevancy | Whether retrieved context is relevant to the user's question. | Retrieval returns unrelated or unnecessary information. |
| Faithfulness | Whether the generated answer is supported by retrieved context. | The answer contains unsupported claims or hallucinations. |
| Answer Relevancy | Whether the generated answer addresses the user's question. | The answer is incomplete, off-topic, or does not answer the query. |

### 6.3 Common failures and possible improvements

| Failure | Possible reason | Possible improvement |
|---|---|---|
| Low Contextual Relevancy | Retrieval returns irrelevant context. | Improve chunking, embeddings, filtering, and reranking. |
| Low Faithfulness | The generator is not sufficiently grounded in context. | Improve system prompts and grounding instructions. |
| Low Answer Relevancy | The generated response does not answer the query. | Improve query interpretation and generation prompts. |

Detailed explanation: `docs/rag_triad_evaluation_report.md`

### 6.4 Run pipeline evaluation

```bash
uv run python -m evaluation.pipeline.evaluate_rag_triad
```

---

## 7. Application-Level Evaluation

### 7.1 Definition

Application-level evaluation measures the behavior of the complete application from three perspectives:

1. Quality
2. Safety
3. Operations

**Application-level orchestrator:** `evaluation.application.evals_application`

It executes the quality evaluation, safety runner, and operations evaluation.

### 7.2 Quality evaluation

**Module:** `evaluation.application.quality.evaluate_quality`

Quality evaluation checks whether application responses meet the expected answer-quality criteria.

Depending on the configured evaluator and dataset, evaluation areas can include:

| Evaluation area | Purpose |
|---|---|
| Correctness | Checks whether the response is factually correct against the reference. |
| Completeness | Checks whether the response covers the required information. |
| Answer Relevancy | Checks whether the response addresses the user's question. |
| Faithfulness / Groundedness | Checks whether the answer is supported by the provided context. |
| Style | Checks whether the response follows the expected communication style. |

**Common failures and possible improvements**

| Failure | Possible reason | Possible improvement |
|---|---|---|
| Low Correctness | The answer is inaccurate or conflicts with the reference. | Inspect retrieved context, reference answers, and generation behavior. |
| Low Completeness | Important parts of the expected answer are missing. | Improve context coverage and answer instructions. |
| Low Answer Relevancy | The response is not focused on the question. | Improve prompt design and query handling. |
| Low Style score | The response does not follow the expected format or tone. | Make output requirements more explicit in the prompt. |

Detailed explanation: `docs/application_quality_evaluation_report.md`

Run quality evaluation:

```bash
uv run python -m evaluation.application.quality.evaluate_quality
```

### 7.3 Safety evaluation

**Runner:** `evaluation.application.safety.evals_safety`

The safety runner coordinates four safety evaluation modules.

| Module | Evaluation | Purpose |
|---|---|---|
| `evaluate_leakage.py` | Leakage | Checks for disclosure of restricted course content, system prompts, or personally identifiable information. |
| `evaluate_toxicity.py` | Toxicity | Checks whether generated responses contain toxic or harmful language. |
| `evaluate_scope.py` | Scope adherence | Checks whether the application handles in-scope and out-of-scope questions appropriately. |
| `evaluate_safety.py` | Application safety | Checks whether the application responds appropriately to safety-sensitive requests. |

**Important safety checks**

- Course content leakage
- Prompt leakage
- PII leakage
- Toxicity
- In-scope and out-of-scope behavior
- Appropriate handling of safety-sensitive requests

**Common failures and possible improvements**

| Failure | Possible reason | Possible improvement |
|---|---|---|
| Course content leakage | Restricted content is returned when it should not be. | Review access rules, prompt instructions, and output controls. |
| Prompt leakage | Internal system instructions are exposed. | Strengthen instruction boundaries and refusal handling. |
| PII leakage | Sensitive personal information appears in output. | Add privacy controls and appropriate input/output checks. |
| Toxicity | The response contains abusive or harmful language. | Improve safety instructions and response validation. |
| Scope failure | The application answers unrelated requests instead of handling them as out of scope. | Define the supported domain and out-of-scope behavior clearly. |
| Application safety failure | A safety-sensitive request receives an inappropriate response. | Improve safety handling and test coverage for sensitive scenarios. |

Detailed explanations:
- `docs/application_leakage_evaluation_report.md`
- `docs/application_toxicity_evaluation_report.md`
- `docs/application_scope_results.md`
- `docs/application_safety_results.md`

Run the complete safety evaluation:

```bash
uv run python -m evaluation.application.safety.evals_safety
```

Run individual safety modules for debugging:

```bash
uv run python -m evaluation.application.safety.evaluate_leakage
uv run python -m evaluation.application.safety.evaluate_toxicity
uv run python -m evaluation.application.safety.evaluate_scope
uv run python -m evaluation.application.safety.evaluate_safety
```

**Evaluation failure vs. evaluation error**

A safety test failure means the test ran and the response did not meet the expected safety criteria.

An evaluation error means the test could not be scored or completed, for example because the Groq API quota was exhausted, the model was unavailable, or a configuration was missing. An API error is not evidence that the application itself failed the safety test.

### 7.4 Operations evaluation

**Module:** `evaluation.application.operations.evaluate_operations`

Operations evaluation measures runtime behavior and operational performance. It helps determine whether the application responds reliably and within its configured performance expectations.

**Operational metrics**

| Metric | Purpose |
|---|---|
| Request success rate | Percentage of invocations that complete according to the evaluator's success definition. |
| Error rate | Percentage of invocations that encounter errors. |
| Average latency | Average time taken to process requests. |
| P50 latency | Median request latency. |
| P95 latency | Latency at or below which 95% of measured requests complete. |
| P99 latency | Latency at or below which 99% of measured requests complete. |
| Throughput | Number of requests processed per unit of time. |
| API cost | Estimated or measured model/API usage cost, if token and pricing data are available. |
| TTFT | Time to First Token, if streaming measurements are implemented. |

The actual metrics depend on what `evaluate_operations.py` measures and writes to its report. Do not claim a metric is measured unless it is present in the implementation and output.

**Common failures and possible improvements**

| Failure | Possible reason | Possible improvement |
|---|---|---|
| High average latency | Slow model response, retrieval, or document processing. | Profile each stage and optimize the bottleneck. |
| High P95/P99 latency | A subset of requests takes much longer than others. | Investigate retries, rate limits, long prompts, and slow requests. |
| High error rate | API failures, timeouts, or application exceptions. | Review logs, timeouts, retries, and exception handling. |
| Low throughput | Requests are processed slowly or sequentially. | Profile the workload and test suitable concurrency. |
| High API cost | Large prompts, large contexts, or expensive model usage. | Reduce unnecessary context and measure actual token usage. |
| SLO failure | A measured metric does not meet its configured target. | Identify the failing metric and improve the responsible stage. |

**Important:** Operational success is not the same as answer quality. A request can finish without an exception and still return `I don't know.` A successful invocation should not automatically be interpreted as a correct or useful answer.

Detailed explanation: `docs/application_operations_evaluation_report.md`

Run operations evaluation:

```bash
uv run python -m evaluation.application.operations.evaluate_operations
```

### 7.5 Application-level runner

**Module:** `evaluation.application.evals_application`

This runner coordinates:

1. Quality: `evaluation.application.quality.evaluate_quality`
2. Safety: `evaluation.application.safety.evals_safety`
3. Operations: `evaluation.application.operations.evaluate_operations`

It executes them sequentially, tracks execution durations and statuses, and prints an application-level summary.

Run application-level evaluation:

```bash
uv run python -m evaluation.application.evals_application
```

---

## 8. Main Evaluation Orchestrator

### 8.1 Purpose

`evaluation/runners/run_all_evaluations.py` is the main entry point for the complete evaluation framework.

It does not implement evaluation metrics itself. Instead, it invokes the component, pipeline, and application evaluation modules in sequence and summarizes their process results.

### 8.2 Execution stages

| Order | Evaluation stage | Module executed |
|---:|---|---|
| 1 | Component-Level | `evaluation.component.evals_component` |
| 2 | Pipeline-Level | `evaluation.pipeline.evaluate_rag_triad` |
| 3 | Application-Level | `evaluation.application.evals_application` |

### 8.3 How it works

1. Initializes the complete evaluation run and records the start time.
2. Executes the component runner, which runs retriever and generator evaluations.
3. Executes the RAG Triad pipeline evaluation.
4. Executes the application runner, which coordinates quality, safety, and operations.
5. Captures each process's return code and execution duration.
6. Prints a consolidated summary of the three stages.
7. Returns a nonzero process exit code if any stage fails.

The orchestrator uses Python's `subprocess` module to run each module as a separate process.

### 8.4 Run the complete evaluation pipeline

Run this command from the repository root:

```bash
uv run python -m evaluation.runners.run_all_evaluations
```

**Important:** The main orchestrator relies on the exit codes returned by the child runners. Each evaluation module or runner must return a nonzero exit code when its own metric checks fail. If a script always exits with code `0`, the orchestrator may report that stage as passed even when its JSON report contains failed test cases.

The orchestrator continues to later stages after a stage fails, so the final summary can show the status of all three stages. Later evaluations may still consume API tokens even if an earlier stage has failed.

---

## 9. Datasets and Golden Test Cases

The `datasets/` directory stores test cases used by the evaluation modules.

A dataset may contain:
- User questions or inputs
- Expected answers or reference outputs
- Expected retrieval context or relevant information
- Test-case identifiers
- Safety or scope categories
- Additional metadata required by an evaluator

The project has used datasets such as:

| Dataset | Evaluation purpose |
|---|---|
| `retriever_goldens.json` | Retriever evaluation. |
| `faithfulness_dataset.json` | Faithfulness and grounded-answer evaluation. |
| `correctness_goldens.json` | Answer correctness evaluation. |
| `leakage_goldens.json` | Leakage evaluation. |
| `scope_goldens.json` | Scope adherence evaluation. |
| `toxicity_goldens.json` | Toxicity evaluation. |

The exact dataset fields and test-case counts should be confirmed from the current JSON files and evaluation code.

### Why golden datasets are important

Golden datasets provide repeatable test inputs and expected outcomes. They help compare changes to retrieval, prompts, models, and application logic over time.

### Dataset best practices

1. Use representative questions from the application's intended domain.
2. Include normal, difficult, ambiguous, and edge-case inputs.
3. Keep reference answers accurate and reviewable.
4. Add negative and out-of-scope examples where relevant.
5. Use stable test-case IDs so failures can be tracked.
6. Update datasets when application requirements change.
7. Avoid changing expected answers merely to make a failing evaluation pass.

---

## 10. Reports and Result Analysis

The `reports/` directory stores generated evaluation outputs. The `docs/` directory stores human-readable explanations and evaluation reports.

Depending on the evaluator, generated outputs may include:
- JSON files containing structured results and individual test-case details.
- Other machine-readable artifacts produced by the evaluation code.

### Difference between `docs/` and `reports/`

| Directory | Purpose |
|---|---|
| `docs/` | Human-readable Markdown documentation describing evaluation methodology, metrics, findings, and limitations. |
| `reports/` | Generated evaluation results, such as JSON scores, test-case outcomes, and summaries. |

Examples of Markdown documentation in `docs/`:

- `retriever_evaluation_report.md`
- `generator_evaluation_report.md`
- `rag_triad_evaluation_report.md`
- `application_quality_evaluation_report.md`
- `application_leakage_evaluation_report.md`
- `application_toxicity_evaluation_report.md`
- `application_scope_results.md`
- `application_safety_results.md`
- `application_operations_evaluation_report.md`

Known report names from the evaluation workflow include:

- `application_quality_results.json`
- `application_toxicity_results.json`
- `application_leakage_results.json`
- `application_operations_results.json`

Other component, pipeline, and safety results may also be generated. Confirm exact filenames in the current `reports/` directory and in each evaluator's report-writing code.

### How to analyze a report

1. Check the total number of test cases.
2. Check passed, failed, and error counts.
3. Review metric scores and configured thresholds.
4. Inspect individual failed test cases.
5. Separate application failures from judge/API execution errors.
6. Compare the latest report with previous runs when available.
7. Update the relevant Markdown document in `docs/` with verified findings.

Do not manually copy scores into documentation unless they have been verified against the latest generated report.

---

## 11. Recorded Operations Evaluation Snapshot

The repeated-run operations evaluation on **28 October 2026** executed five dataset questions three times each, for a total of 15 requests.

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

### Interpretation and limitations

- These results represent one small, sequential run, not a production performance guarantee.
- Groq rate-limit responses and retries affected the latency of one request.
- Some invocations returned `I don't know.` and still counted as technically successful because no exception was raised.
- API cost was not measured, so no cost conclusion can be drawn from this run.
- A sample of 15 sequential requests is not sufficient to establish production capacity or concurrent-load performance.

See `docs/application_operations_evaluation_report.md` for the detailed methodology and findings.

Update this snapshot only after running a new evaluation and verifying its output.

---

## 12. LLM Judge and DeepEval

The evaluation framework uses DeepEval and a Groq-powered LLM judge for applicable LLM-based metrics.

### What is an LLM judge?

An LLM judge is a language model used to assess another model's output against defined evaluation criteria.

For example, a judge can assess:
- Whether an answer is supported by retrieved context.
- Whether an answer is relevant to the question.
- Whether an answer meets a reference-based quality criterion.
- Whether a response contains unsafe or restricted content.

### Role of DeepEval

DeepEval provides evaluation metrics, test cases, and utilities for testing LLM applications. The project uses it for applicable component, pipeline, and application evaluations.

### Role of Groq

Groq provides API access to the configured judge model. The judge implementation is maintained in `evaluation/judges/groq_judge.py` and is used by evaluation modules that require LLM-based scoring.

### Important considerations

1. Verify the configured Groq model name.
2. Keep API keys in environment variables; never commit secrets.
3. Monitor token usage and provider rate limits.
4. Use consistent judge settings when comparing experiments.
5. Review individual failed cases, not just average scores.
6. Treat API, quota, and model errors as evaluation errors, not as proof of application failure.
7. Be aware that LLM-judge scores can vary and should be interpreted alongside test cases and deterministic checks.

---

## 13. Understanding Evaluation Statuses

Evaluation modules and runners should distinguish between a metric failure and an execution problem.

| Status | Meaning |
|---|---|
| `PASSED` | The evaluation completed and met its implemented checks. |
| `FAILED` | The evaluation completed, but one or more test cases or configured thresholds failed. |
| `ERROR` | The evaluation could not complete or could not produce a valid result because of a technical or external problem. |

### Evaluation failure example

```text
Total Test Cases : 15
Passed           : 14
Failed           : 1
Errors           : 0

Status: FAILED
```

This means the evaluation ran, but at least one test case did not meet the expected criteria.

**How to investigate:**

1. Identify the failed test case.
2. Inspect the input, expected result, and actual output.
3. Determine whether retrieval, generation, or application logic caused the failure.
4. Fix the relevant implementation or configuration.
5. Rerun the affected evaluation.

### Evaluation error example

```text
Error: Groq API rate limit exceeded
Error: Model not found
Error: Missing API key

Status: ERROR
```

This means the evaluation could not complete or score the test.

**How to investigate:**

1. Read the traceback and provider error.
2. Verify the API key and model configuration.
3. Check token quota and rate limits.
4. Verify dependencies, file paths, and input datasets.
5. Resolve the issue and rerun the evaluation.

A provider error must not be counted as a genuine application safety or quality failure unless the application itself caused the error being measured.

---

## 14. Common Failures and Troubleshooting

| Problem | Likely area | What to check |
|---|---|---|
| Low Contextual Precision | Retriever | Retrieved chunks, ranking, filters, and reranker. |
| Low Contextual Recall | Retriever | Document parsing, chunk size, overlap, embeddings, and `top_k`. |
| Low Faithfulness | Generator / Pipeline | Retrieved context, grounding instructions, and generated claims. |
| Low Answer Relevancy | Generator / Pipeline | Query interpretation, prompt, and response content. |
| Low Correctness | Quality | Reference answer, context, and generated response. |
| Low Completeness | Quality | Required answer elements, context coverage, and prompt. |
| Prompt or document leakage | Safety | System instructions, access controls, and output handling. |
| PII leakage | Safety | Sensitive-data handling and input/output controls. |
| Toxic response | Safety | Safety instructions, model behavior, and output validation. |
| Scope failure | Safety | Domain definition and out-of-scope handling. |
| High latency | Operations | Retrieval time, model response time, retries, and long prompts. |
| High P95/P99 latency | Operations | Slow requests, rate limits, retries, and service variability. |
| High API cost | Operations | Token counts, context size, model choice, and pricing assumptions. |
| Groq quota or rate-limit error | Evaluation infrastructure | Provider limits, retry behavior, and judge-model availability. |
| `No module named ...` | Python package structure | Module path, `__init__.py`, working directory, and spelling. |
| Missing dataset or report | Evaluation configuration | Configured file path, filename, and report-writing permissions. |

---

## 15. Recommended Execution Order

During development, run evaluations individually to make failures easier to isolate.

### Step 1: Component-level evaluation

```bash
uv run python -m evaluation.component.evals_component
```

### Step 2: Pipeline-level evaluation

```bash
uv run python -m evaluation.pipeline.evaluate_rag_triad
```

### Step 3: Application-level evaluation

```bash
uv run python -m evaluation.application.evals_application
```

### Step 4: Complete evaluation pipeline

```bash
uv run python -m evaluation.runners.run_all_evaluations
```

### Step 5: Unit and regression tests

```bash
uv run pytest tests/ -v
```

Run the full pipeline after the individual modules and their dependencies are configured correctly. LLM-judge evaluations can consume API tokens, so check provider quota before starting a full run.

---

## 16. Validation Checklist

- [ ] Confirm all evaluation module paths match the current project structure.
- [ ] Run retriever and generator evaluations.
- [ ] Run the RAG Triad evaluation.
- [ ] Run quality, safety, and operations evaluations.
- [ ] Run the complete orchestrator.
- [ ] Confirm every evaluator checks its configured thresholds.
- [ ] Confirm failed evaluations return a nonzero exit code.
- [ ] Distinguish metric failures from API or execution errors.
- [ ] Verify generated JSON reports and their test-case details.
- [ ] Run the unit/regression test suite.
- [ ] Document dataset sizes and evaluation limitations.
- [ ] Capture actual token usage before reporting API cost.
- [ ] Use larger samples and controlled concurrent-load tests before making production latency or capacity claims.
- [ ] Update `docs/` when evaluation methodology, metrics, or verified results change.
- [ ] Update this README when folders, modules, datasets, metrics, or reports change.

---

## 17. Recommended Evaluation Workflow

1. Add or update test cases in `datasets/`.
2. Run the relevant evaluation module or level runner.
3. Inspect terminal output and generated results in `reports/`.
4. Review failed cases and distinguish evaluation failures from execution errors.
5. Fix the relevant retrieval, generation, prompt, safety, or operational issue.
6. Rerun the affected evaluation.
7. Run the complete evaluation orchestrator after individual stages are ready.
8. Run relevant unit and regression tests.
9. Update the corresponding Markdown documentation in `docs/` with verified results.
10. Update this central README when the evaluation architecture or verified result snapshot changes.

---

## 18. Best Practices

1. Keep component, pipeline, and application evaluations separate.
2. Use representative and version-controlled golden datasets.
3. Keep evaluation thresholds explicit and configurable.
4. Do not lower thresholds simply to make an evaluation pass.
5. Store structured results for traceability and comparison.
6. Inspect individual failures instead of relying only on aggregate scores.
7. Keep API keys and other secrets out of source control.
8. Monitor LLM-judge token usage and provider limits.
9. Do not treat a successful API invocation as proof of answer correctness.
10. Do not treat an evaluation execution error as a metric failure.
11. Make each evaluator return a meaningful process exit code.
12. Run regression tests after changing retrieval, prompts, models, or application behavior.
13. Keep `docs/` explanations aligned with the actual evaluator implementation and latest verified reports.

---

## 19. Interview Summary

> "I organized the evaluation framework into component, pipeline, and application levels. Component-level evaluation measures retriever and generator performance independently. Pipeline-level evaluation uses the RAG Triad to assess contextual relevancy, faithfulness, and answer relevancy. Application-level evaluation covers quality, safety, and operations. I use evaluation datasets and DeepEval metrics, with a Groq-powered LLM judge for applicable evaluations. Each evaluator produces structured results, while individual Markdown documents explain the methodology and findings. A main orchestrator runs the complete workflow and summarizes the status. This makes evaluation repeatable, traceable, and easier to debug."

---

## 20. Main Execution Command

Run the complete evaluation workflow from the repository root:

```bash
uv run python -m evaluation.runners.run_all_evaluations
```
