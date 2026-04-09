# AutoSkill Experiment Report

- Tools source: `data\raw\public_mcp_filesystem_subset.json`
- Benchmark source: `data\eval\public_mcp_filesystem_benchmark.jsonl`

## Packaging Summary

| Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | ---: | ---: | ---: | ---: |
| raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| schema_only | 1.0000 | 1.60 | 2.00 | 0.00 |
| autoskill_base | 1.0000 | 3.40 | 2.00 | 4.20 |

## Benchmark Summary

| Condition | Exact Match | Argument Validity | Required Arg Recall | Hallucinated Args |
| --- | ---: | ---: | ---: | ---: |
| raw_mcp | 0.6667 | 0.8667 | 0.9000 | 0 |
| schema_only | 0.6667 | 0.8667 | 0.9000 | 0 |
| autoskill_base | 1.0000 | 1.0000 | 1.0000 | 0 |

## Benchmark By Tool

| Tool | Condition | Tasks | Exact Match | Argument Validity | Required Arg Recall |
| --- | --- | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 |
| create_directory | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 |
| create_directory | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 |
| list_directory | raw_mcp | 1 | 1.0000 | 1.0000 | 1.0000 |
| list_directory | schema_only | 1 | 1.0000 | 1.0000 | 1.0000 |
| list_directory | autoskill_base | 1 | 1.0000 | 1.0000 | 1.0000 |
| read_text_file | raw_mcp | 5 | 0.6000 | 0.8000 | 1.0000 |
| read_text_file | schema_only | 5 | 0.6000 | 0.8000 | 1.0000 |
| read_text_file | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 |
| search_files | raw_mcp | 5 | 0.4000 | 0.8000 | 0.7000 |
| search_files | schema_only | 5 | 0.4000 | 0.8000 | 0.7000 |
| search_files | autoskill_base | 5 | 1.0000 | 1.0000 | 1.0000 |
| write_file | raw_mcp | 2 | 1.0000 | 1.0000 | 1.0000 |
| write_file | schema_only | 2 | 1.0000 | 1.0000 | 1.0000 |
| write_file | autoskill_base | 2 | 1.0000 | 1.0000 | 1.0000 |

## Packaging By Tool

| Tool | Condition | Valid Rate | Avg Examples | Avg Template Fields | Avg Semantic Hints |
| --- | --- | ---: | ---: | ---: | ---: |
| create_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| create_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| create_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| list_directory | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| list_directory | schema_only | 1.0000 | 1.00 | 1.00 | 0.00 |
| list_directory | autoskill_base | 1.0000 | 3.00 | 1.00 | 0.00 |
| read_text_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| read_text_file | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| read_text_file | autoskill_base | 1.0000 | 4.00 | 3.00 | 8.00 |
| search_files | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| search_files | schema_only | 1.0000 | 2.00 | 3.00 | 0.00 |
| search_files | autoskill_base | 1.0000 | 4.00 | 3.00 | 9.00 |
| write_file | raw_mcp | 1.0000 | 0.00 | 0.00 | 0.00 |
| write_file | schema_only | 1.0000 | 2.00 | 2.00 | 0.00 |
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


## Headline

The main comparison to track is whether `autoskill_base` improves exact-match and argument-validity metrics over `raw_mcp`, and whether that gain shows up consistently on individual tools instead of only in the aggregate.
