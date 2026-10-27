 # Generator Evaluation Report

## 1. Overview

This document explains the generator evaluation workflow implemented in the **End-to-End LLMOps Project**, the initial results, what those results mean, and how to improve answer-generation quality.

**Evaluation status:** The evaluation script ran successfully, evaluated three test cases, and generated a JSON report. These results establish an initial baseline rather than a final benchmark.

The generator is responsible for producing accurate, relevant, and contextually supported answers using the information retrieved by the RAG pipeline.

This evaluation focuses on two key metrics:

- **Faithfulness:** Is the generated answer supported by the retrieved context?
- **Answer Relevancy:** Does the generated answer address the user's question?

## 2. What Is Being Evaluated?

The generator evaluation assesses the answer-generation component of the RAG application.

It checks whether the generated answers remain grounded in the supplied context and respond appropriately to the user's questions.

### Components involved

- **Evaluation dataset:** `evaluation/datasets/generator_eval.json`
- **RAG application:** `ConversationalRAG`
- **Vector store:** FAISS
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`
- **LLM for answer generation:** Groq-hosted `openai/gpt-oss-20b`
- **LLM judge:** `DeepEvalGroqModel`
- **Evaluation library:** DeepEval
- **Evaluation script:** `evaluation/component/evaluate_generator.py`
- **Output report:** `evaluation/reports/generator_eval_results.json`
- **Documentation report:** `evaluation/docs/generator_evaluation_report.md`

### Evaluation metrics

| Metric | What it measures |
|---|---|
| Faithfulness | Whether claims in the generated answer are supported by the retrieved context |
| Answer Relevancy | Whether the generated answer addresses the user's question |

## 3. Evaluation Workflow

The workflow runs as follows.

1. **Load the evaluation dataset.**  
   The script reads the test questions and their reference information from `generator_eval.json`.

2. **Load the RAG application.**  
   The `ConversationalRAG` implementation provides the retrieval and answer-generation functionality.

3. **Retrieve relevant context.**  
   The retriever obtains document chunks from the FAISS index for the current question.

4. **Generate an answer.**  
   The RAG application uses the question and retrieved context to generate an answer with the configured Groq model.

5. **Create a DeepEval test case.**  
   The script prepares the question, generated answer, and relevant context for evaluation.

6. **Evaluate faithfulness.**  
   DeepEval assesses whether the generated answer is supported by the supplied context.

7. **Evaluate answer relevancy.**  
   DeepEval assesses whether the generated answer addresses the original question.

8. **Record the results.**  
   The script records per-case scores and evaluation details in the JSON report and prints summary results.

### Workflow diagram

```text
Generator Evaluation Dataset
             |
             v
      Load RAG Application
             |
             v
      Receive Evaluation Question
             |
             v
      Retrieve Relevant Context
             |
             v
       Generate Answer Using LLM
             |
             v
       Create DeepEval Test Case
             |
             v
        Evaluate Generated Answer
             |
       +-----+-----+
       |           |
       v           v
  Faithfulness  Answer Relevancy
       |           |
       +-----+-----+
             |
             v
      Aggregate Evaluation Scores
             |
             v
     Save JSON Evaluation Report
