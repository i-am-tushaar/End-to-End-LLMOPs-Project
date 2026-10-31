# Complete LLMOps Evaluation Orchestrator

## 1. Introduction

`run_all_evaluations.py` is the central orchestrator of the End-to-End LLMOps evaluation framework.

It executes all three evaluation levels:

1. Component-Level Evaluation
2. Pipeline-Level Evaluation
3. Application-Level Evaluation

Instead of manually executing individual evaluation scripts, the orchestrator runs them sequentially, tracks execution time, checks execution status, and generates a consolidated evaluation summary.

Its main objective is to automate the complete evaluation workflow and identify performance, quality, safety, and operational issues across the RAG application.

---

## 2. Folder Structure

The evaluation module follows this structure:

```text
evaluation/
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
│   │   └── evaluate_quality.py
│   │
│   ├── safety/
│   │   ├── evals_safety.py
│   │   ├── evaluate_leakage.py
│   │   ├── evaluate_toxicity.py
│   │   ├── evaluate_scope.py
│   │   └── evaluate_safety.py
│   │
│   └── operations/
│       └── evaluate_operations.py
│
└── runners/
    ├── __init__.py
    ├── run_all_evaluations.py
    └── README.md
```

### Responsibilities of the evaluation files

| File | Responsibility |
|---|---|
| `evaluate_retriever.py` | Evaluates retrieval performance. |
| `evaluate_generator.py` | Evaluates generated response quality. |
| `evals_component.py` | Executes retriever and generator evaluations. |
| `evaluate_rag_triad.py` | Evaluates the complete RAG pipeline. |
| `evaluate_quality.py` | Evaluates application response quality. |
| `evals_safety.py` | Executes all safety evaluations. |
| `evaluate_leakage.py` | Evaluates information leakage. |
| `evaluate_toxicity.py` | Evaluates toxic or harmful responses. |
| `evaluate_scope.py` | Evaluates scope adherence. |
| `evaluate_safety.py` | Evaluates application safety. |
| `evaluate_operations.py` | Evaluates operational performance. |
| `evals_application.py` | Coordinates quality, safety, and operations evaluations. |
| `run_all_evaluations.py` | Executes the complete evaluation pipeline. |

---

## 3. Three Levels of Evaluation

### 3.1 Component-Level Evaluation

**Definition:**

Component-level evaluation measures the performance of individual components of the RAG application independently.

It helps identify whether the retriever or generator is responsible for poor application performance.

**Execution module:**

`evaluation.component.evals_component`

**Evaluations performed:**

| Component | Evaluation | Purpose |
|---|---|---|
| Retriever | `evaluate_retriever.py` | Measures the quality and relevance of retrieved documents. |
| Generator | `evaluate_generator.py` | Measures the quality and correctness of generated responses. |

**Important metrics:**

Retriever:
- Contextual Precision
- Contextual Recall
- Retrieval Relevance

Generator:
- Faithfulness
- Answer Relevancy
- Answer Correctness

**Common failures and solutions:**

| Failure | Possible reason | Solution |
|---|---|---|
| Low Contextual Precision | Irrelevant documents are retrieved. | Improve embeddings, retrieval strategy, and reranking. |
| Low Contextual Recall | Relevant information is missing from retrieved documents. | Improve chunking, overlap, and retrieval parameters. |
| Low Faithfulness | Generated answers contain unsupported information. | Improve prompts and context-grounding instructions. |
| Low Answer Relevancy | Answers do not directly address questions. | Optimize generation prompts and retrieved context. |
| Low Correctness | Generated answers contain incorrect information. | Improve retrieval quality and generation configuration. |

### 3.2 Pipeline-Level Evaluation

**Definition:**

Pipeline-level evaluation measures the performance of the complete RAG pipeline by evaluating the interaction between retrieval and generation.

It helps determine whether the complete RAG workflow produces relevant, accurate, and contextually supported answers.

**Execution module:**

`evaluation.pipeline.evaluate_rag_triad`

**RAG Triad metrics:**

| Metric | Purpose |
|---|---|
| Contextual Relevancy | Checks whether retrieved context is relevant to the user's question. |
| Faithfulness | Checks whether generated answers are supported by retrieved context. |
| Answer Relevancy | Checks whether generated answers address the user's question. |

**Common failures and solutions:**

| Failure | Possible reason | Solution |
|---|---|---|
| Low Contextual Relevancy | Retrieved context contains irrelevant information. | Improve retrieval and document chunking. |
| Low Faithfulness | Answers contain information not supported by context. | Improve prompts and context-grounding instructions. |
| Low Answer Relevancy | Answers do not address the user's query. | Improve query handling and generation prompts. |

