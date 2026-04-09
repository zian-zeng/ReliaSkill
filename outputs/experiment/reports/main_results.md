# AutoSkill Experiment Report

- Tools source: `data\raw\public_mcp_filesystem_subset.json`
- Benchmark source: `data\eval\public_mcp_filesystem_benchmark.jsonl`

## Packaging Summary

| Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | ---: | ---: | ---: | ---: |
| raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| schema_only | 1.0000 | 1.60 | 2.00 | 0.00 |
| retrieved_docs | 1.0000 | 1.60 | 2.00 | 0.00 |
| retrieved_candidates | 1.0000 | 2.80 | 2.00 | 0.00 |
| retrieved_memory | 1.0000 | 2.60 | 2.00 | 0.00 |
| autoskill_base | 1.0000 | 3.40 | 2.00 | 4.20 |

## Benchmark Summary

| Condition | Exact Match | Argument Validity | Required Arg Recall | Retrieval Hit@K | Avg Target Rank | Hallucinated Args |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| raw_mcp | 0.6667 | 0.8667 | 0.9000 |  |  | 0 |
| schema_only | 0.6667 | 0.8667 | 0.9000 |  |  | 0 |
| retrieved_docs | 0.6667 | 0.8667 | 0.9000 | 1.0000 | 1.43 | 0 |
| retrieved_candidates | 0.6667 | 0.9000 | 0.9000 | 1.0000 | 1.43 | 2 |
| retrieved_memory | 0.8667 | 0.9667 | 1.0000 |  |  | 2 |
| autoskill_base | 1.0000 | 1.0000 | 1.0000 |  |  | 0 |

## Hidden-Tool Routing Summary

| Condition | Tool Accuracy | Joint Exact Match | Argument Validity | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw_mcp | 0.7333 | 0.5333 | 0.6444 | 0.8667 | 1.15 |
| schema_only | 0.7333 | 0.5333 | 0.6444 | 0.8667 | 1.15 |
| retrieved_docs | 0.7333 | 0.4667 | 0.6222 | 0.9333 | 1.43 |
| retrieved_candidates | 0.9333 | 0.6000 | 0.8333 | 1.0000 | 1.07 |
| retrieved_memory | 0.8667 | 0.7333 | 0.8333 | 1.0000 | 1.20 |
| autoskill_base | 0.9333 | 0.9333 | 0.9333 | 1.0000 | 1.07 |

## Benchmark By Split

| Split | Condition | Tasks | Exact Match | 95% CI | Argument Validity | Retrieval Hit@K | Avg Target Rank |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| dev | raw_mcp | 6 | 1.0000 | [1.0000, 1.0000] | 1.0000 |  |  |
| dev | schema_only | 6 | 1.0000 | [1.0000, 1.0000] | 1.0000 |  |  |
| dev | retrieved_docs | 6 | 1.0000 | [1.0000, 1.0000] | 1.0000 | 1.0000 | 1.67 |
| dev | retrieved_candidates | 6 | 0.8333 | [0.5000, 1.0000] | 1.0000 | 1.0000 | 1.67 |
| dev | retrieved_memory | 6 | 0.8333 | [0.5000, 1.0000] | 1.0000 |  |  |
| dev | autoskill_base | 6 | 1.0000 | [1.0000, 1.0000] | 1.0000 |  |  |
| test | raw_mcp | 9 | 0.4444 | [0.1111, 0.7778] | 0.7778 |  |  |
| test | schema_only | 9 | 0.4444 | [0.1111, 0.7778] | 0.7778 |  |  |
| test | retrieved_docs | 9 | 0.4444 | [0.1111, 0.7778] | 0.7778 | 1.0000 | 1.25 |
| test | retrieved_candidates | 9 | 0.5556 | [0.2222, 0.8889] | 0.8333 | 1.0000 | 1.25 |
| test | retrieved_memory | 9 | 0.8889 | [0.6667, 1.0000] | 0.9444 |  |  |
| test | autoskill_base | 9 | 1.0000 | [1.0000, 1.0000] | 1.0000 |  |  |

