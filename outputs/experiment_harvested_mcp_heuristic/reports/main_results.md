# AutoSkill Experiment Report

- Tools source: `data/raw/harvested_mcp_reference_servers.json`
- Benchmark source: `data/eval/public_mcp_filesystem_benchmark.jsonl`

## Packaging Summary

| Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | ---: | ---: | ---: | ---: |
| raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| schema_only | 0.8704 | 1.33 | 1.59 | 0.00 |
| retrieved_docs | 0.8704 | 1.33 | 1.59 | 0.00 |
| retrieved_candidates | 0.8519 | 1.48 | 1.59 | 0.00 |
| retrieved_memory | 0.8519 | 0.98 | 1.59 | 0.00 |
| autoskill_base | 0.8704 | 1.76 | 1.59 | 0.63 |

## Benchmark Summary

| Condition | Exact Match | Argument Validity | Required Arg Recall | Retrieval Hit@K | Avg Target Rank | Hallucinated Args |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw_mcp | 0.6000 | 0.8222 | 0.8667 |  |  | 0 |
| schema_only | 0.4000 | 0.8222 | 0.6889 |  |  | 8 |
| retrieved_docs | 0.4000 | 0.8222 | 0.6889 | 1.0000 | 1.10 | 8 |
| retrieved_candidates | 0.4000 | 0.8556 | 0.7111 | 1.0000 | 1.10 | 8 |
| retrieved_memory | 0.6667 | 0.9667 | 0.8444 |  |  | 6 |
| autoskill_base | 0.6667 | 1.0000 | 0.8667 |  |  | 6 |

## Hidden-Tool Routing Summary

| Condition | Tool Accuracy | Joint Exact Match | Argument Validity | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw_mcp | 0.6667 | 0.4000 | 0.5556 | 0.6667 | 1.00 |
| schema_only | 0.6667 | 0.2667 | 0.5556 | 0.6667 | 1.00 |
| retrieved_docs | 0.6000 | 0.2000 | 0.4889 | 0.6667 | 1.10 |
| retrieved_candidates | 0.9333 | 0.4000 | 0.7889 | 1.0000 | 1.07 |
| retrieved_memory | 0.8667 | 0.5333 | 0.8333 | 0.9333 | 1.07 |
| autoskill_base | 1.0000 | 0.6667 | 1.0000 | 1.0000 | 1.00 |

## Benchmark By Split

| Split | Condition | Tasks | Exact Match | 95% CI | Argument Validity | Retrieval Hit@K | Avg Target Rank |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| dev | raw_mcp | 6 | 0.8333 | [0.5000, 1.0000] | 0.9444 |  |  |
| dev | schema_only | 6 | 0.5000 | [0.1667, 0.8333] | 0.9444 |  |  |
| dev | retrieved_docs | 6 | 0.5000 | [0.1667, 0.8333] | 0.9444 | 1.0000 | 1.00 |
| dev | retrieved_candidates | 6 | 0.5000 | [0.1667, 0.8333] | 0.9444 | 1.0000 | 1.00 |
| dev | retrieved_memory | 6 | 0.6667 | [0.3333, 1.0000] | 1.0000 |  |  |
| dev | autoskill_base | 6 | 0.6667 | [0.3333, 1.0000] | 1.0000 |  |  |
| test | raw_mcp | 9 | 0.4444 | [0.1111, 0.7778] | 0.7407 |  |  |
| test | schema_only | 9 | 0.3333 | [0.1111, 0.6667] | 0.7407 |  |  |
| test | retrieved_docs | 9 | 0.3333 | [0.1111, 0.6667] | 0.7407 | 1.0000 | 1.17 |
| test | retrieved_candidates | 9 | 0.3333 | [0.1111, 0.6667] | 0.7963 | 1.0000 | 1.17 |
| test | retrieved_memory | 9 | 0.6667 | [0.3333, 0.8889] | 0.9444 |  |  |
| test | autoskill_base | 9 | 0.6667 | [0.3333, 0.8889] | 1.0000 |  |  |

