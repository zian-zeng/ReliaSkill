# MCPToolBench++ Conversion Notes

This note records the optional larger-benchmark path used to convert MCPToolBench++ records into ReliaSkill-style positive cases and adjacent negative controls.

The recommended larger benchmark source is **MCPToolBench++**:

- Dataset: https://huggingface.co/datasets/MCPToolBench/MCPToolBenchPP
- Benchmark overview: https://mcpbr.org/mcptoolbench
- GitHub: https://github.com/MCPToolBench/MCPToolBenchPP

Why this is the best immediate fit:

- It provides natural-language queries, MCP tool schemas, and ground-truth tool calls.
- It covers file system, browser, search, map, pay, finance, and other MCP categories.
- It can be converted into ReliaSkill positive cases and adjacent negative controls without running live MCP servers.
- It directly stresses tool discovery, tool selection, invocation arguments, and over-triggering.

MCP-Atlas is also relevant, but it is heavier: it targets realistic multi-step workflows over real MCP servers and is better suited as a later full-agent execution benchmark rather than the first larger negative-control fixture.

## Download

If network access is available:

```powershell
python scripts\download_mcptoolbenchpp.py --out data\external\mcptoolbenchpp
```

If downloading manually, place the Hugging Face dataset snapshot in:

```text
data/external/mcptoolbenchpp/
```

The repository should contain JSON/JSONL files under that folder, usually beneath `data/`.

## Convert

Convert the full dataset:

```powershell
python scripts\convert_mcptoolbenchpp.py --input data\external\mcptoolbenchpp
```

For a low-compute paper slice, start with file/search/browser categories:

```powershell
python scripts\convert_mcptoolbenchpp.py --input data\external\mcptoolbenchpp --category file_system --category search --category browser --limit 300
```

The converter writes:

- `data/raw/mcptoolbenchpp_tools.json`
- `data/eval/mcptoolbenchpp_reliability.jsonl`

Positive cases preserve the expected tool and arguments. Negative controls are generated from adjacent tools that appeared in the same MCPToolBench++ task, so the same user request must not trigger the wrong tool.

## Run

After conversion:

```powershell
python scripts\run_reliability_pipeline.py --tools data\raw\mcptoolbenchpp_tools.json --behavior data\eval\mcptoolbenchpp_reliability.jsonl --out outputs\reliability_mcptoolbenchpp
```

For small local-model comparison, update `configs/model_comparison.low_compute.sample.json` to use:

```json
"tools_path": "data/raw/mcptoolbenchpp_tools.json",
"behavior_path": "data/eval/mcptoolbenchpp_reliability.jsonl"
```
