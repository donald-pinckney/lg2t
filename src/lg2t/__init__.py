"""LangGraph to Temporal migration tool.

This package provides tools to automatically migrate LangGraph graphs
to Temporal workflows using Claude AI.
"""

from lg2t.graph import (
    Graph,
    Node,
    Edge,
    StaticEdge,
    RoutingEdge,
    CommandEdge,
    START,
    END,
)
from lg2t.migrator import migrate_to_temporal

__version__ = "0.1.0"

__all__ = [
    # Core types
    "Graph",
    "Node",
    "Edge",
    "StaticEdge",
    "RoutingEdge",
    "CommandEdge",
    # Constants
    "START",
    "END",
    # Main function
    "migrate_to_temporal",
    # Version
    "__version__",
]