## Hidden-Tool Routing By Split

| Split | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| dev | raw_mcp | 6 | 0.8333 | 0.6667 | 0.8333 | 1.00 |
| dev | schema_only | 6 | 0.8333 | 0.3333 | 0.8333 | 1.00 |
| dev | retrieved_docs | 6 | 0.6667 | 0.1667 | 0.6667 | 1.00 |
| dev | retrieved_candidates | 6 | 1.0000 | 0.5000 | 1.0000 | 1.00 |
| dev | retrieved_memory | 6 | 0.6667 | 0.3333 | 0.8333 | 1.20 |
| dev | autoskill_base | 6 | 1.0000 | 0.6667 | 1.0000 | 1.00 |
| test | raw_mcp | 9 | 0.5556 | 0.2222 | 0.5556 | 1.00 |
| test | schema_only | 9 | 0.5556 | 0.2222 | 0.5556 | 1.00 |
| test | retrieved_docs | 9 | 0.5556 | 0.2222 | 0.6667 | 1.17 |
| test | retrieved_candidates | 9 | 0.8889 | 0.3333 | 1.0000 | 1.11 |
| test | retrieved_memory | 9 | 1.0000 | 0.6667 | 1.0000 | 1.00 |
| test | autoskill_base | 9 | 1.0000 | 0.6667 | 1.0000 | 1.00 |

## Benchmark By Tool

| Tool | Condition | Tasks | Exact Match | Argument Validity | Required Arg Recall | Retrieval Hit@K | Avg Target Rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| create_directory | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| create_directory | retrieved_docs | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_memory | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| create_directory | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | raw_mcp | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | schema_only | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | retrieved_docs | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | retrieved_candidates | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | retrieved_memory | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | autoskill_base | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| read_text_file | raw_mcp | 5 | 0.6000 | 0.8000 | 0.8667 |  |  |
| read_text_file | schema_only | 5 | 0.0000 | 0.8000 | 0.4667 |  |  |
| read_text_file | retrieved_docs | 5 | 0.0000 | 0.8000 | 0.4667 | 1.0000 | 1.00 |
| read_text_file | retrieved_candidates | 5 | 0.0000 | 0.9000 | 0.5333 | 1.0000 | 1.00 |
| read_text_file | retrieved_memory | 5 | 0.0000 | 0.9000 | 0.5333 |  |  |
| read_text_file | autoskill_base | 5 | 0.0000 | 1.0000 | 0.6000 |  |  |
| search_files | raw_mcp | 5 | 0.2000 | 0.6667 | 0.7334 |  |  |
| search_files | schema_only | 5 | 0.2000 | 0.6667 | 0.6000 |  |  |
| search_files | retrieved_docs | 5 | 0.2000 | 0.6667 | 0.6000 | 1.0000 | 1.25 |
| search_files | retrieved_candidates | 5 | 0.2000 | 0.6667 | 0.6000 | 1.0000 | 1.25 |
| search_files | retrieved_memory | 5 | 1.0000 | 1.0000 | 1.0000 |  |  |
| search_files | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | retrieved_docs | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | retrieved_memory | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |

## Hidden-Tool Routing By Gold Tool

