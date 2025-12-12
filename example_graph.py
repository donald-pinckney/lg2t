from typing import TypedDict, List
from langgraph.graph import StateGraph, END

class State(TypedDict):
    messages: List[str]


def greet(state: State):
    state["messages"].append("Hello!")
    return state

def farewell(state: State):
    state["messages"].append("Goodbye!")
    return state

workflow = StateGraph(State)

workflow.add_node("greet", greet)
workflow.add_node("farewell", farewell)
workflow.set_entry_point("greet")

# When greet finishes, go to farewell
workflow.add_edge("greet", "farewell")

# When farewell finishes, end the graph
workflow.add_edge("farewell", END)

print(workflow)

app = workflow.compile()

print(app)


result = app.invoke({"messages": []})
print(result)
