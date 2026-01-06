"""Tests for the Graph class."""

import pytest

from lg2t import (
    END,
    START,
    CommandEdge,
    Edge,
    Graph,
    Node,
    RoutingEdge,
    StaticEdge,
)


class TestNode:
    """Tests for the Node dataclass."""

    def test_create_node_minimal(self) -> None:
        """Test creating a node with just a name."""
        node = Node(name="test_node")
        assert node.name == "test_node"
        assert node.defined_at is None
        assert node.definition is None

    def test_create_node_full(self) -> None:
        """Test creating a node with all fields."""
        node = Node(
            name="test_node",
            defined_at="file.py:10",
            definition="def test(): pass",
        )
        assert node.name == "test_node"
        assert node.defined_at == "file.py:10"
        assert node.definition == "def test(): pass"


class TestEdge:
    """Tests for Edge classes."""

    def test_static_edge(self) -> None:
        """Test creating a static edge."""
        edge = StaticEdge(target="next_node")
        assert edge.target == "next_node"
        assert isinstance(edge, Edge)

    def test_routing_edge(self) -> None:
        """Test creating a routing edge."""
        edge = RoutingEdge(
            routing_fn="my_router",
            possible_targets=["a", "b", "c"],
        )
        assert edge.routing_fn == "my_router"
        assert edge.possible_targets == ["a", "b", "c"]
        assert isinstance(edge, Edge)

    def test_command_edge(self) -> None:
        """Test creating a command edge."""
        edge = CommandEdge(possible_targets=["x", "y"])
        assert edge.possible_targets == ["x", "y"]
        assert isinstance(edge, Edge)


class TestGraph:
    """Tests for the Graph class."""

    def test_create_empty_graph(self) -> None:
        """Test creating an empty graph."""
        graph = Graph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self) -> None:
        """Test adding a node to the graph."""
        graph = Graph()
        node = Node(name="test")
        graph.add_node(node)
        assert "test" in graph.nodes
        assert graph.nodes["test"] == node

    def test_add_edge(self) -> None:
        """Test adding an edge to the graph."""
        graph = Graph()
        edge = StaticEdge(target="b")
        graph.add_edge("a", edge)
        assert "a" in graph.edges
        assert len(graph.edges["a"]) == 1
        assert graph.edges["a"][0] == edge

    def test_add_multiple_edges_from_same_node(self) -> None:
        """Test adding multiple edges from the same source node."""
        graph = Graph()
        edge1 = StaticEdge(target="b")
        edge2 = StaticEdge(target="c")
        graph.add_edge("a", edge1)
        graph.add_edge("a", edge2)
        assert len(graph.edges["a"]) == 2

    def test_to_prompt_basic(self) -> None:
        """Test serializing graph to prompt format."""
        graph = Graph()
        graph.add_node(Node(name="test"))
        graph.add_edge("test", StaticEdge(target=END))
        
        prompt = graph.to_prompt()
        assert "test" in prompt
        assert "static" in prompt
        assert "<graph_json>" in prompt

    def test_constants(self) -> None:
        """Test START and END constants."""
        assert START == "__special_start_node__"
        assert END == "__special_end_node__"

