# AutoSkill Method Ablation

- Tools source: `data\raw\public_mcp_filesystem_subset.json`
- Benchmark source: `data\eval\public_mcp_filesystem_benchmark.jsonl`

| Method Variant | Exact Match | Argument Validity | Required Arg Recall | Avg Semantic Hints | Avg Examples |
| --- | ---: | ---: | ---: | ---: | ---: |
| base_only | 0.6667 | 0.8667 | 0.9000 | 0.00 | 2.00 |
| semantic_concise | 1.0000 | 1.0000 | 1.0000 | 4.20 | 2.00 |
| semantic_dense | 1.0000 | 1.0000 | 1.0000 | 4.20 | 3.40 |
| selected | 1.0000 | 1.0000 | 1.0000 | 4.20 | 3.40 |
