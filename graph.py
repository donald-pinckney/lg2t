from collections import defaultdict
from dataclasses import dataclass, field
import json
from typing import Optional, Self

from langgraph.graph import StateGraph
from langgraph.constants import START as LG_START, END as LG_END


START = "__special_start_node__"
END = "__special_end_node__"


def _map_node_name(name: str) -> str:
    """Map langgraph node names to our internal names."""
    if name == LG_START:
        return START
    elif name == LG_END:
        return END
    return name


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
    defined_at: Optional[str] = None

@dataclass
class Graph:
    """A control flow graph."""
    nodes: dict[str, Node] = field(default_factory=lambda: dict())
    edges: defaultdict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    
    def add_node(self, node: Node) -> None:
        self.nodes[node.name] = node

    def add_edge(self, from_node: str, edge: Edge) -> None:
        self.edges[from_node].append(edge)

    def to_json(self) -> str:
        """Serialize the graph to JSON."""
        def edge_to_dict(edge: Edge) -> dict:
            if isinstance(edge, StaticEdge):
                return {"type": "static", "target": edge.target}
            elif isinstance(edge, RoutingEdge):
                return {
                    "type": "routing",
                    "routing_fn": edge.routing_fn,
                    "possible_targets": edge.possible_targets,
                }
            elif isinstance(edge, CommandEdge):
                return {"type": "command", "possible_targets": edge.possible_targets}
            else:
                raise ValueError(f"Unknown edge type: {type(edge)}")

        return json.dumps({
            "nodes": [{
                "name": node.name,
                "defined_at": node.defined_at,
            } for node in self.nodes.values()],
            "edges": {
                source: [edge_to_dict(e) for e in edges]
                for source, edges in self.edges.items()
            },
        }, indent=2)

    @staticmethod
    def from_langgraph(lg: StateGraph) -> "Graph":
        """Convert a LangGraph StateGraph to our Graph representation.
        
        Args:
            lg: A langgraph StateGraph instance (not compiled)
            
        Returns:
            A Graph instance representing the same control flow
        """
        graph = Graph()
        
        # Add START and END pseudo-nodes
        graph.add_node(Node(name=START, defined_at=None))
        graph.add_node(Node(name=END, defined_at=None))
        
        # Add all nodes from the langgraph
        for node_name in lg.nodes:
            spec = lg.nodes[node_name]
            # spec.runnable.
            node_code = spec.runnable.func.__code__
            def_place = f"{node_code.co_filename}:{node_code.co_firstlineno}"
            graph.add_node(Node(name=node_name, defined_at=def_place))
        
        # Add static edges from lg.edges (set of (start, end) tuples)
        for start, end in lg.edges:
            mapped_start = _map_node_name(start)
            mapped_end = _map_node_name(end)
            graph.add_edge(mapped_start, StaticEdge(target=mapped_end))
        
        # Add waiting edges (fan-in edges from multiple sources)
        # These are stored as ((start1, start2, ...), end)
        for starts, end in lg.waiting_edges:
            mapped_end = _map_node_name(end)
            for start in starts:
                mapped_start = _map_node_name(start)
                graph.add_edge(mapped_start, StaticEdge(target=mapped_end))
        
        # Add conditional edges from lg.branches
        # branches is defaultdict[str, dict[str, BranchSpec]]
        # maps source_node -> {branch_name -> BranchSpec}
        for source, branch_dict in lg.branches.items():
            mapped_source = _map_node_name(source)
            for branch_name, branch_spec in branch_dict.items():
                # branch_spec.path is a Runnable - get its name
                routing_fn_name = getattr(branch_spec.path, 'name', None) or branch_name
                
                graph.add_edge(
                    mapped_source,
                    RoutingEdge(routing_fn=routing_fn_name, possible_targets=None)
                )
        
        # Add command edges from nodes that can return Command objects
        # These are stored in StateNodeSpec.ends
        for node_name, node_spec in lg.nodes.items():
            if node_spec.ends:
                # ends can be tuple[str, ...] or dict[str, str]
                if isinstance(node_spec.ends, dict):
                    targets = [_map_node_name(t) for t in node_spec.ends.keys()]
                else:
                    targets = [_map_node_name(t) for t in node_spec.ends]
                
                if targets:  # Only add if there are actual targets
                    graph.add_edge(node_name, CommandEdge(possible_targets=targets))
        
        return graph