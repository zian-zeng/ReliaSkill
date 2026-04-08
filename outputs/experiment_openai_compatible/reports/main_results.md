# AutoSkill Experiment Report

- Tools source: `data/raw/public_mcp_filesystem_subset.json`
- Benchmark source: `data/eval/public_mcp_filesystem_benchmark.jsonl`

## Packaging Summary

| Condition | Valid Rate | Avg Examples | Avg Template Fields |
| --- | ---: | ---: | ---: |
| raw_mcp | 1.0000 | 0.00 | 0.00 |
| schema_only | 1.0000 | 1.60 | 2.00 |
| autoskill_base | 1.0000 | 2.00 | 2.00 |

## Benchmark Summary

| Condition | Exact Match | Argument Validity | Required Arg Recall | Hallucinated Args |
| --- | ---: | ---: | ---: | ---: |
| raw_mcp | 1.0000 | 1.0000 | 1.0000 | 0 |
| schema_only | 1.0000 | 1.0000 | 1.0000 | 0 |
| autoskill_base | 1.0000 | 1.0000 | 1.0000 | 0 |

## Headline

The main comparison to track is whether `autoskill_base` improves exact-match and argument-validity metrics over `raw_mcp` while staying schema-valid.
