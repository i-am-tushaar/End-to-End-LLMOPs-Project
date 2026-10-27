
def retrieval_metrics(
    retrieved_ids: list[str],
    relevant_ids: list[str],
) -> dict[str, float]:
    relevant = set(relevant_ids)

    if not relevant:
        raise ValueError("relevant_ids must not be empty")

    hits = [item in relevant for item in retrieved_ids]
    hit_count = sum(hits)

    recall = len(set(retrieved_ids) & relevant) / len(relevant)
    precision = hit_count / len(retrieved_ids) if retrieved_ids else 0.0

    reciprocal_rank = 0.0
    for rank, is_relevant in enumerate(hits, start=1):
        if is_relevant:
            reciprocal_rank = 1.0 / rank
            break

    return {
        "hit_rate": float(hit_count > 0),
        "recall_at_k": recall,
        "precision_at_k": precision,
        "mrr": reciprocal_rank,
    }