## Hidden-Tool Routing By Split

| Split | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| dev | raw_mcp | 6 | 0.8333 | 0.8333 | 1.0000 | 1.17 |
| dev | schema_only | 6 | 0.8333 | 0.8333 | 1.0000 | 1.17 |
| dev | retrieved_docs | 6 | 0.6667 | 0.6667 | 1.0000 | 1.67 |
| dev | retrieved_candidates | 6 | 0.8333 | 0.6667 | 1.0000 | 1.17 |
| dev | retrieved_memory | 6 | 0.6667 | 0.5000 | 1.0000 | 1.50 |
| dev | autoskill_base | 6 | 0.8333 | 0.8333 | 1.0000 | 1.17 |
| test | raw_mcp | 9 | 0.6667 | 0.3333 | 0.7778 | 1.14 |
| test | schema_only | 9 | 0.6667 | 0.3333 | 0.7778 | 1.14 |
| test | retrieved_docs | 9 | 0.7778 | 0.3333 | 0.8889 | 1.25 |
| test | retrieved_candidates | 9 | 1.0000 | 0.5556 | 1.0000 | 1.00 |
| test | retrieved_memory | 9 | 1.0000 | 0.8889 | 1.0000 | 1.00 |
| test | autoskill_base | 9 | 1.0000 | 1.0000 | 1.0000 | 1.00 |

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
| list_directory | retrieved_docs | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.00 |
| list_directory | retrieved_candidates | 1 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.00 |
| list_directory | retrieved_memory | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| list_directory | autoskill_base | 1 | 1.0000 | 1.0000 | 1.0000 |  |  |
| read_text_file | raw_mcp | 5 | 0.6000 | 0.8000 | 1.0000 |  |  |
| read_text_file | schema_only | 5 | 0.6000 | 0.8000 | 1.0000 |  |  |
| read_text_file | retrieved_docs | 5 | 0.6000 | 0.8000 | 1.0000 | 1.0000 | 1.00 |
| read_text_file | retrieved_candidates | 5 | 0.6000 | 0.9000 | 1.0000 | 1.0000 | 1.00 |
| read_text_file | retrieved_memory | 5 | 0.6000 | 0.9000 | 1.0000 |  |  |
| read_text_file | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 |  |  |
| search_files | raw_mcp | 5 | 0.4000 | 0.8000 | 0.7000 |  |  |
| search_files | schema_only | 5 | 0.4000 | 0.8000 | 0.7000 |  |  |
| search_files | retrieved_docs | 5 | 0.4000 | 0.8000 | 0.7000 | 1.0000 | 1.40 |
| search_files | retrieved_candidates | 5 | 0.4000 | 0.8000 | 0.7000 | 1.0000 | 1.40 |
| search_files | retrieved_memory | 5 | 1.0000 | 1.0000 | 1.0000 |  |  |
| search_files | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | retrieved_docs | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.00 |
| write_file | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.00 |
| write_file | retrieved_memory | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |
| write_file | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 |  |  |

## Hidden-Tool Routing By Gold Tool