| Gold Tool | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_docs | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_memory | 2 | 0.5000 | 0.5000 | 0.5000 | 1.00 |
| create_directory | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| list_directory | raw_mcp | 1 | 0.0000 | 0.0000 | 0.0000 |  |
| list_directory | schema_only | 1 | 0.0000 | 0.0000 | 0.0000 |  |
| list_directory | retrieved_docs | 1 | 0.0000 | 0.0000 | 0.0000 |  |
| list_directory | retrieved_candidates | 1 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| list_directory | retrieved_memory | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| list_directory | autoskill_base | 1 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| read_text_file | raw_mcp | 5 | 0.8000 | 0.4000 | 0.8000 | 1.00 |
| read_text_file | schema_only | 5 | 0.8000 | 0.0000 | 0.8000 | 1.00 |
| read_text_file | retrieved_docs | 5 | 0.8000 | 0.0000 | 0.8000 | 1.00 |
| read_text_file | retrieved_candidates | 5 | 0.8000 | 0.0000 | 1.0000 | 1.20 |
| read_text_file | retrieved_memory | 5 | 1.0000 | 0.0000 | 1.0000 | 1.00 |
| read_text_file | autoskill_base | 5 | 1.0000 | 0.0000 | 1.0000 | 1.00 |
| search_files | raw_mcp | 5 | 0.6000 | 0.2000 | 0.6000 | 1.00 |
| search_files | schema_only | 5 | 0.6000 | 0.2000 | 0.6000 | 1.00 |
| search_files | retrieved_docs | 5 | 0.6000 | 0.2000 | 0.8000 | 1.25 |
| search_files | retrieved_candidates | 5 | 1.0000 | 0.2000 | 1.0000 | 1.00 |
| search_files | retrieved_memory | 5 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| search_files | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | raw_mcp | 2 | 0.5000 | 0.5000 | 0.5000 | 1.00 |
| write_file | schema_only | 2 | 0.5000 | 0.5000 | 0.5000 | 1.00 |
| write_file | retrieved_docs | 2 | 0.0000 | 0.0000 | 0.0000 |  |
| write_file | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | retrieved_memory | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |

## Pairwise Comparisons

| Anchor | Baseline | Paired Tasks | Win | Tie | Loss | Exact Match Delta | 95% CI | Avg Argument Validity Delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| autoskill_base | raw_mcp | 15 | 4 | 8 | 3 | 0.0667 | [-0.2667, 0.4000] | 0.1778 |
| autoskill_base | schema_only | 15 | 4 | 11 | 0 | 0.2667 | [0.0667, 0.4667] | 0.1778 |
| autoskill_base | retrieved_docs | 15 | 4 | 11 | 0 | 0.2667 | [0.0667, 0.4667] | 0.1778 |
| autoskill_base | retrieved_candidates | 15 | 4 | 11 | 0 | 0.2667 | [0.0667, 0.4667] | 0.1444 |
| autoskill_base | retrieved_memory | 15 | 0 | 15 | 0 | 0.0000 | [0.0000, 0.0000] | 0.0333 |

## Error Taxonomy

### raw_mcp

- failures: 6
- missing_required_argument: 1 (0.1667)
- semantic_missing_required_argument: 5 (0.8333)

### schema_only

- failures: 9
- hallucinated_argument: 7 (0.7778)
- missing_required_argument: 1 (0.1111)
- semantic_missing_required_argument: 1 (0.1111)

### retrieved_docs

- failures: 9
- hallucinated_argument: 7 (0.7778)
- missing_required_argument: 1 (0.1111)
- semantic_missing_required_argument: 1 (0.1111)

### retrieved_candidates

- failures: 9
- hallucinated_argument: 7 (0.7778)
- missing_required_argument: 1 (0.1111)
- semantic_missing_required_argument: 1 (0.1111)

### retrieved_memory

- failures: 5
- hallucinated_argument: 5 (1.0000)

### autoskill_base

- failures: 5
- hallucinated_argument: 5 (1.0000)


## Method Wins

### autoskill_base vs raw_mcp

- anchor wins: 4
- recovered failure types: semantic_missing_required_argument=3, missing_required_argument=1
- recovered tags: search=4, semantic=3, literal=1, glob=1
- `fs_search_py` on `search_files` [missing_required_argument]
- `fs_search_python_semantic` on `search_files` [semantic_missing_required_argument]
- `fs_search_markdown_semantic` on `search_files` [semantic_missing_required_argument]

### autoskill_base vs schema_only

- anchor wins: 4
- recovered failure types: hallucinated_argument=2, missing_required_argument=1, semantic_missing_required_argument=1
- recovered tags: search=4, semantic=3, literal=1, glob=1
- `fs_search_py` on `search_files` [missing_required_argument]
- `fs_search_python_semantic` on `search_files` [hallucinated_argument]
- `fs_search_markdown_semantic` on `search_files` [hallucinated_argument]