```

## 4. Initial Evaluation Results

Three test cases were evaluated.

| Metric | Average score | Result |
|---|---:|---|
| Faithfulness | 1.000 | 100% |
| Answer Relevancy | 1.000 | 100% |

### Execution summary

| Item | Result |
|---|---:|
| Total test cases | 3 |
| Successful cases | 3 |
| Failed cases | 0 |
| Average faithfulness | 100% |
| Average answer relevancy | 100% |

**Interpretation:** All three test cases completed successfully, and both evaluation metrics achieved perfect average scores in this run.

### What does faithfulness mean?

Faithfulness measures whether the answer's claims are supported by the retrieved context.

For example, suppose the retrieved document states that a Transformer uses self-attention to model relationships between tokens.

- **Faithful answer:** Explains that self-attention helps the model capture relationships between tokens.
- **Potentially unfaithful answer:** Adds unsupported claims about the model's architecture or capabilities that are not established by the retrieved context.

The average faithfulness score was **1.000 (100%)**. The judge considered the evaluated answers fully supported by their contexts.

This is encouraging, but it does not prove that every generated answer will be factually correct. Faithfulness is about support from the provided context, which itself may be incomplete or incorrect.

### What does answer relevancy mean?

Answer relevancy measures whether the generated answer directly addresses the user's question.

For example, if the question asks what multi-head attention does:

- **Relevant answer:** Explains how multiple attention heads can capture different relationships in the input.
- **Irrelevant answer:** Provides a general explanation of neural networks without answering the question.

The average answer relevancy score was **1.000 (100%)**. The judge considered the answers relevant to their questions.

However, an answer can be relevant without being complete or factually correct. Answer relevancy should therefore be considered alongside faithfulness and other quality metrics.

## 5. What Is Working and What Needs Attention?

### Working

- The generator evaluation script executes successfully.
- All three test cases completed without a final evaluation failure.
- Both faithfulness and answer relevancy metrics returned scores.
- The initial results provide a baseline for future generator improvements.
- HTTP 429 rate-limit errors occurred during the run, but retries succeeded.

### Needs attention

- The dataset contains only three test cases, which is insufficient for a representative benchmark.
- Perfect scores do not guarantee correctness across different questions or documents.
- The LLM judge may produce inconsistent or incorrect assessments.
- The reference answers and evaluation contexts should be checked against the source documents.
- Rate limiting may affect larger evaluation runs.
- Completeness, correctness, style, and safety are not fully covered by these two generator metrics.

**Important distinction:** This report evaluates answer faithfulness and relevancy. It does not independently establish the overall quality, safety, or production readiness of the application.

## 6. How to Improve the Generator

Make one change at a time and rerun the same evaluation dataset so that results can be compared fairly.

### Step 1: Inspect individual test cases

Open:

`evaluation/reports/generator_eval_results.json`

Inspect the generated answer, retrieved context, metric scores, and available explanations for each test case.

Check:

- Does the answer address the exact question?
- Are its claims supported by the retrieved context?
- Does it introduce unsupported facts?
- Does it omit important information?
- Is the answer unnecessarily long or repetitive?
- Are the evaluation scores consistent with a manual review?

### Step 2: Expand the evaluation dataset

Add more questions that cover:

- Simple factual questions
- Definitions and explanations
- Comparisons between concepts
- Questions requiring information from multiple chunks
- Questions with incomplete or ambiguous context
- Questions where the retrieved context does not contain the answer

For each test case, verify that the expected answer is grounded in the source material.

### Step 3: Establish a baseline

Preserve the initial results and record:

- Generator model and configuration
- Evaluation dataset version
- Embedding model and index version
- Retrieval configuration
- Faithfulness and answer relevancy scores
- Failed cases and judge errors
- Response latency and token usage, where available

Use the same dataset and evaluation configuration when comparing future changes.

### Step 4: Improve the generation prompt

If answers contain unsupported claims, omit important information, or fail to address the question, review the prompt.

Potential improvements include:

- Instructing the model to answer using the supplied context.
- Telling the model to acknowledge insufficient evidence instead of guessing.
- Requesting a direct answer before optional elaboration.
- Avoiding repetitive or irrelevant explanations.
- Requiring the model to distinguish supported facts from uncertainty.

After changing the prompt, rerun the evaluation and compare both metrics.

### Step 5: Review retrieval and generation together

Poor generated answers may result from weak retrieval rather than the generator itself.

If the context does not contain the information needed to answer a question, prompt changes alone may not solve the problem.

Compare the retrieved context, generated answer, and evaluation scores to determine whether the issue originates in retrieval, generation, or both.

### Step 6: Add broader answer-quality metrics

The two current metrics do not cover every aspect of answer quality.

Consider adding application-level metrics for:

- **Correctness:** Does the answer match validated reference information?
- **Completeness:** Does it cover the important parts of the question?
- **Style:** Is it clear, concise, and appropriately structured?
- **Safety:** Does it avoid toxic content, prompt leakage, and PII leakage?

These metrics belong in the broader application-level evaluation stage of the project.

### Step 7: Handle judge rate limits

If HTTP 429 responses become frequent:

- Reduce concurrent evaluation requests.
- Use bounded retries with exponential backoff.
- Keep the judge model fixed when comparing experiments.
- Record failed evaluations separately.
- Avoid treating missing metric scores as successful results.

## 7. Recommended Improvement Order

1. Inspect the three existing generated answers and their contexts.
2. Validate the evaluation dataset against the source documents.
3. Expand the dataset with diverse questions and edge cases.
4. Preserve the initial results as the baseline.
5. Review the generation prompt for grounding and clarity.
6. Compare retrieval context with the generated answers.
7. Add correctness, completeness, and style evaluations.
8. Include safety checks in application-level evaluation.
9. Track latency, token usage, and cost.
10. Rerun the evaluation and compare the results before claiming an improvement.

## 8. How to Run the Evaluation

From the project root in Windows Command Prompt (CMD), run:

```cmd
uv run python -m evaluation.component.evaluate_generator
```

The script should load the evaluation dataset, execute the generator evaluation, calculate faithfulness and answer relevancy scores, and save the results.

Output JSON:

```text
evaluation/reports/generator_eval_results.json
```

Markdown documentation:

```text
evaluation/docs/generator_evaluation_report.md
```

If the FAISS index, generator configuration, or evaluation dataset changes, verify that the script uses the intended versions before comparing results.

 

## 9. Final Takeaway

The generator evaluation pipeline is operational, and the first baseline has been recorded.

The initial averages are:

- **Faithfulness:** 100%
- **Answer Relevancy:** 100%
- **Successful test cases:** 3 out of 3

The next priority is to validate the results on a larger and more diverse dataset, review individual answers, and extend the evaluation to broader application-quality metrics.

These results are a promising starting point, not proof of production readiness. A larger validated dataset and repeatable evaluation runs are needed to establish confidence in generator quality.
