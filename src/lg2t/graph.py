"""Graph representation for LangGraph to Temporal migration."""

from collections import defaultdict
from dataclasses import dataclass, field
import inspect
import json
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

from langgraph.constants import START as LG_START, END as LG_END


START = "__special_start_node__"
"""Special identifier for the start node in the graph."""

END = "__special_end_node__"
"""Special identifier for the end node in the graph."""


def _map_node_name(name: str) -> str:
    """Map langgraph node names to our internal names.
    
    Args:
        name: The LangGraph node name.
        
    Returns:
        The mapped internal node name.
    """
    if name == LG_START:
        return START
    elif name == LG_END:
        return END
    return name


@dataclass
class Edge:
    """Base class for graph edges."""
    pass


@dataclass
class StaticEdge(Edge):
    """A static edge that always transitions to the same target node.
    
    Attributes:
        target: The name of the target node.
    """
    target: str


@dataclass
class RoutingEdge(Edge):
    """A conditional edge that uses a routing function to determine the target.
    
    Attributes:
        routing_fn: The name of the routing function.
        possible_targets: Optional list of possible target nodes.
    """
    routing_fn: str
    possible_targets: Optional[list[str]]


@dataclass
class CommandEdge(Edge):
    """An edge triggered by a Command object returned from a node.
    
    Attributes:
        possible_targets: Optional list of possible target nodes.
    """
    possible_targets: Optional[list[str]]


@dataclass
class Node:
    """A node in the graph representing a computation step.
    
    Attributes:
        name: The node's identifier.
        defined_at: Optional source location where the node function is defined.
        definition: Optional full definition of the node function.
    """
    name: str
    defined_at: Optional[str] = None
    definition: Optional[str] = None


@dataclass
class Graph:
    """A control flow graph representation.
    
    This class represents a LangGraph as a directed graph that can be
    serialized to a format suitable for AI-assisted migration to Temporal.
    
    Attributes:
        state_schema_description: Description of the state schema.
        input_schema_description: Description of the input schema.
        output_schema_description: Description of the output schema.
        nodes: Dictionary mapping node names to Node objects.
        edges: Dictionary mapping source node names to lists of Edge objects.
    """
    state_schema_description: Optional[str] = None
    input_schema_description: Optional[str] = None
    output_schema_description: Optional[str] = None

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: defaultdict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.
        
        Args:
            node: The node to add.
        """
        self.nodes[node.name] = node

    def add_edge(self, from_node: str, edge: Edge) -> None:
        """Add an edge from a node.
        
        Args:
            from_node: The source node name.
            edge: The edge to add.
        """
        self.edges[from_node].append(edge)

    def to_prompt(self) -> str:
        """Serialize the graph to a format suitable for AI prompts.
        
        Returns:
            A string representation of the graph with JSON structure
            and source code definitions.
        """
        def edge_to_dict(edge: Edge) -> dict[str, Any]:
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

        graph_json = json.dumps({
            "nodes": [{
                "name": node.name,
                **({"defined_at": node.defined_at} if node.defined_at is not None else {})
            } for node in self.nodes.values()],
            "edges": {
                source: [edge_to_dict(e) for e in edges]
                for source, edges in self.edges.items()
            },
        }, indent=2)

        node_definitions = "\n\n".join([
            f"Function for node \"{node.name}\" {node.definition}" 
            for node in self.nodes.values() if node.definition
        ])

        return f"""<graph_json>
{graph_json}
</graph_json>

<state_schema_description>
{self.state_schema_description}
</state_schema_description>

<input_schema_description>
{self.input_schema_description}
</input_schema_description>

<output_schema_description>
{self.output_schema_description}
</output_schema_description>

<node_definitions>
{node_definitions}
</node_definitions>"""

    @staticmethod
    def get_type_definition_description(t: type) -> str:
        """Get a description of a type definition including source code.
        
        Args:
            t: The type to describe.
            
        Returns:
            A string with file location and source code.
        """
        def_code = inspect.getsource(t)
        file = inspect.getsourcefile(t)
        lines = inspect.getsourcelines(t)
        return f"Defined at {file}:{lines[1]}:\n```python\n{def_code}```"

    @staticmethod
    def get_function_definition_description(f: Callable[..., Any]) -> str:
        """Get a description of a function definition including source code.
        
        Args:
            f: The function to describe.
            
        Returns:
            A string with file location and source code.
        """
        def_code = inspect.getsource(f)
        file = inspect.getsourcefile(f)
        lines = inspect.getsourcelines(f)
        return f"defined at {file}:{lines[1]}:\n```python\n{def_code}```"

    @staticmethod
    def from_langgraph(lg: "StateGraph") -> "Graph":
        """Convert a LangGraph StateGraph to our Graph representation.
        
        Args:
            lg: A langgraph StateGraph instance (not compiled).
            
        Returns:
            A Graph instance representing the same control flow.
            
        Example:
            >>> from langgraph.graph import StateGraph
            >>> from lg2t import Graph
            >>> 
            >>> # Create your LangGraph
            >>> builder = StateGraph(MyState)
            >>> # ... add nodes and edges ...
            >>> 
            >>> # Convert to our Graph format
            >>> graph = Graph.from_langgraph(builder)
        """
        graph = Graph()

        graph.state_schema_description = Graph.get_type_definition_description(lg.state_schema)
        graph.input_schema_description = Graph.get_type_definition_description(lg.input_schema)
        graph.output_schema_description = Graph.get_type_definition_description(lg.output_schema)
        
        # Add START and END pseudo-nodes
        graph.add_node(Node(name=START, defined_at=None))
        graph.add_node(Node(name=END, defined_at=None))
        
        # Add all nodes from the langgraph
        for node_name in lg.nodes:
            spec = lg.nodes[node_name]
            node_code = spec.runnable.func.__code__
            def_place = f"{node_code.co_filename}:{node_code.co_firstlineno}"
            definition = Graph.get_function_definition_description(spec.runnable.func)
            graph.add_node(Node(name=node_name, defined_at=def_place, definition=definition))
        
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

