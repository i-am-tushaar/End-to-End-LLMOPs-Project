evaluation/
│
├── datasets/
│   ├── retriever_eval.json
│   ├── generator_eval.json
│   ├── rag_triad_eval.json
│   ├── application_quality_eval.json
│   └── safety_eval.json
│
├── component/
│   ├── evaluate_retriever.py          # Done
│   └── evaluate_generator.py          # Done
│
├── pipeline/
│   └── evaluate_rag_triad.py          # Next
│
├── application/
│   ├── evaluate_quality.py
│   ├── evaluate_safety.py
│   └── evaluate_operations.py
│
├── judges/
│   └── deepeval_groq_model.py         # Existing
│
├── reports/
│   ├── retriever_eval_results.json    # Existing
│   ├── generator_eval_results.json    # Existing
│   ├── rag_triad_results.json
│   ├── application_quality_results.json
│   ├── safety_results.json
│   ├── operations_results.json
│   └── evaluation_summary.json
│
└── docs/
    ├── retriever_evaluation_report.md # Existing
    ├── generator_evaluation_report.md # Existing
    ├── rag_triad_report.md
    ├── application_quality_report.md
    ├── safety_report.md
    └── operations_report.md