### 3.3 Application-Level Evaluation

**Definition:**

Application-level evaluation measures the overall quality, safety, and operational performance of the complete application.

It verifies whether the application is reliable, safe, and suitable for its intended use.

**Execution module:**

`evaluation.application.evals_application`

It coordinates three evaluation categories.

**A. Quality Evaluation**

Module: `evaluate_quality.py`

Measures the quality of application responses.

Evaluation areas:
- Correctness
- Completeness
- Response relevance
- Style and consistency

**B. Safety Evaluation**

Module: `evals_safety.py`

Executes four safety evaluations:

| Evaluation | Purpose |
|---|---|
| Leakage | Checks course content, prompt, and PII leakage. |
| Toxicity | Checks harmful, abusive, or toxic responses. |
| Scope | Checks whether the application stays within its intended domain. |
| Application Safety | Checks appropriate handling of safety-sensitive requests. |

**C. Operations Evaluation**

Module: `evaluate_operations.py`

Evaluates operational performance.

Common evaluation areas:
- Latency
- Time to First Token (TTFT)
- P95 and P99 latency
- API cost
- Reliability
- Service Level Objectives (SLOs)

The exact metrics and thresholds depend on the implementation of the respective evaluation modules.

---

## 4. How run_all_evaluations.py Works

The main orchestrator executes the evaluation modules sequentially using Python's `subprocess` module.

### Execution workflow

**Step 1: Initialize the evaluation pipeline**

The script initializes the complete evaluation process and records the starting time.

**Step 2: Execute component-level evaluation**

Runs:

```bash
uv run python -m evaluation.component.evals_component
```

This executes:
- Retriever evaluation
- Generator evaluation

**Step 3: Execute pipeline-level evaluation**

Runs:

```bash
uv run python -m evaluation.pipeline.evaluate_rag_triad
```

This evaluates the complete RAG pipeline using RAG Triad metrics.

**Step 4: Execute application-level evaluation**

Runs:

```bash
uv run python -m evaluation.application.evals_application
```

This coordinates:
- Quality evaluation
- Safety evaluation
- Operations evaluation

**Step 5: Track execution status**

The orchestrator records:
- Evaluation name
- Evaluation level
- Execution status
- Execution duration
- Process return code

**Step 6: Generate final summary**

After all stages finish, the orchestrator displays:
- Total evaluation stages
- Passed stages
- Failed stages
- Execution errors
- Total execution time
- Overall pipeline status

**Step 7: Return final exit status**

If every stage passes, the script returns success.

If any stage fails or encounters an execution error, the script returns a nonzero exit code.

---

## 5. Overall Evaluation Workflow

```text
                 run_all_evaluations.py
                           |
             -----------------------------
             |             |             |
          Component      Pipeline     Application
             |             |             |
       evals_component  RAG Triad  evals_application
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

The orchestrator executes the three major stages in sequence.

Within each stage, the corresponding evaluation module manages its own evaluation scripts.

---

## 6. Execution Commands

Run the complete evaluation pipeline from the project root directory:

```bash
uv run python -m evaluation.runners.run_all_evaluations
```

### Run individual evaluation levels

**Component-level:**

```bash
uv run python -m evaluation.component.evals_component
```

**Pipeline-level:**

```bash
uv run python -m evaluation.pipeline.evaluate_rag_triad
```

**Application-level:**

```bash
uv run python -m evaluation.application.evals_application
```

### Run individual application evaluations

**Quality:**

```bash
uv run python -m evaluation.application.quality.evaluate_quality
```

**Safety:**

```bash
uv run python -m evaluation.application.safety.evals_safety
```

**Operations:**

```bash
uv run python -m evaluation.application.operations.evaluate_operations
```

---

## 7. Understanding Evaluation Statuses

| Status | Meaning |
|---|---|
| PASSED | The evaluation process completed successfully according to its implemented checks. |
| FAILED | The evaluation completed but returned a failure status. |
| ERROR | An unexpected execution error occurred. |

### Evaluation Failure vs Execution Error

**Evaluation Failure**

An evaluation failure occurs when the evaluation executes successfully but one or more test cases or configured thresholds do not meet the expected criteria.

Example:

```text
Total Test Cases : 15
Passed           : 14
Failed           : 1
Errors           : 0