| Gold Tool | Condition | Tasks | Tool Accuracy | Joint Exact Match | Gold Tool Hit@K | Avg Gold Tool Rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_docs | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| create_directory | retrieved_memory | 2 | 0.5000 | 0.5000 | 1.0000 | 2.00 |
| create_directory | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| list_directory | raw_mcp | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| list_directory | schema_only | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| list_directory | retrieved_docs | 1 | 0.0000 | 0.0000 | 1.0000 | 3.00 |
| list_directory | retrieved_candidates | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| list_directory | retrieved_memory | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| list_directory | autoskill_base | 1 | 0.0000 | 0.0000 | 1.0000 | 2.00 |
| read_text_file | raw_mcp | 5 | 1.0000 | 0.6000 | 1.0000 | 1.00 |
| read_text_file | schema_only | 5 | 1.0000 | 0.6000 | 1.0000 | 1.00 |
| read_text_file | retrieved_docs | 5 | 1.0000 | 0.6000 | 1.0000 | 1.00 |
| read_text_file | retrieved_candidates | 5 | 1.0000 | 0.6000 | 1.0000 | 1.00 |
| read_text_file | retrieved_memory | 5 | 1.0000 | 0.6000 | 1.0000 | 1.00 |
| read_text_file | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| search_files | raw_mcp | 5 | 0.6000 | 0.4000 | 0.8000 | 1.25 |
| search_files | schema_only | 5 | 0.6000 | 0.4000 | 0.8000 | 1.25 |
| search_files | retrieved_docs | 5 | 0.8000 | 0.4000 | 1.0000 | 1.40 |
| search_files | retrieved_candidates | 5 | 1.0000 | 0.4000 | 1.0000 | 1.00 |
| search_files | retrieved_memory | 5 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| search_files | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | raw_mcp | 2 | 0.5000 | 0.5000 | 0.5000 | 1.00 |
| write_file | schema_only | 2 | 0.5000 | 0.5000 | 0.5000 | 1.00 |
| write_file | retrieved_docs | 2 | 0.0000 | 0.0000 | 0.5000 | 3.00 |
| write_file | retrieved_candidates | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | retrieved_memory | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |
| write_file | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 | 1.00 |

## Pairwise Comparisons

| Anchor | Baseline | Paired Tasks | Win | Tie | Loss | Exact Match Delta | 95% CI | Avg Argument Validity Delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| autoskill_base | raw_mcp | 15 | 5 | 10 | 0 | 0.3333 | [0.1333, 0.6000] | 0.1333 |
| autoskill_base | schema_only | 15 | 5 | 10 | 0 | 0.3333 | [0.1333, 0.6000] | 0.1333 |
| autoskill_base | retrieved_docs | 15 | 5 | 10 | 0 | 0.3333 | [0.1333, 0.6000] | 0.1333 |
| autoskill_base | retrieved_candidates | 15 | 5 | 10 | 0 | 0.3333 | [0.0667, 0.6000] | 0.1000 |
| autoskill_base | retrieved_memory | 15 | 2 | 13 | 0 | 0.1333 | [0.0000, 0.3333] | 0.0333 |

## Error Taxonomy

### raw_mcp

- failures: 5
- semantic_mapping_failure: 2 (0.4000)
- semantic_missing_required_argument: 3 (0.6000)

### schema_only

- failures: 5
- semantic_mapping_failure: 2 (0.4000)
- semantic_missing_required_argument: 3 (0.6000)

### retrieved_docs

- failures: 5
- semantic_mapping_failure: 2 (0.4000)
- semantic_missing_required_argument: 3 (0.6000)

### retrieved_candidates

- failures: 5
- hallucinated_argument: 2 (0.4000)
- semantic_missing_required_argument: 3 (0.6000)

### retrieved_memory

- failures: 2
- hallucinated_argument: 2 (1.0000)

### autoskill_base

- failures: 0


## Method Wins

### autoskill_base vs raw_mcp

- anchor wins: 5
- recovered failure types: semantic_missing_required_argument=3, semantic_mapping_failure=2
- recovered tags: semantic=5, search=3, head=1, tail=1
- `fs_read_top_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_read_trailing_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_search_python_semantic` on `search_files` [semantic_missing_required_argument]

### autoskill_base vs schema_only

- anchor wins: 5
- recovered failure types: semantic_missing_required_argument=3, semantic_mapping_failure=2
- recovered tags: semantic=5, search=3, head=1, tail=1
- `fs_read_top_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_read_trailing_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_search_python_semantic` on `search_files` [semantic_missing_required_argument]

### autoskill_base vs retrieved_docs

- anchor wins: 5
- recovered failure types: semantic_missing_required_argument=3, semantic_mapping_failure=2
- recovered tags: semantic=5, search=3, head=1, tail=1
- `fs_read_top_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_read_trailing_synonym` on `read_text_file` [semantic_mapping_failure]
- `fs_search_python_semantic` on `search_files` [semantic_missing_required_argument]

### autoskill_base vs retrieved_candidates

