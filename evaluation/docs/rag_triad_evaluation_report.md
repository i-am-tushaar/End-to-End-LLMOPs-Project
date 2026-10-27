# RAG Triad Evaluation Report

## 1. Overview

This document explains the RAG Triad evaluation workflow implemented in the **End-to-End LLMOps Project**, the initial evaluation results, what those results mean, and how to improve the complete Retrieval-Augmented Generation (RAG) pipeline.

**Evaluation status:** The evaluation script ran successfully, generated scores for all three test cases, and saved the results to a JSON report. These results establish an initial baseline rather than a final benchmark.

The RAG Triad evaluates three important dimensions:

- **Contextual Relevancy:** Is the retrieved context relevant to the question?
- **Faithfulness:** Is the generated answer supported by the retrieved context?
- **Answer Relevancy:** Does the generated answer address the user's question?

## 2. What Is Being Evaluated?

The RAG Triad evaluates retrieval and answer generation together. Unlike component-level evaluation, which tests the retriever and generator separately, this evaluation provides a combined view of the RAG pipeline.

### Components involved

- **Evaluation dataset:** `evaluation/datasets/rag_triad_eval.json`
- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vector store:** FAISS
- **Retrieval strategy:** Maximum Marginal Relevance (MMR)
- **LLM for answer generation:** Groq-hosted `openai/gpt-oss-20b`
- **LLM judge:** `DeepEvalGroqModel`, using `openai/gpt-oss-20b`
- **Evaluation library:** DeepEval
- **Evaluation script:** `evaluation/pipeline/evaluate_rag_triad.py`
- **Output report:** `evaluation/reports/rag_triad_results.json`
- **Documentation report:** `evaluation/docs/rag_triad_evaluation_report.md`

### Evaluation metrics

| Metric | What it measures |
|---|---|
| Contextual Relevancy | How relevant the retrieved context is to the user's question |
| Faithfulness | Whether the generated answer is supported by the retrieved context |
| Answer Relevancy | Whether the generated answer directly addresses the user's question |

## 3. Evaluation Workflow

The evaluation workflow runs as follows.

1. **Load the evaluation dataset.**  
   The script reads the evaluation questions and reference answers from `rag_triad_eval.json`.

2. **Load the RAG application.**  
   The `ConversationalRAG` implementation loads the components needed to generate answers.

3. **Load the FAISS index.**  
   The script uses the configured index at:

   `faiss_index/session_20261026_215230_88296173`

4. **Configure the retriever.**  
   The current retrieval settings are:

   - `TOP_K = 3`
   - `FETCH_K = 10`
   - `LAMBDA_MULT = 0.5`
   - `search_type = "mmr"`

5. **Generate the answer.**  
   Each evaluation question is passed to the RAG application, which generates an answer using the retrieved information.

6. **Collect retrieved context.**  
   The script retrieves document chunks associated with each question for evaluation.

7. **Create DeepEval test cases.**  
   The question, generated answer, and retrieved context are used to create `LLMTestCase` instances.

8. **Evaluate the RAG Triad.**  
   DeepEval evaluates contextual relevancy, faithfulness, and answer relevancy using the configured Groq-hosted judge model.

9. **Record the results.**  
   The script records per-case metric scores, evaluation status, and available explanations in the JSON report.

### Workflow diagram

```text
Evaluation dataset
(questions + reference answers)
             |
             v
       Load RAG application
             |
             v
        Load FAISS index
             |
             v
    Configure MMR retriever
             |
             v
    Retrieve document chunks
             |
             v
      Generate RAG answer
             |
             v
      Build DeepEval test case
             |
             v
     Evaluate the RAG Triad
             |
      +------+------+
      |      |      |
      v      v      v
 Context  Faithfulness  Answer
Relevancy              Relevancy
      |      |      |
      +------+------+
             |
             v
  Save scores and evaluation results
      to rag_triad_results.json
```

## 4. Initial Evaluation Results

Three test cases were evaluated.

