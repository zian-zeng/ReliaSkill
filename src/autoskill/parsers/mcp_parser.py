"""
MCP Parser Module for AutoSkill.

This module is responsible for the deterministic extraction and normalization 
of raw, heterogenous Model Context Protocol (MCP) definitions into the 
standardized Tool Internal Representation (ToolIR). It acts as the 
first crucial step in the ETL (Extract, Transform, Load) pipeline, ensuring 
downstream generative models receive strictly formatted, noise-free schemas.
"""

import logging
from typing import Any, Dict, List, Optional

from src.autoskill.ir.models import ParameterSchema, ToolIR

# Configure module-level logging for rigorous experimentation tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _extract_canonical_name(raw_data: Dict[str, Any]) -> str:
    """
    Extracts the canonical tool name using heuristic fallbacks.
    
    Real-world MCP definitions exhibit structural variance (e.g., using 'name' 
    vs proprietary keys like 'app:weeu'). This function normalizes these variations.
    
    Args:
        raw_data (Dict[str, Any]): The raw JSON dictionary of the MCP tool.
        
    Returns:
        str: The sanitized, canonical name of the tool.
    """
    # Heuristic 1: Standard 'name' field
    if "name" in raw_data and isinstance(raw_data["name"], str):
        return raw_data["name"].strip()
    
    # Heuristic 2: Proprietary or malformed keys (e.g., 'app:weeu')
    for key, value in raw_data.items():
        if isinstance(key, str) and "app" in key.lower() and isinstance(value, str):
            # Clean up potential malformed formatting like ': weather'
            return value.replace(":", "").strip()
            
    logger.warning("Canonical name not found. Falling back to 'unknown_tool'.")
    return "unknown_tool"


def _extract_description(raw_data: Dict[str, Any]) -> str:
    """
    Extracts the base functional description of the tool.
    
    Args:
        raw_data (Dict[str, Any]): The raw JSON dictionary of the MCP tool.
        
    Returns:
        str: The base description, defaulting to a placeholder if missing.
    """
    desc = raw_data.get("description") or raw_data.get("Description")
    if desc and isinstance(desc, str):
        return desc.strip()
    
    logger.warning("Tool description missing. This may negatively impact downstream generation.")
    return "No description provided in the raw MCP specification."


def _extract_parameters(raw_data: Dict[str, Any]) -> Dict[str, ParameterSchema]:
    """
    Parses the nested parameter schema and strictly aligns it with ParameterSchema.
    
    This function traverses the 'inputSchema' or 'properties' dictionary, 
    extracting data types, requirements, and constraints (e.g., enums).
    
    Args:
        raw_data (Dict[str, Any]): The raw JSON dictionary of the MCP tool.
        
    Returns:
        Dict[str, ParameterSchema]: A dictionary mapping parameter names to their 
                                    strongly-typed Pydantic schemas.
    """
    parsed_parameters: Dict[str, ParameterSchema] = {}
    
    # Locate the schema block (handling varying MCP specification versions)
    schema_block = raw_data.get("inputSchema") or raw_data.get("schema_info", {})
    if not isinstance(schema_block, dict):
        logger.error("Malformed schema block detected. Returning empty parameters.")
        return parsed_parameters

    properties: Dict[str, Any] = schema_block.get("properties", {})
    required_fields: List[str] = schema_block.get("required", [])

    for param_name, param_details in properties.items():
        if not isinstance(param_details, dict):
            continue
            
        # Map raw fields to the strict ParameterSchema constraints
        parsed_parameters[param_name] = ParameterSchema(
            type=param_details.get("type", "string"),
            description=param_details.get("description"),
            required=(param_name in required_fields),
            default=param_details.get("default"),
            enum=param_details.get("enum")
        )
        
    return parsed_parameters


def parse_mcp_to_ir(raw_data: Dict[str, Any], source_pointer: str = "unknown_source") -> ToolIR:
    """
    The main orchestrator function to convert raw MCP definitions into ToolIR.
    
    Args:
        raw_data (Dict[str, Any]): The unformatted, raw MCP tool definition.
        source_pointer (str): An identifier tracking the origin of this data 
                              (e.g., GitHub URL or dataset split).
                              
    Returns:
        ToolIR: The rigorously validated and structured internal representation.
    """
    logger.info(f"Initiating MCP parsing pipeline for source: {source_pointer}")
    
    name = _extract_canonical_name(raw_data)
    description = _extract_description(raw_data)
    parameters = _extract_parameters(raw_data)
    
    # Construct and return the strictly validated Pydantic model
    tool_ir = ToolIR(
        name=name,
        description=description,
        parameters=parameters,
        source=source_pointer
    )
    
    logger.info(f"Successfully parsed ToolIR: '{tool_ir.name}' with {len(tool_ir.parameters)} parameters.")
    return tool_ir