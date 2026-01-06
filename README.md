# lg2t

Automatically migrate your [LangGraph](https://github.com/langchain-ai/langgraph) graphs to [Temporal](https://temporal.io/) workflows using Claude.

## Why Migrate?

LangGraph is excellent for prototyping AI agent workflows, but as your application scales, you may want:

- **Durable execution**: Temporal provides automatic retries, timeouts, and crash recovery
- **Better observability**: Built-in workflow history and debugging tools
- **Production reliability**: Battle-tested at massive scale by companies like Netflix, Uber, and Stripe
- **Natural Python code**: Write workflows as regular Python instead of graph definitions

This tool uses Claude to analyze your LangGraph and generate equivalent Temporal code while preserving your existing node function logic.

## Installation

```bash
pip install lg2t
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add lg2t
```

### Requirements

- Python 3.11+
- A local installation of Claude Code
- Your existing LangGraph code

## Quick Start

```python
from langgraph.graph import StateGraph, END
from lg2t import migrate_to_temporal

# Your existing LangGraph definition

class State(TypedDict):
    messages: list[str]

def process(state: State) -> State:
    state["messages"].append("Processed!")
    return state

def finalize(state: State) -> State:
    state["messages"].append("Done!")
    return state

# Typical LangGraph wiring
graph = StateGraph(State)
graph.add_node("process", process)
graph.add_node("finalize", finalize)
graph.set_entry_point("process")
graph.add_edge("process", "finalize")
graph.add_edge("finalize", END)

migrate_to_temporal(graph) # <- Just add this line, and run!
```

This will:

1. Analyze your LangGraph structure and node functions
2. Generate a Temporal workflow (`workflow.py`) that mirrors your graph's control flow
3. Generate Temporal activities (`activities.py`) that wrap your existing node functions
4. Offer to continue the conversation with Claude for refinements

## What Gets Generated

### Workflow File (`workflow.py`)

A Temporal workflow class that:
- Mirrors your graph's control flow using standard Python constructs
- Calls activities instead of node functions
- Handles state through natural Python variables

### Activities File (`activities.py`)

Temporal activities that:
- Import and call your **existing node functions**. This enables gradual migration.
- Provide typed input/output dataclasses
- Handle the state mapping between workflow and node functions

## API Reference

### `migrate_to_temporal(graph, output_dir=None)`

Run the migration process. Requires Claude Code to be setup locally.

```python
from lg2t import migrate_to_temporal

migrate_to_temporal(graph)
# Or specify output directory:
migrate_to_temporal(graph, output_dir="/path/to/output")
```

**Parameters:**
- `graph`: A `Graph` instance from `Graph.from_langgraph()`
- `output_dir`: Optional output directory (defaults to the calling script's directory)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/donald-pinckney/lg2t.git
cd lg2t

# Install with dev dependencies
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy src/
```

### Linting

```bash
ruff check src/
ruff format src/
```