### autoskill_base vs retrieved_docs

- anchor wins: 4
- recovered failure types: hallucinated_argument=2, missing_required_argument=1, semantic_missing_required_argument=1
- recovered tags: search=4, semantic=3, literal=1, glob=1
- `fs_search_py` on `search_files` [missing_required_argument]
- `fs_search_python_semantic` on `search_files` [hallucinated_argument]
- `fs_search_markdown_semantic` on `search_files` [hallucinated_argument]

### autoskill_base vs retrieved_candidates

- anchor wins: 4
- recovered failure types: hallucinated_argument=2, missing_required_argument=1, semantic_missing_required_argument=1
- recovered tags: search=4, semantic=3, literal=1, glob=1
- `fs_search_py` on `search_files` [missing_required_argument]
- `fs_search_python_semantic` on `search_files` [hallucinated_argument]
- `fs_search_markdown_semantic` on `search_files` [hallucinated_argument]

### autoskill_base vs retrieved_memory

- anchor wins: 0


## Packaging By Tool

| Tool | Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | --- | ---: | ---: | ---: | ---: |
| add_observations | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| add_observations | schema_only | 0.0000 | 1.00 | 1.00 | 0.00 |
| add_observations | retrieved_docs | 0.0000 | 1.00 | 1.00 | 0.00 |
| add_observations | retrieved_candidates | 0.0000 | 1.00 | 1.00 | 0.00 |
| add_observations | retrieved_memory | 0.0000 | 1.00 | 1.00 | 0.00 |
| add_observations | autoskill_base | 0.0000 | 2.00 | 1.00 | 0.00 |
| convert_time | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| convert_time | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| convert_time | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| convert_time | retrieved_candidates | 1.0000 | 2.00 | 3.00 | 0.00 |
| convert_time | retrieved_memory | 1.0000 | 1.00 | 3.00 | 0.00 |
| convert_time | autoskill_base | 1.0000 | 2.00 | 3.00 | 0.00 |
| create_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| create_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| create_directory | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| create_directory | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| create_directory | retrieved_memory | 1.0000 | 2.00 | 1.00 | 0.00 |
| create_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| create_entities | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| create_entities | schema_only | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_entities | retrieved_docs | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_entities | retrieved_candidates | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_entities | retrieved_memory | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_entities | autoskill_base | 0.0000 | 2.00 | 1.00 | 0.00 |
| create_relations | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| create_relations | schema_only | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_relations | retrieved_docs | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_relations | retrieved_candidates | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_relations | retrieved_memory | 0.0000 | 1.00 | 1.00 | 0.00 |
| create_relations | autoskill_base | 0.0000 | 2.00 | 1.00 | 0.00 |
| delete_entities | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| delete_entities | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| delete_entities | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| delete_entities | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| delete_entities | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| delete_entities | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| delete_observations | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| delete_observations | schema_only | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_observations | retrieved_docs | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_observations | retrieved_candidates | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_observations | retrieved_memory | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_observations | autoskill_base | 0.0000 | 2.00 | 1.00 | 0.00 |
| delete_relations | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| delete_relations | schema_only | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_relations | retrieved_docs | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_relations | retrieved_candidates | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_relations | retrieved_memory | 0.0000 | 1.00 | 1.00 | 0.00 |
| delete_relations | autoskill_base | 0.0000 | 2.00 | 1.00 | 0.00 |
| directory_tree | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| directory_tree | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| directory_tree | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| directory_tree | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| directory_tree | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| directory_tree | autoskill_base | 1.0000 | 2.00 | 2.00 | 3.00 |
| echo | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| echo | schema_only | 1.0000 | 2.00 | 1.00 | 0.00 |
| echo | retrieved_docs | 1.0000 | 2.00 | 1.00 | 0.00 |
| echo | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| echo | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| echo | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| edit_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| edit_file | schema_only | 0.0000 | 2.00 | 3.00 | 0.00 |
| edit_file | retrieved_docs | 0.0000 | 2.00 | 3.00 | 0.00 |
| edit_file | retrieved_candidates | 0.0000 | 2.00 | 3.00 | 0.00 |
| edit_file | retrieved_memory | 0.0000 | 1.00 | 3.00 | 0.00 |
| edit_file | autoskill_base | 0.0000 | 2.00 | 3.00 | 0.00 |
| fetch | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| fetch | schema_only | 1.0000 | 2.00 | 4.00 | 0.00 |
| fetch | retrieved_docs | 1.0000 | 2.00 | 4.00 | 0.00 |
| fetch | retrieved_candidates | 1.0000 | 2.00 | 4.00 | 0.00 |
| fetch | retrieved_memory | 1.0000 | 1.00 | 4.00 | 0.00 |
| fetch | autoskill_base | 1.0000 | 2.00 | 4.00 | 0.00 |
| get-annotated-message | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-annotated-message | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-annotated-message | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-annotated-message | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-annotated-message | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| get-annotated-message | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-env | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-env | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-env | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-env | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-env | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-env | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-resource-links | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-resource-links | schema_only | 1.0000 | 2.00 | 1.00 | 0.00 |
| get-resource-links | retrieved_docs | 1.0000 | 2.00 | 1.00 | 0.00 |
| get-resource-links | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| get-resource-links | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| get-resource-links | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| get-resource-reference | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-resource-reference | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-resource-reference | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-resource-reference | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-resource-reference | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| get-resource-reference | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-structured-content | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-structured-content | schema_only | 0.0000 | 0.00 | 0.00 | 0.00 |
| get-structured-content | retrieved_docs | 0.0000 | 0.00 | 0.00 | 0.00 |
| get-structured-content | retrieved_candidates | 0.0000 | 0.00 | 0.00 | 0.00 |
| get-structured-content | retrieved_memory | 0.0000 | 0.00 | 0.00 | 0.00 |
| get-structured-content | autoskill_base | 0.0000 | 0.00 | 0.00 | 0.00 |
| get-sum | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-sum | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-sum | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-sum | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-sum | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| get-sum | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| get-tiny-image | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-tiny-image | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-tiny-image | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-tiny-image | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-tiny-image | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| get-tiny-image | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| get_current_time | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get_current_time | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_current_time | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_current_time | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_current_time | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_current_time | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| get_file_info | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| get_file_info | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_file_info | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_file_info | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_file_info | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| get_file_info | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| git_add | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_add | schema_only | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_add | retrieved_docs | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_add | retrieved_candidates | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_add | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_add | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_branch | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_branch | schema_only | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_branch | retrieved_docs | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_branch | retrieved_candidates | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_branch | retrieved_memory | 1.0000 | 1.00 | 4.00 | 0.00 |
| git_branch | autoskill_base | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_checkout | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_checkout | schema_only | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_checkout | retrieved_docs | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_checkout | retrieved_candidates | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_checkout | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_checkout | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_commit | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_commit | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_commit | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_commit | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_commit | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_commit | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_create_branch | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_create_branch | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_create_branch | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_create_branch | retrieved_candidates | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_create_branch | retrieved_memory | 1.0000 | 1.00 | 3.00 | 0.00 |
| git_create_branch | autoskill_base | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_diff | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_diff | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_diff | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_diff | retrieved_candidates | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_diff | retrieved_memory | 1.0000 | 1.00 | 3.00 | 0.00 |
| git_diff | autoskill_base | 1.0000 | 2.00 | 3.00 | 0.00 |
| git_diff_staged | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_diff_staged | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_staged | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_staged | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_staged | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_diff_staged | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_unstaged | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_diff_unstaged | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_unstaged | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_unstaged | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_diff_unstaged | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_diff_unstaged | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_log | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_log | schema_only | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_log | retrieved_docs | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_log | retrieved_candidates | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_log | retrieved_memory | 1.0000 | 1.00 | 4.00 | 0.00 |
| git_log | autoskill_base | 1.0000 | 2.00 | 4.00 | 0.00 |
| git_reset | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_reset | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_reset | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_reset | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_reset | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_reset | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| git_show | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_show | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_show | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_show | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_show | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| git_show | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| git_status | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| git_status | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_status | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_status | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_status | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| git_status | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| gzip-file-as-resource | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| gzip-file-as-resource | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| gzip-file-as-resource | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| gzip-file-as-resource | retrieved_candidates | 1.0000 | 2.00 | 3.00 | 0.00 |
| gzip-file-as-resource | retrieved_memory | 1.0000 | 1.00 | 3.00 | 0.00 |
| gzip-file-as-resource | autoskill_base | 1.0000 | 2.00 | 3.00 | 0.00 |
| list_allowed_directories | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_allowed_directories | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_allowed_directories | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_allowed_directories | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_allowed_directories | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_allowed_directories | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| list_directory | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| list_directory | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| list_directory | retrieved_memory | 1.0000 | 2.00 | 1.00 | 0.00 |
| list_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| list_directory_with_sizes | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_directory_with_sizes | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| list_directory_with_sizes | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| list_directory_with_sizes | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| list_directory_with_sizes | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| list_directory_with_sizes | autoskill_base | 1.0000 | 2.00 | 2.00 | 2.00 |
| move_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| move_file | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| move_file | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| move_file | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| move_file | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| move_file | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| open_nodes | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| open_nodes | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| open_nodes | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| open_nodes | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| open_nodes | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| open_nodes | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| read_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_file | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_file | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_file | retrieved_candidates | 1.0000 | 4.00 | 3.00 | 0.00 |
| read_file | retrieved_memory | 1.0000 | 1.00 | 3.00 | 0.00 |
| read_file | autoskill_base | 1.0000 | 2.00 | 3.00 | 8.00 |
| read_graph | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_graph | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_graph | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_graph | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_graph | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_graph | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_media_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_media_file | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_media_file | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_media_file | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_media_file | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_media_file | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| read_multiple_files | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_multiple_files | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_multiple_files | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_multiple_files | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_multiple_files | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| read_multiple_files | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| read_text_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_text_file | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_text_file | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_text_file | retrieved_candidates | 0.0000 | 4.00 | 3.00 | 0.00 |
| read_text_file | retrieved_memory | 0.0000 | 3.00 | 3.00 | 0.00 |
| read_text_file | autoskill_base | 1.0000 | 2.00 | 3.00 | 8.00 |
| search_files | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| search_files | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| search_files | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| search_files | retrieved_candidates | 1.0000 | 3.00 | 3.00 | 0.00 |
| search_files | retrieved_memory | 1.0000 | 4.00 | 3.00 | 0.00 |
| search_files | autoskill_base | 1.0000 | 4.00 | 3.00 | 9.00 |
| search_nodes | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| search_nodes | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| search_nodes | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| search_nodes | retrieved_candidates | 1.0000 | 1.00 | 1.00 | 0.00 |
| search_nodes | retrieved_memory | 1.0000 | 1.00 | 1.00 | 0.00 |
| search_nodes | autoskill_base | 1.0000 | 2.00 | 1.00 | 0.00 |
| toggle-simulated-logging | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-simulated-logging | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-simulated-logging | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-simulated-logging | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-simulated-logging | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-simulated-logging | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| toggle-subscriber-updates | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | schema_only | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | retrieved_docs | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | retrieved_candidates | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | retrieved_memory | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-elicitation-request-async | autoskill_base | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-long-running-operation | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-long-running-operation | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-long-running-operation | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-long-running-operation | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-long-running-operation | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| trigger-long-running-operation | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-sampling-request | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| trigger-sampling-request | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request-async | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| trigger-sampling-request-async | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request-async | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request-async | retrieved_candidates | 1.0000 | 2.00 | 2.00 | 0.00 |
| trigger-sampling-request-async | retrieved_memory | 1.0000 | 1.00 | 2.00 | 0.00 |
| trigger-sampling-request-async | autoskill_base | 1.0000 | 2.00 | 2.00 | 0.00 |
| write_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| write_file | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
| write_file | retrieved_docs | 1.0000 | 2.00 | 2.00 | 0.00 |
| write_file | retrieved_candidates | 1.0000 | 3.00 | 2.00 | 0.00 |
| write_file | retrieved_memory | 1.0000 | 2.00 | 2.00 | 0.00 |
| write_file | autoskill_base | 1.0000 | 3.00 | 2.00 | 4.00 |

