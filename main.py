"""
AutoSkill Batch Processing Pipeline.

This script automates the generation of 'Schema-only Formatted Baselines' 
by processing a directory of raw MCP tool definitions. It follows the 
deterministic flow: Load File -> Parse to ToolIR -> Render Baseline -> Save Output.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from src.autoskill.parsers.mcp_parser import parse_mcp_to_ir
from src.autoskill.ir.models import ToolIR

# Academic-grade logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================================
# Configuration: Define paths relative to the project root
# =====================================================================
INPUT_DIR = Path("data/raw")
OUTPUT_DIR = Path("outputs/baselines/schema_only")

# Ensure the output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================================
# Baseline Renderer
# =====================================================================
def render_schema_only_baseline(tool_ir: ToolIR) -> Dict[str, Any]:
    """
    Renders a sanitized, deterministic JSON representation of the tool.
    
    This function explicitly excludes generative guidance (examples, summaries)
    to serve as a strict structural control group for academic evaluation.
    """
    return {
        "tool_name": tool_ir.name,
        "purpose": tool_ir.description,
        "arguments": {
            name: param.model_dump(exclude_none=True) 
            for name, param in tool_ir.parameters.items()
        }
    }

# =====================================================================
# Main Orchestrator
# =====================================================================
def run_batch_pipeline():
    """
    Scans the input directory and processes all JSON files in sequence.
    """
    logger.info(f"Initiating batch pipeline. Scanning: {INPUT_DIR.absolute()}")
    
    # Support both .json and .jsonl files if necessary
    target_files = list(INPUT_DIR.glob("*.json"))
    
    if not target_files:
        logger.warning(f"No JSON files found in {INPUT_DIR}. Please check your data ingestion.")
        return

    logger.info(f"Found {len(target_files)} raw tool definitions. Starting processing...")

    success_count = 0
    for file_path in target_files:
        try:
            # 1. Load raw data from disk
            with open(file_path, "r", encoding="utf-8") as f:
                raw_mcp_data = json.load(f)
            
            # 2. Convert to internal representation (ToolIR)
            # We use the filename as the source pointer for traceability
            tool_ir = parse_mcp_to_ir(raw_mcp_data, source_pointer=file_path.name)
            
            # 3. Generate the Schema-only Baseline
            baseline_dict = render_schema_only_baseline(tool_ir)
            
            # 4. Save the result to the output directory
            output_path = OUTPUT_DIR / f"{tool_ir.name}_baseline.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(baseline_dict, f, indent=4, ensure_ascii=False)
            
            logger.info(f"Successfully processed: {tool_ir.name} -> {output_path.name}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {str(e)}")
            continue

    logger.info("="*50)
    logger.info(f"PIPELINE COMPLETE: {success_count}/{len(target_files)} tools processed.")
    logger.info(f"Outputs saved to: {OUTPUT_DIR.absolute()}")
    logger.info("="*50)

if __name__ == "__main__":
    run_batch_pipeline()