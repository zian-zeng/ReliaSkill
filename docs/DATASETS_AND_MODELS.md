# Datasets And Models

## Current datasets on disk

### Default experiment dataset

- Tools: [public_mcp_filesystem_subset.json](data/raw/public_mcp_filesystem_subset.json)
- Tasks: [public_mcp_filesystem_benchmark.jsonl](data/eval/public_mcp_filesystem_benchmark.jsonl)
- Status: fully wired into the default runners

### Sample / regression fixtures

- [sample_tools.json](data/raw/sample_tools.json)
- [sample_mcp_export.json](data/raw/sample_mcp_export.json)
- [sample_bfcl_style.json](data/eval/sample_bfcl_style.json)
- [sample_bfcl_style.jsonl](data/eval/sample_bfcl_style.jsonl)
- [sample_bfcl_raw_possible_answer.jsonl](data/eval/sample_bfcl_raw_possible_answer.jsonl)
- Status: used for testing and format coverage

### Downloaded external corpora

- BFCL data root: [data/external/bfcl](data/external/bfcl)
- MCP servers repo: [data/external/modelcontextprotocol-servers](data/external/modelcontextprotocol-servers)

Observed BFCL slices present:

- `data/external/bfcl/data/api/`
- `data/external/bfcl/data/apibench/`
- `data/external/bfcl/data/apizoo/`

Observed MCP server source trees present:

- `src/filesystem`
- `src/fetch`
- `src/git`
- `src/memory`
- `src/time`
- `src/sequentialthinking`
- `src/everything`

## Integration status

### What is already wired

- The default experiment uses the curated MCP filesystem subset and its benchmark.
- The repo supports BFCL-style JSON and JSONL fixtures that already match the current evaluator.
- The repo supports external MCP tool JSON imports through [import_mcp_tools.py](scripts/import_mcp_tools.py).

### What is present but not yet the default

- The downloaded BFCL corpus is on disk, but it is not yet the default benchmark because the external BFCL files are code-generation / API-call style data, not the same schema-faithful MCP argument format as the current evaluator.
- The downloaded `modelcontextprotocol/servers` repo is on disk, but it is not yet auto-harvested into the default tool corpus. The current default tool file is still the curated filesystem subset.

### External experiment artifacts now wired

- Harvested MCP corpus: [harvested_mcp_reference_servers.json](data/raw/harvested_mcp_reference_servers.json)
- BFCL Hugging Face pseudo-tool corpus: [bfcl_huggingface_tools.json](data/raw/bfcl_huggingface_tools.json)
- BFCL Hugging Face train routing tasks: [bfcl_huggingface_train_routing.jsonl](data/eval/bfcl_huggingface_train_routing.jsonl)
- BFCL Hugging Face eval routing tasks: [bfcl_huggingface_eval_routing.jsonl](data/eval/bfcl_huggingface_eval_routing.jsonl)

### BFCL v3 Benchmarks

- BFCL v3 tools: `data/raw/bfcl_v3_tools.json`
- BFCL v3 benchmark: `data/eval/bfcl_v3_benchmark.jsonl`
- Subsets: `data/eval/bfcl_v3_benchmark_subset100.jsonl`, `...subset50.jsonl`, `...subset30.jsonl`

### Unified Routing Benchmark

- Unified routing tasks: [unified_routing_benchmark.jsonl](data/eval/unified_routing_benchmark.jsonl)

## Current model presets in code

### Local Hugging Face

- [experiment.local_hf.qwen25_3b.sample.json](configs/experiment.local_hf.qwen25_3b.sample.json)
- [experiment.local_hf.qwen25_7b.sample.json](configs/experiment.local_hf.qwen25_7b.sample.json)
- [experiment.local_hf.qwen25_14b_4bit.sample.json](configs/experiment.local_hf.qwen25_14b_4bit.sample.json)
- [experiment.local_hf.qwen25_32b_4bit.sample.json](configs/experiment.local_hf.qwen25_32b_4bit.sample.json)

### OpenAI-compatible endpoint

- [experiment.openai_compatible.sample.json](configs/experiment.openai_compatible.sample.json)
- [experiment.openai_compatible.qwen25_14b.sample.json](configs/experiment.openai_compatible.qwen25_14b.sample.json)
- [experiment.openai_compatible.qwen25_32b.sample.json](configs/experiment.openai_compatible.qwen25_32b.sample.json)

### External experiment configs

- [experiment.harvested_mcp.heuristic.sample.json](configs/experiment.harvested_mcp.heuristic.sample.json)
- [experiment.harvested_mcp.qwen25_14b_4bit.sample.json](configs/experiment.harvested_mcp.qwen25_14b_4bit.sample.json)
- [experiment.bfcl_huggingface_routing.heuristic.sample.json](configs/experiment.bfcl_huggingface_routing.heuristic.sample.json)
- [experiment.bfcl_huggingface_routing.qwen25_32b_endpoint.sample.json](configs/experiment.bfcl_huggingface_routing.qwen25_32b_endpoint.sample.json)

## Recommended cluster path

If you move to a GPU cluster, the cleanest options are:

- direct `local_hf` with 14B or 32B plus `load_in_4bit`
- `openai_compatible` with a served model such as vLLM, using the endpoint presets

In both cases, no Python code changes should be needed. Switching should be config-only.
