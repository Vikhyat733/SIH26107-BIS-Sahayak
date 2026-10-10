import json

failed_queries = [
    'TMT bar standard', 
    'rebar BIS standard', 
    'Which IS standard covers reinforcement bars?', 
    'What standard should I use for steel bars used to reinforce concrete?', 
    'Which Indian Standard covers reinforcement steel used in concrete?', 
    'deformed steel reinforcement standard'
]

res = json.load(open('eval_results.json'))
for r in res:
    if r['query'] in failed_queries:
        print(f"Query: {r['query']}")
        print(f"BM25 Cands: {r['bm25_candidates']}")
        print(f"Rerank Cands: {r['reranked_candidates']}")
        print(f"Rerank Scores: {r['rerank_scores']}")
        print("-" * 40)
