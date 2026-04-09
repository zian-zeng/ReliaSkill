# Datasets And Models

## Current datasets on disk

### Default experiment dataset

- Tools: [public_mcp_filesystem_subset.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/raw/public_mcp_filesystem_subset.json)
- Tasks: [public_mcp_filesystem_benchmark.jsonl](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/eval/public_mcp_filesystem_benchmark.jsonl)
- Status: fully wired into the default runners

### Sample / regression fixtures

- [sample_tools.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/raw/sample_tools.json)
- [sample_mcp_export.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/raw/sample_mcp_export.json)
- [sample_bfcl_style.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/eval/sample_bfcl_style.json)
- [sample_bfcl_style.jsonl](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/eval/sample_bfcl_style.jsonl)
- [sample_bfcl_raw_possible_answer.jsonl](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/eval/sample_bfcl_raw_possible_answer.jsonl)
- Status: used for testing and format coverage

### Downloaded external corpora

- BFCL data root: [data/external/bfcl](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/external/bfcl)
- MCP servers repo: [data/external/modelcontextprotocol-servers](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/data/external/modelcontextprotocol-servers)

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
- The repo supports external MCP tool JSON imports through [import_mcp_tools.py](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/scripts/import_mcp_tools.py).

### What is present but not yet the default

- The downloaded BFCL corpus is on disk, but it is not yet the default benchmark because the external BFCL files are code-generation / API-call style data, not the same schema-faithful MCP argument format as the current evaluator.
- The downloaded `modelcontextprotocol/servers` repo is on disk, but it is not yet auto-harvested into the default tool corpus. The current default tool file is still the curated filesystem subset.

## Current model presets in code

### Local Hugging Face

- [experiment.local_hf.qwen25_3b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_3b.sample.json)
- [experiment.local_hf.qwen25_7b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_7b.sample.json)
- [experiment.local_hf.qwen25_14b_4bit.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_14b_4bit.sample.json)
- [experiment.local_hf.qwen25_32b_4bit.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_32b_4bit.sample.json)

### OpenAI-compatible endpoint

- [experiment.openai_compatible.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.openai_compatible.sample.json)
- [experiment.openai_compatible.qwen25_14b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.openai_compatible.qwen25_14b.sample.json)
- [experiment.openai_compatible.qwen25_32b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.openai_compatible.qwen25_32b.sample.json)

## Recommended cluster path

If you move to a GPU cluster, the cleanest options are:

- direct `local_hf` with 14B or 32B plus `load_in_4bit`
- `openai_compatible` with a served model such as vLLM, using the endpoint presets

In both cases, no Python code changes should be needed. Switching should be config-only.
