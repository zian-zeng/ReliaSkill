from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ParameterSchema(BaseModel):
    """
    Represents the schema definition for a single parameter within a tool.
    This enforces strict type checking and captures essential constraints 
    required for the Schema-only baseline.
    """
    type: str = Field(..., description="Data type of the parameter (e.g., 'string', 'integer', 'boolean').")
    description: Optional[str] = Field(None, description="Natural language description of the parameter.")
    required: bool = Field(False, description="Flag indicating whether the parameter is mandatory.")
    default: Optional[Any] = Field(None, description="Default value for the parameter, if any.")
    enum: Optional[List[Any]] = Field(None, description="List of strictly allowed values (categorical choices).")

class ToolIR(BaseModel):
    """
    Tool Internal Representation (ToolIR).
    
    This class perfectly maps to the formal definition M = (schema, docs) introduced 
    in Section 3.2 of the AutoSkill paper. It acts as the deterministic, sanitized 
    bridge between chaotic raw MCP specifications and the downstream generators.
    """
    name: str = Field(
        ..., 
        description="The unique canonical identifier of the tool (e.g., 'get_weather')."
    )
    description: str = Field(
        ..., 
        description="The base natural language documentation provided by the raw MCP server."
    )
    parameters: Dict[str, ParameterSchema] = Field(
        default_factory=dict, 
        description="A dictionary mapping parameter names to their explicit structural schemas."
    )
    source: str = Field(
        default="unknown_mcp_server", 
        description="Provenance tracking string indicating where this MCP definition originated."
    )