- anchor wins: 5
- recovered failure types: semantic_missing_required_argument=3, hallucinated_argument=2
- recovered tags: semantic=4, search=3, head=2, literal=1
- `fs_read_head` on `read_text_file` [hallucinated_argument]
- `fs_read_top_synonym` on `read_text_file` [hallucinated_argument]
- `fs_search_python_semantic` on `search_files` [semantic_missing_required_argument]

### autoskill_base vs retrieved_memory

- anchor wins: 2
- recovered failure types: hallucinated_argument=2
- recovered tags: head=2, literal=1, semantic=1
- `fs_read_head` on `read_text_file` [hallucinated_argument]
- `fs_read_top_synonym` on `read_text_file` [hallucinated_argument]


## Packaging By Tool

| Tool | Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | --- | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| create_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| create_directory | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| create_directory | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| create_directory | retrieved_memory | 1.0000 | 2.00 | 1.00 | 0.00 |
| create_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| list_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| list_directory | retrieved_docs | 1.0000 | 1.00 | 1.00 | 0.00 |
| list_directory | retrieved_candidates | 1.0000 | 2.00 | 1.00 | 0.00 |
| list_directory | retrieved_memory | 1.0000 | 2.00 | 1.00 | 0.00 |
| list_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| read_text_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_text_file | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_text_file | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_text_file | retrieved_candidates | 1.0000 | 4.00 | 3.00 | 0.00 |
| read_text_file | retrieved_memory | 1.0000 | 3.00 | 3.00 | 0.00 |
| read_text_file | autoskill_base | 1.0000 | 4.00 | 3.00 | 8.00 |
| search_files | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| search_files | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| search_files | retrieved_docs | 1.0000 | 2.00 | 3.00 | 0.00 |
| search_files | retrieved_candidates | 1.0000 | 3.00 | 3.00 | 0.00 |
| search_files | retrieved_memory | 1.0000 | 4.00 | 3.00 | 0.00 |
| search_files | autoskill_base | 1.0000 | 4.00 | 3.00 | 9.00 |
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
  expected `{"excludePatterns": [], "path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": [], "path": "src"}`

### schema_only

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"path": "src/main.py"}`
- `fs_read_trailing_synonym` on `read_text_file`: Show the trailing 12 lines of reports/latest.log.
  expected `{"path": "reports/latest.log", "tail": 12}`
  predicted `{"path": "reports/latest.log"}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"excludePatterns": [], "path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": [], "path": "src", "pattern": "sample_pattern_1"}`

### retrieved_docs

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"path": "src/main.py"}`
- `fs_read_trailing_synonym` on `read_text_file`: Show the trailing 12 lines of reports/latest.log.
  expected `{"path": "reports/latest.log", "tail": 12}`
  predicted `{"path": "reports/latest.log"}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"excludePatterns": [], "path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": [], "path": "src", "pattern": "sample_pattern_1"}`

### retrieved_candidates

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"path": "src/main.py", "tail": 12}`
- `fs_search_python_semantic` on `search_files`: Look under src for python files.
  expected `{"excludePatterns": [], "path": "src", "pattern": "**/*.py"}`
  predicted `{"excludePatterns": [], "path": "src", "pattern": "sample_pattern_1"}`
- `fs_search_markdown_semantic` on `search_files`: Find markdown files under docs.
  expected `{"excludePatterns": [], "path": "docs", "pattern": "**/*.md"}`
  predicted `{"excludePatterns": [], "path": "docs", "pattern": "sample_pattern_1"}`

### retrieved_memory

- `fs_read_top_synonym` on `read_text_file`: Show the top 8 lines of src/main.py.
  expected `{"head": 8, "path": "src/main.py"}`
  predicted `{"path": "src/main.py", "tail": 12}`
- `fs_read_head` on `read_text_file`: Read the first 20 lines of src/app.py.
  expected `{"head": 20, "path": "src/app.py"}`
  predicted `{"head": 20, "path": "src/app.py", "tail": 12}`


## Headline

The main comparison to track is whether `autoskill_base` improves exact-match and argument-validity metrics over `raw_mcp`, and whether that gain shows up consistently on individual tools instead of only in the aggregate.