| Test case | Contextual Relevancy | Faithfulness | Answer Relevancy |
|---|---:|---:|---:|
| Transformer architecture | 1.000 | 1.000 | 1.000 |
| Self-attention in the Transformer | 1.000 | 1.000 | 1.000 |
| Multi-head attention | 0.600 | 1.000 | 1.000 |
| **Average** | **0.867 (86.7%)** | **1.000 (100%)** | **1.000 (100%)** |

**Metric threshold:** `0.7`

The evaluation script completed all three cases. However, the multi-head attention case scored below the configured threshold for contextual relevancy.

### What does contextual relevancy mean?

Contextual relevancy measures whether the retrieved context contains information relevant to the question.

The average score is **0.867 (86.7%)**. The multi-head attention test scored **0.600**, below the configured threshold of `0.7`.

This suggests that the retrieved context for that question needs investigation. Inspect the retrieved chunks and the metric's explanation before deciding whether the issue comes from retrieval, the evaluation data, or the judge.

### What does faithfulness mean?

Faithfulness evaluates whether the generated answer is supported by the retrieved context rather than introducing unsupported claims.

The average score is **1.000 (100%)** across the three cases. The judge considered the generated answers fully supported by their evaluated contexts.

This is encouraging, but it does not establish that every possible answer will be faithful. The result is based on only three test cases and an LLM-based evaluator.

### What does answer relevancy mean?

Answer relevancy measures whether the generated answer addresses the question being asked.

The average score is **1.000 (100%)**. All three cases received a perfect answer relevancy score in this run.

This indicates that the answers were judged to address their questions directly. It does not independently establish factual correctness, completeness, or production reliability.

## 5. What Is Working and What Needs Attention?

### Working

- The RAG Triad evaluation script executes successfully.
- All three evaluation cases complete and produce metric scores.
- The application generates answers using the configured RAG pipeline.
- All three faithfulness scores are `1.000`.
- All three answer relevancy scores are `1.000`.
- The JSON report is saved for further inspection.
- The results establish a baseline for future RAG pipeline improvements.

### Needs attention

- The evaluation dataset contains only three questions, which is insufficient for a reliable, representative benchmark.
- The multi-head attention contextual relevancy score is `0.600`, below the `0.7` threshold.
- Perfect faithfulness and answer relevancy scores do not guarantee overall application quality.
- The retrieved context used for evaluation should be verified against the context actually used to generate each answer.
- LLM judge results can vary and should be reviewed against source documents and manually checked examples.
- HTTP 429 rate-limit responses occurred during the run, although retries succeeded. Larger evaluations may require controlled request rates and retry handling.
- Reference answers and evaluation cases should be verified against the original source material.

**Important distinction:** The script completed all three cases, but that does not mean every metric passed its threshold. The multi-head attention contextual relevancy metric did not pass.

## 6. How to Improve the RAG Pipeline

Make one change at a time and rerun the same evaluation dataset so that results can be compared fairly.

### Step 1: Investigate the low-scoring case

Start with the multi-head attention test case.

Open:

`evaluation/reports/rag_triad_results.json`

Inspect the contextual relevancy score and its explanation, along with the retrieved context and generated answer.

Check:

- Does the retrieved context directly explain multi-head attention?
- Are the most relevant chunks ranked near the top?
- Are any chunks unrelated or repetitive?
- Does the generated answer use the relevant evidence?
- Is the evaluator's explanation consistent with the source document?

Do not change retrieval parameters until the evidence has been inspected.

### Step 2: Improve the evaluation dataset

Expand the dataset beyond three cases. Include questions covering:

- Definitions and direct facts
- Conceptual explanations
- Comparisons between related concepts
- Questions requiring evidence from multiple document sections
- Questions that test whether the application handles insufficient evidence appropriately

Keep reference answers grounded in the source documents and manually validate them.

### Step 3: Establish a reproducible baseline

Record the following details for each experiment:

