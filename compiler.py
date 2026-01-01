import asyncio
from claude_agent_sdk.types import SystemPromptPreset, ToolsPreset
from graph import Graph

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

import json


async def documentation_writer_example():
    """Example using a documentation writer agent."""
    print("=== Documentation Writer Agent Example ===")




async def migrate_using_claude_async(graph: Graph) -> str:
    graph_json = graph.to_json()

    print(graph_json)
    # return ""

    options = (
        ClaudeAgentOptions(
            tools=ToolsPreset(type="preset", preset="claude_code"),
            system_prompt=SystemPromptPreset(type="preset", preset="claude_code"),
            description="Writes comprehensive documentation",
            model="opus",
        ),
    )

    async for message in query(
        prompt=f"""
Your task is to help me with migrating my LangGraph code to Temporal.

As a refresher, LangGraph is a directed-graph framework. 
Structure: each node is a function which returns an updated state. 
An edge from node A to node B means that after A executes, B will execute. 
Edges can be either static or dynamically determined by an edge function.
LangGraph maintains a global state (essentially a big JSON map) during execution, 
which is passed into each node function, and maps returned from node functions are merged into the map.

On the other hand, Temporal is a durable execution framework.
Instead of specifying a graph, you write a Temporal Workflow, which is
standard Python code rather than a graph. Crucially, all significant computation (things that are non-deterministic, fallible, etc.)
are defined in separate Temporal Activities, and are executed in the workflow code via `await workflow.execute_activity(<the activity>, ...)`.
The Temporal runtime does not manage a large state object for you, like LangGraph. Instead, workflows use local and class level variable to store state and update them as natural Python code instead.

Key steps for migrating:
1. Identify the schema of the LangGraph graph object, and consider how to map it into natural variables in Python code. Consider that some aspects of state may no longer be needed at all as they may become implicit in the control flow of the workflow.
2. Identify all the node functions in the LangGraph graph. Each of these will become a Temporal Activity.
3. Understand the structure of the LangGraph graph, and plan out how to translate it into a Temporal Workflow. The control flow of the workflow code should reflect the control flow of the LangGraph graph.
4. Conditional edges in the LangGraph graph may also need to be translated into activities, depending on if they perform significant computation, are non-deterministic, or are fallible. If they simply check state, then that logic may just be in the workflow code instead.

You will create two new Python files: workflow.py and activities.py. The workflow.py file will contain the Temporal Workflow code, and the activities.py file will contain the Temporal Activity code.

The LangGraph graph object is as follows:
<graph_json>
{graph_json}
</graph_json>

Please perform your analysis and create workflow.py and activities.py files. Additionally, perform research using online documentation as needed to help you understand the Temporal Python SDK and how to use it.
""",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
        elif (
            isinstance(message, ResultMessage)
            and message.total_cost_usd
            and message.total_cost_usd > 0
        ):
            print(f"\nCost: ${message.total_cost_usd:.4f}")
    print()

def migrate_using_claude(graph: Graph) -> str:
    return asyncio.run(migrate_using_claude_async(graph))