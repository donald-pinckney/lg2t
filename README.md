# lg2t

[![PyPI version](https://badge.fury.io/py/lg2t.svg)](https://badge.fury.io/py/lg2t)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically migrate your [LangGraph](https://github.com/langchain-ai/langgraph) graphs to [Temporal](https://temporal.io/) workflows using Claude AI.

## Why Migrate?

LangGraph is excellent for prototyping AI agent workflows, but as your application scales, you may want:

- **Durable execution**: Temporal provides automatic retries, timeouts, and crash recovery
- **Better observability**: Built-in workflow history and debugging tools
- **Production reliability**: Battle-tested at massive scale by companies like Netflix, Uber, and Stripe
- **Natural Python code**: Write workflows as regular Python instead of graph definitions

This tool uses Claude AI to analyze your LangGraph and generate equivalent Temporal code while preserving your existing node function logic.

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
- A Claude API key (via `claude-agent-sdk`)
- Your existing LangGraph code

## Quick Start

```python
from langgraph.graph import StateGraph, END
from lg2t import Graph, migrate_using_claude

# Your existing LangGraph definition
class State(TypedDict):
    messages: list[str]

def process(state: State) -> State:
    state["messages"].append("Processed!")
    return state

def finalize(state: State) -> State:
    state["messages"].append("Done!")
    return state

# Build the graph
builder = StateGraph(State)
builder.add_node("process", process)
builder.add_node("finalize", finalize)
builder.set_entry_point("process")
builder.add_edge("process", "finalize")
builder.add_edge("finalize", END)

# Convert and migrate
graph = Graph.from_langgraph(builder)
migrate_using_claude(graph)
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
- Import and call your **existing node functions** (no logic duplication!)
- Provide typed input/output dataclasses
- Handle the state mapping between workflow and node functions

## API Reference

### `Graph.from_langgraph(builder)`

Convert a LangGraph `StateGraph` to the internal Graph representation.

```python
from lg2t import Graph

graph = Graph.from_langgraph(your_state_graph)
```

**Parameters:**
- `builder`: A LangGraph `StateGraph` instance (not compiled)

**Returns:** A `Graph` instance ready for migration

### `migrate_using_claude(graph, output_dir=None)`

Run the AI-powered migration process.

```python
from lg2t import migrate_using_claude

migrate_using_claude(graph)
# Or specify output directory:
migrate_using_claude(graph, output_dir="/path/to/output")
```

**Parameters:**
- `graph`: A `Graph` instance from `Graph.from_langgraph()`
- `output_dir`: Optional output directory (defaults to the calling script's directory)

## Supported LangGraph Features

| Feature | Supported |
|---------|-----------|
| Static edges | ✅ |
| Conditional edges (routing) | ✅ |
| Command-based edges | ✅ |
| Waiting edges (fan-in) | ✅ |
| State schemas | ✅ |
| Input/output schemas | ✅ |
| Subgraphs | 🚧 Coming soon |

## Example

See the [`examples/`](./examples/) directory for a complete working example.

```python
# examples/example_graph.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from lg2t import Graph, migrate_using_claude

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
g.add_edge("greet", "farewell")
g.add_edge("farewell", END)

graph = Graph.from_langgraph(g)
migrate_using_claude(graph)
```

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) - The source framework
- [Temporal](https://temporal.io/) - The target durable execution platform
- [Claude](https://www.anthropic.com/claude) - The AI powering the migration

