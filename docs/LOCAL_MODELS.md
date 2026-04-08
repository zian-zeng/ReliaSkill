# Local Model Setup

## What `local_hf` means

`local_hf` runs the generator and predictor directly through local Hugging Face model loading. It does not require an HTTP server.

The current code lazily imports `transformers` and `torch`, so the rest of the repo still works even if those packages are not installed.

## Minimum requirements

- Python environment with:
  - `transformers`
  - `torch`
- A chat-capable instruction model available locally or downloadable through Hugging Face
- Enough RAM / VRAM for the selected model

## Example install

```powershell
pip install transformers torch accelerate
```

Or install from the repo helper file:

```powershell
pip install -r requirements-local.txt
```

If you want faster inference or quantization, you may also want packages such as `bitsandbytes`, depending on your hardware.

Common practical variants:

- full precision on CPU: simplest, but slow
- half precision on CUDA: good default if your GPU supports it
- quantized loading with extra libraries: useful for tighter VRAM budgets, but model-specific

## Example config

Use [configs/experiment.local_hf.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.sample.json) as a starting point.

Recommended ready-made presets:

- [experiment.local_hf.qwen25_3b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_3b.sample.json)
- [experiment.local_hf.qwen25_7b.sample.json](/c:/Users/zianz/OneDrive/Documents/GitHub/AutoSkill/configs/experiment.local_hf.qwen25_7b.sample.json)

Example:

```json
{
  "tools_path": "data/raw/public_mcp_filesystem_subset.json",
  "tasks_path": "data/eval/public_mcp_filesystem_benchmark.jsonl",
  "output_root": "outputs/experiment_local_hf",
  "generator": {
    "type": "local_hf",
    "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
    "device": "auto",
    "device_map": "auto",
    "torch_dtype": "float16",
    "max_new_tokens": 768,
    "trust_remote_code": false,
    "attn_implementation": null,
    "load_in_4bit": false,
    "load_in_8bit": false
  },
  "predictor": {
    "type": "local_hf",
    "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
    "device": "auto",
    "device_map": "auto",
    "torch_dtype": "float16",
    "max_new_tokens": 512,
    "trust_remote_code": false,
    "attn_implementation": null,
    "load_in_4bit": false,
    "load_in_8bit": false
  }
}
```

## Run command

```powershell
python scripts\run_experiment.py --config configs\experiment.local_hf.sample.json
```

## Notes

- If you are starting from scratch, try the Qwen 3B preset first. It is usually a much easier first local run than 7B.
- Move to the Qwen 7B preset when the 3B setup is stable and you have enough VRAM or are comfortable with quantized loading.
- Smaller models are easier to bring up first.
- If a local model returns extra commentary around JSON, the project now tries to recover the JSON object automatically.
- If a local model call fails, the current code falls back to the heuristic backend instead of crashing the whole experiment.
- `device` and `device_map` are separate:
  - `device` is mainly useful for simple CPU or CUDA placement hints
  - `device_map` is the better choice for multi-device or automatic placement
- `trust_remote_code` may be needed for some model families.
- `attn_implementation` can be useful for models that support alternatives such as `flash_attention_2`.
- `load_in_4bit` or `load_in_8bit` can reduce memory usage, but typically require extra packages and compatible hardware.
- Do not enable both `load_in_4bit` and `load_in_8bit` at the same time.
- `generation_kwargs` lets you pass through extra `model.generate(...)` options without editing code.