## Failure Highlights

### raw_mcp

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"path": "src/main.py"}`
- `fs_read_trailing_synonym` on `read_text_file`: Show the trailing 12 lines of reports/latest.log.
  expected `{"path": "reports/latest.log", "tail": 12}`
  predicted `{"path": "reports/latest.log"}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"path": "src", "pattern": "**/*.py"}`
  predicted `{"path": "src"}`

### schema_only

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"head": 1.0, "path": "src/main.py", "tail": 1.0}`
- `fs_read_trailing_synonym` on `read_text_file`: Show the trailing 12 lines of reports/latest.log.
  expected `{"path": "reports/latest.log", "tail": 12}`
  predicted `{"head": 1.0, "path": "reports/latest.log", "tail": 1.0}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": ["sample_excludePatterns_item_1"], "path": "src", "pattern": "sample_pattern_1"}`

### retrieved_docs

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"head": 1.0, "path": "src/main.py", "tail": 1.0}`
- `fs_read_trailing_synonym` on `read_text_file`: Show the trailing 12 lines of reports/latest.log.
  expected `{"path": "reports/latest.log", "tail": 12}`
  predicted `{"head": 1.0, "path": "reports/latest.log", "tail": 1.0}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": ["sample_excludePatterns_item_1"], "path": "src", "pattern": "sample_pattern_1"}`

