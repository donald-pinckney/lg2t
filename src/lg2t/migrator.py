"""Migration engine using Claude AI to convert LangGraph to Temporal."""

import asyncio
import inspect
import os
import sys
import threading
import time
from typing import Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk.types import SystemPromptPreset, ToolsPreset
from langgraph.graph import StateGraph
from pydantic import BaseModel

from lg2t.graph import Graph


class _Spinner:
    """A simple terminal spinner for visual feedback."""

    def __init__(self, text: str = "working...", delay: float = 0.1) -> None:
        self.text = text
        self.delay = delay
        self._stop = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the spinner animation."""

        def run() -> None:
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while not self._stop.is_set():
                sys.stdout.write("\r" + spinner[i % len(spinner)] + " " + self.text)
                sys.stdout.flush()
                i += 1
                time.sleep(self.delay)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._stop.set()
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r✓ " + self.text + " " * 10 + "\n")


class MigrationOutput(BaseModel):
    """The output from the Claude migration process.

    Attributes:
        workflow_file: The generated Temporal workflow Python code.
        activities_file: The generated Temporal activities Python code.
    """

    workflow_file: str
    activities_file: str


async def _migrate_using_claude_async(graph: Graph, migration_dir: str) -> Optional[str]:
    """Async implementation of the migration process.

    Args:
        graph: The Graph representation to migrate.
        migration_dir: Directory where generated files will be saved.

    Returns:
        The session ID for continuing the conversation, or None.
    """
    graph_prompt = graph.to_prompt()

    options = ClaudeAgentOptions(
        tools=ToolsPreset(type="preset", preset="claude_code"),
        system_prompt=SystemPromptPreset(type="preset", preset="claude_code"),
        model="opus",
        output_format={
            "type": "json_schema",
            "schema": MigrationOutput.model_json_schema(),
        },
        allowed_tools=["WebSearch"],
    )

    spinner_task = "Analyzing graph"
    spinner = _Spinner(spinner_task)
    spinner.start()

    session_id: Optional[str] = None

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
5. When creating a Temporal Activity for each node function, you should:
    5a. Write a wrapper function, which calls the currently defined node function and returns the result. For example:
```python
@dataclass
class FooInput:
    # ... things that are needed to call node_foo ...

@dataclass
class FooOutput:
    # ... things that node_foo needs to send to the workflow state ...

import node_foo from ... appropriate module ...

@workflow.defn
def node_foo_activity(input: FooInput) -> FooOutput:
    # NOTE: You MUST call the existing node_foo function here!
    new_state_map = node_foo({{ ... assemble dictionary of state that node_foo expects from the input ... }})
    return FooOutput(... assemble typed output of the outputs node_foo needs to make to the workflow state ...)
```
    
    5b. When calling the activity function within the workflow code, you will need to pass appropriate inputs from workflow state to the activity function,
    and take outputs from the activity function and update workflow state accordingly.

    5c. CRUCIALLY, your node activity functions MUST call the existing node function! This is because we are aiming to do a step-by-step migration, and this makes it easier to verify correctness.
    Do NOT, under any circumstances, re-do or duplicate the logic of the existing node function!

You will write the code for two separate Python files: one for the workflow code and one for all the activities' code. 
You will do so by returning a structured output with the fields: "workflow_file" and "activities_file", each of which is a string containing the code for the respective file.
On your behalf, I will save those files in the {migration_dir} directory, so keep that in mind for imports when writing the code.

The full description of the LangGraph graph is as follows:
{graph_prompt}

Please perform your analysis and create the workflow and activity code. Additionally, perform research using online documentation as needed to help you understand the Temporal Python SDK and how to use it.
""",
        options=options,
    ):
        if hasattr(message, "subtype") and message.subtype == "init":
            session_id = message.data.get("session_id")

        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    if spinner_task == "Analyzing graph":
                        spinner.stop()
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        spinner_task = "Generating Temporal code"
                        spinner = _Spinner(spinner_task)
                        spinner.start()
        elif (
            isinstance(message, ResultMessage)
            and message.total_cost_usd
            and message.total_cost_usd > 0
        ):
            pass

        if hasattr(message, "structured_output"):
            output = MigrationOutput.model_validate(message.structured_output)
            spinner.stop()
            _apply_migration(output, migration_dir)

    print()
    return session_id


def _apply_migration(migration: MigrationOutput, migration_dir: str) -> None:
    """Write the generated migration files to disk.

    Args:
        migration: The migration output containing file contents.
        migration_dir: Directory where files will be saved.
    """
    spinner = _Spinner("Applying migration")
    spinner.start()
    with open(os.path.join(migration_dir, "workflow.py"), "w") as f:
        f.write(migration.workflow_file)
    with open(os.path.join(migration_dir, "activities.py"), "w") as f:
        f.write(migration.activities_file)
    spinner.stop()


def _migrate_using_claude(graph: Graph, migration_dir: str) -> None:
    workflow_file = os.path.join(migration_dir, "workflow.py")
    activities_file = os.path.join(migration_dir, "activities.py")

    already_exists = os.path.exists(workflow_file) or os.path.exists(activities_file)

    if already_exists:
        response = input(
            f"workflow.py or activities.py already exist in {migration_dir}. "
            "Continue (will overwrite)? (y/N) "
        )
        if response.lower() != "y":
            print("Aborting migration.")
            return

        if os.path.exists(workflow_file):
            os.remove(workflow_file)
        if os.path.exists(activities_file):
            os.remove(activities_file)

    session_id = asyncio.run(_migrate_using_claude_async(graph, migration_dir))

    print(
        f"Migration completed! Files saved to {migration_dir}/workflow.py and {migration_dir}/activities.py."
    )
    print("Would you like to continue the conversion with Claude? (Y/n) ")
    response = input()
    if response.lower() == "n":
        return
    else:
        if session_id:
            os.execvp("claude", ["claude", "--resume", session_id])


def migrate_to_temporal(g: StateGraph, output_dir: Optional[str] = None):
    """Migrate a LangGraph graph to Temporal using Claude.

    This function takes a LangGraph StateGraph and uses Claude to generate equivalent Temporal workflow
    and activity code.

    Args:
        graph: The Graph to migrate.
        output_dir: Optional directory for output files. If not specified,
            uses the directory of the calling script.

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from lg2t import migrate
        >>>
        >>> # Create your LangGraph
        >>> graph = StateGraph(MyState)
        >>> graph.add_node("process", process_fn)
        >>> # ... add more nodes and edges ...
        >>>
        >>> # Migrate the graph to Temporal
        >>> migrate(graph)
    """

    if output_dir is None:
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back  # type: ignore[union-attr]
            migration_dir = os.path.dirname(os.path.abspath(caller_frame.f_code.co_filename))  # type: ignore[union-attr]
        finally:
            del frame
    else:
        migration_dir = output_dir

    graph = Graph.from_langgraph(g)
    _migrate_using_claude(graph, migration_dir)