Status: FAILED
```

**Solution:**

1. Identify the failed test case.
2. Inspect its input, expected output, and actual output.
3. Identify the component responsible.
4. Improve the retrieval strategy, prompt, or application logic.
5. Rerun the affected evaluation.

**Execution Error**

An execution error occurs when the evaluation cannot complete because of a technical or external issue.

Example:

```text
Error: Groq API Rate Limit Exceeded
Error: Model Not Found
Error: Missing API Key

Status: ERROR
```

**Solution:**

1. Check the error traceback.
2. Verify API keys and model configuration.
3. Check package dependencies.
4. Verify module paths and input files.
5. Resolve the issue and rerun the evaluation.

**Important:** An API error does not automatically indicate that the application failed its evaluation. It means the evaluation could not be completed.

---

## 8. Common Failures and Troubleshooting

| Failure | Evaluation level | Recommended solution |
|---|---|---|
| Poor document retrieval | Component | Improve chunking, embeddings, and retrieval parameters. |
| Missing relevant context | Component | Improve contextual recall and retrieval configuration. |
| Hallucinated answers | Component / Pipeline | Improve faithfulness and context-grounding instructions. |
| Irrelevant answers | Component / Pipeline | Improve answer relevancy and prompt design. |
| Prompt leakage | Application | Strengthen system instructions and prevent internal prompt disclosure. |
| PII leakage | Application | Add privacy protection and sensitive-information filtering. |
| Toxic responses | Application | Improve safety instructions and response validation. |
| Out-of-scope responses | Application | Strengthen domain restrictions and scope handling. |
| High latency | Application | Optimize retrieval, model selection, and response generation. |
| High API cost | Application | Reduce token usage and optimize model selection. |
| Groq quota exceeded | Execution | Wait for quota reset or configure another available judge model. |
| Import errors | Execution | Verify module paths, package structure, and dependencies. |

---

## 9. LLM Judge and DeepEval Integration

The evaluation framework uses DeepEval and a Groq-powered LLM judge.

### What is an LLM Judge?

An LLM judge is a language model used to evaluate responses generated by another language model against defined criteria.

For example, it can assess:
- Whether an answer is correct.
- Whether an answer is supported by retrieved context.
- Whether an answer is relevant.
- Whether sensitive information is exposed.
- Whether a response follows safety requirements.

### Why DeepEval?

DeepEval provides evaluation metrics, test cases, and evaluation utilities for testing LLM applications.

### Why Groq?

Groq provides API access to the configured judge model for running LLM-based evaluations.

### Important considerations

- Verify the configured Groq model name.
- Keep the API key in environment variables.
- Monitor daily token and request limits.
- Use consistent judge configurations across comparable experiments.
- Review failed test cases instead of relying only on average scores.
- Treat API errors separately from genuine evaluation failures.

---

## 10. Reports and Result Analysis

Each evaluation module is responsible for generating its corresponding evaluation report.

The reports should be reviewed to understand:
- Total test cases
- Passed test cases
- Failed test cases
- Evaluation errors
- Metric scores
- Configured thresholds
- Overall evaluation status

### What to do when the complete pipeline fails

1. Identify the failed stage in the final summary.
2. Open the corresponding evaluation report.
3. Inspect failed test cases and metric scores.
4. Determine whether the issue is an evaluation failure or execution error.
5. Fix the responsible component.
6. Rerun the affected module.
7. Rerun the complete evaluation pipeline.

---

## 11. Best Practices

1. Execute individual evaluations during development and debugging.
2. Run the complete pipeline before major releases.
3. Maintain separate golden datasets for different evaluation categories.
4. Keep evaluation thresholds configurable.
5. Save evaluation reports for future comparisons.
6. Do not change thresholds just to make evaluations pass.
7. Monitor API usage when using an LLM judge.
8. Investigate failed cases instead of relying only on average scores.
9. Make sure every evaluation module returns a nonzero exit code when its checks fail.
10. Keep the orchestrator modular and easy to maintain.

---

## 12. Final Summary

`run_all_evaluations.py` acts as the central execution point for the complete LLMOps evaluation framework.

| Evaluation level | Main objective |
|---|---|
| Component-Level | Evaluate retriever and generator independently. |
| Pipeline-Level | Evaluate the complete RAG workflow using RAG Triad metrics. |
| Application-Level | Evaluate application quality, safety, and operational performance. |

The purpose of this architecture is to make the evaluation process automated, modular, repeatable, and easier to debug.

It provides a consolidated view of the RAG application's component performance, end-to-end response quality, application safety, and operational reliability.

**Main execution command:**

```bash
uv run python -m evaluation.runners.run_all_evaluations
```
