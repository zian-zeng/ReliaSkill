"""Download BFCL simple + multiple data from HuggingFace."""
import json
import os
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ID = "gorilla-llm/Berkeley-Function-Calling-Leaderboard"
OUT_DIR = Path("data/bfcl")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Files we need:
# - Questions (with function definitions): BFCL_v3_simple.json, BFCL_v3_multiple.json
# - Answers: BFCL_v3_simple_possible_answer.json, BFCL_v3_multiple_possible_answer.json
FILES = [
    "BFCL_v3_simple.json",
    "BFCL_v3_multiple.json",
    "BFCL_v3_exec_simple.json",
    "BFCL_v3_exec_multiple.json",
]

# Also try to get possible answers
ANSWER_FILES = [
    "possible_answer/BFCL_v3_simple_possible_answer.json",
    "possible_answer/BFCL_v3_multiple_possible_answer.json",
    "possible_answer/BFCL_v3_exec_simple_possible_answer.json",
    "possible_answer/BFCL_v3_exec_multiple_possible_answer.json",
]

print("=" * 60)
print("Downloading BFCL data from HuggingFace...")
print("=" * 60)

# First, list available files to find the right ones
from huggingface_hub import list_repo_files

print("\nListing repository files containing 'simple' or 'multiple'...")
all_files = list(list_repo_files(REPO_ID, repo_type="dataset"))
relevant = [f for f in all_files if "simple" in f.lower() or "multiple" in f.lower()]
for f in sorted(relevant):
    print(f"  {f}")

print(f"\nTotal relevant files found: {len(relevant)}")
print()

# Download question files
for filename in FILES + ANSWER_FILES:
    if filename in all_files:
        print(f"Downloading: {filename}")
        try:
            local_path = hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                repo_type="dataset",
                local_dir=str(OUT_DIR),
            )
            print(f"  -> Saved to: {local_path}")
            # Quick peek at the data
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                print(f"  -> {len(data)} records")
                if data:
                    print(f"  -> Keys: {list(data[0].keys())[:8]}")
        except Exception as e:
            print(f"  -> Error: {e}")
    else:
        print(f"Skipping (not found): {filename}")

print("\n" + "=" * 60)
print("Download complete! Files saved to:", OUT_DIR.resolve())
print("=" * 60)
