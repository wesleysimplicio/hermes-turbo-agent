"""Response contracts for output-token-efficient agent replies (issue #101)."""

from agent.contracts.concise_response import (
    ConciseContractError,
    Diagnostic,
    TerseAnswer,
    ToolCall,
    enforce_budget,
)

__all__ = [
    "ConciseContractError",
    "Diagnostic",
    "TerseAnswer",
    "ToolCall",
    "enforce_budget",
]
