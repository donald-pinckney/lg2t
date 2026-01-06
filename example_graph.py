import json
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from graph import Graph
from migrator import migrate_using_claude

class State(TypedDict):
    messages: List[str]


def greet(state: State):
    state["messages"].append("Hello!")
    return state

def farewell(state: State):
    state["messages"].append("Goodbye!")
    return state


g = StateGraph(State)

g.add_node("greet", greet)
g.add_node("farewell", farewell)
g.set_entry_point("greet")

# When greet finishes, go to farewell
g.add_edge("greet", "farewell")

# When farewell finishes, end the graph
g.add_edge("farewell", END)

app = g.compile()
graph = Graph.from_langgraph(g)
migrate_using_claude(graph)