- Embedding model
- Index version and source documents
- Chunk size and overlap
- Retrieval strategy and parameters
- Evaluation dataset version
- Generator model
- Judge model
- Contextual relevancy, faithfulness, and answer relevancy scores
- Failed or below-threshold cases
- Latency, token usage, and cost where available

Keep the initial report unchanged so that future improvements can be compared against it.

### Step 4: Experiment with retrieval settings

After reviewing the retrieved chunks, test one parameter at a time.

- **`TOP_K`:** Compare values such as 3, 5, and 8. More chunks may improve coverage but introduce irrelevant information.
- **`FETCH_K`:** Compare candidate pool sizes such as 10, 20, and 30, depending on index size.
- **`LAMBDA_MULT`:** Compare values such as 0.25, 0.5, and 0.75. Lower values generally emphasize diversity, while higher values emphasize similarity.
- **Search strategy:** Compare MMR with ordinary similarity search using the same dataset.

These are experiments, not guaranteed improvements. Select the configuration that performs consistently across a larger evaluation dataset.

### Step 5: Investigate chunking and embeddings

If the retriever consistently misses relevant information or returns incomplete context:

- Review the chunk size and overlap used during ingestion.
- Check whether document headings, paragraphs, tables, and page boundaries are preserved appropriately.
- Compare embedding models on the same dataset.
- Rebuild the FAISS index when changing embedding models or chunking.
- Ensure the embedding model used during retrieval matches the model used to build the index.

### Step 6: Consider reranking

If relevant chunks appear in the initial retrieval results but are poorly ranked, test a cross-encoder reranker.

Compare the original and reranked results using the same evaluation dataset and metrics.

A reranker adds computation and latency, so retain it only if the improvement in retrieval quality justifies the additional cost.

### Step 7: Improve evaluation reliability

If HTTP 429 responses become frequent:

- Reduce concurrent judge requests.
- Add bounded exponential backoff and retry handling.
- Keep the judge model and evaluation settings fixed during comparisons.
- Record failed evaluations separately.
- Do not silently treat missing scores as zero or as successful evaluations.

For stronger confidence, manually inspect a sample of evaluated answers and compare judge scores against human judgments.

## 7. Recommended Improvement Order

1. Inspect the multi-head attention case and its contextual relevancy explanation.
2. Verify the retrieved context against the source document.
3. Confirm that the context evaluated by DeepEval matches the context used during answer generation.
4. Expand the dataset with more representative questions.
5. Preserve the initial JSON report as the baseline.
6. Test `TOP_K`, `FETCH_K`, and `LAMBDA_MULT` one at a time.
7. Compare MMR with similarity search.
8. Investigate chunking and embedding alternatives if necessary.
9. Test reranking if retrieval quality remains insufficient.
10. Rerun the full dataset and compare all three metrics.
11. Record latency, cost, and reliability as part of application-level evaluation.

## 8. How to Run the Evaluation

From the project root in Windows Command Prompt (CMD), run:

```cmd
uv run python -m evaluation.pipeline.evaluate_rag_triad
```

The script should load the evaluation dataset, run the RAG pipeline, calculate the three metrics, and save the JSON report.

Output JSON:

```text
evaluation/reports/rag_triad_results.json
```

Markdown documentation:

```text
evaluation/docs/rag_triad_evaluation_report.md
```

If the FAISS index changes, verify that the configured `FAISS_INDEX_PATH` points to the intended index before rerunning the evaluation.

 

## 9. Final Takeaway

The RAG Triad evaluation pipeline is operational, and the first baseline has been recorded.

The initial averages are:

- **Contextual Relevancy:** 86.7%
- **Faithfulness:** 100%
- **Answer Relevancy:** 100%

The main area to investigate is contextual relevancy for the multi-head attention test case. The next priority is to expand the dataset and verify that the evaluated context matches the context used during generation.

These results are promising initial evidence, not proof of production readiness. A larger, validated dataset and reproducible experiments are needed to establish confidence in the complete RAG pipeline.