### retrieved_candidates

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"head": 1.0, "path": "src/main.py", "tail": 12}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": ["sample_excludePatterns_item_1"], "path": "src", "pattern": "sample_pattern_1"}`
- `fs_search_markdown_semantic` on `search_files`: Find markdown files under docs.
  expected `{"path": "docs", "pattern": "**/*.md"}`
  predicted `{"excludePatterns": ["sample_excludePatterns_item_1"], "path": "docs", "pattern": "sample_pattern_1"}`

### retrieved_memory

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"head": 1.0, "path": "src/main.py", "tail": 12}`
- `fs_read_full` on `read_text_file`: Read config/settings.json.
  expected `{"path": "config/settings.json"}`
  predicted `{"head": 1.0, "path": "config/settings.json", "tail": 1.0}`
- `fs_read_head` on `read_text_file`: Read the first 20 lines of src/app.py.
  expected `{"head": 20, "path": "src/app.py"}`
  predicted `{"head": 20, "path": "src/app.py", "tail": 12}`

### autoskill_base

- `fs_read_full` on `read_text_file`: Read config/settings.json.
  expected `{"path": "config/settings.json"}`
  predicted `{"head": 1.0, "path": "config/settings.json", "tail": 1.0}`
- `fs_read_head` on `read_text_file`: Read the first 20 lines of src/app.py.
  expected `{"head": 20, "path": "src/app.py"}`
  predicted `{"head": 20, "path": "src/app.py", "tail": 1.0}`
- `fs_read_tail` on `read_text_file`: Show me the last 15 lines of logs/output.txt.
  expected `{"path": "logs/output.txt", "tail": 15}`
  predicted `{"head": 1.0, "path": "logs/output.txt", "tail": 15}`


## Headline

The main comparison to track is whether `autoskill_base` improves exact-match and argument-validity metrics over `raw_mcp`, and whether that gain shows up consistently on individual tools instead of only in the aggregate.
