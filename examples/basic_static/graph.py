"""Example LangGraph to Temporal migration.

This example demonstrates how to migrate a simple LangGraph workflow
to Temporal using the lg2t package.
"""

from typing import List, TypedDict

from langgraph.graph import END, StateGraph

from lg2t import migrate_to_temporal


class State(TypedDict):
    """The state passed through the graph."""

    messages: List[str]


def greet(state: State) -> State:
    """Add a greeting message to state."""
    state["messages"].append("Hello!")
    return state


def farewell(state: State) -> State:
    """Add a farewell message to state."""
    state["messages"].append("Goodbye!")
    return state


# Build the LangGraph
g = StateGraph(State)

g.add_node("greet", greet)
g.add_node("farewell", farewell)
g.set_entry_point("greet")

# When greet finishes, go to farewell
g.add_edge("greet", "farewell")

# When farewell finishes, end the graph
g.add_edge("farewell", END)

# Migrate the graph to Temporal
if __name__ == "__main__":
    migrate_to_temporal(g)
