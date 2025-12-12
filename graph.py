from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Self

from langgraph.graph import StateGraph


START = "__special_start_node__"
END = "__special_end_node__"


@dataclass
class Edge:
    pass

@dataclass
class StaticEdge(Edge):
    target: str

@dataclass
class RoutingEdge(Edge):
    routing_fn: str
    possible_targets: Optional[list[str]]

@dataclass
class CommandEdge(Edge):
    possible_targets: Optional[list[str]]

@dataclass
class Node:
    """A basic block: a straight-line sequence of instructions."""
    name: str


@dataclass
class Graph:
    """A control flow graph."""
    nodes: dict[str, Node] = field(default_factory=lambda: dict())
    edges: defaultdict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    
    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, from_node: str, edge: Edge) -> None:
        self.edges[from_node].append(edge)


    @staticmethod
    def from_langgraph(g: StateGraph) -> Self:
        