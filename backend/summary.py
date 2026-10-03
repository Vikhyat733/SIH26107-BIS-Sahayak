import json

with open("eval_results.json") as f:
    data = json.load(f)

print(f"Total Queries: {len(data)}")
print(f"Passed Grounding: {sum(1 for d in data if d['grounding_passed'])}")
print("-" * 40)
for d in data:
    top_doc = d['reranked_candidates'][0] if d['reranked_candidates'] else 'None'
    top_score = d['rerank_scores'][0] if d['rerank_scores'] else 0
    bm25_top = d['bm25_candidates'][0] if d['bm25_candidates'] else 'None'
    bm25_score = d['bm25_scores'][0] if d['bm25_scores'] else 0
    
    print(f"Q: {d['query']}")
    print(f"Intent: {d['intent']}")
    print(f"Answered: {d['confidence'] > 0}")
    print(f"Grounding Passed: {d['grounding_passed']}")
    print(f"Top Doc (Reranked): {top_doc} (Score: {top_score:.2f})")
    print(f"Top Doc (BM25): {bm25_top} (Score: {bm25_score:.2f})")
    print("-" * 40)
