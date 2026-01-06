import asyncio
from claude_agent_sdk.types import SystemPromptPreset, ToolsPreset
from graph import Graph
from pydantic import BaseModel
import inspect
import os

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

import sys
import time
import threading

class Spinner:
    def __init__(self, text="working...", delay=0.1):
        self.text = text
        self.delay = delay
        self._stop = threading.Event()

    def start(self):
        def run():
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while not self._stop.is_set():
                sys.stdout.write("\r" + spinner[i % len(spinner)] + " " + self.text)
                sys.stdout.flush()
                i += 1
                time.sleep(self.delay)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()
        self.thread.join()
        sys.stdout.write("\r✓ " + self.text + " " * 10 + "\n")


class MigrationOutput(BaseModel):
    workflow_file: str
    activities_file: str


async def migrate_using_claude_async(graph: Graph, migration_dir: str):
    graph_prompt = graph.to_prompt()

    options = ClaudeAgentOptions(
        tools=ToolsPreset(type="preset", preset="claude_code"),
        system_prompt=SystemPromptPreset(type="preset", preset="claude_code"),
        model="opus",
        output_format={
            "type": "json_schema",
            "schema": MigrationOutput.model_json_schema(),
        }
    )

    spinner_task = "Analyzing graph"
    spinner = Spinner(spinner_task)
    spinner.start()  

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
    new_state_map = node_foo({{ ... assemble dictionary of state that node_foo expects from the input ... }})
    return FooOutput(... assemble typed output of the outputs node_foo needs to make to the workflow state ...)
```
    
    5b. When calling the activity function within the workflow code, you will need to pass appropriate inputs from workflow state to the activity function,
    and take outputs from the activity function and update workflow state accordingly.

You will write the code for two separate Python files: one for the workflow code and one for all the activities' code. 
You will do so by returning a structured output with the fields: "workflow_file" and "activities_file", each of which is a string containing the code for the respective file.
On your behalf, I will save those files in the {migration_dir} directory, so keep that in mind for imports when writing the code.

The full description of the LangGraph graph is as follows:
{graph_prompt}

Please perform your analysis and create the workflow and activity code. Additionally, perform research using online documentation as needed to help you understand the Temporal Python SDK and how to use it.
""",
        options=options,
    ):
        if hasattr(message, 'subtype') and message.subtype == 'init':
            session_id = message.data.get('session_id')
    
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    if spinner_task == "Analyzing graph":
                        spinner.stop()
                        sys.stdout.write("\r" + " " * 80 + "\r")
                        spinner_task = "Generating Temporal code"
                        spinner = Spinner(spinner_task)
                        spinner.start()
        elif (
            isinstance(message, ResultMessage)
            and message.total_cost_usd
            and message.total_cost_usd > 0
        ):
            pass
            # print(f"\nCost: ${message.total_cost_usd:.4f}")

        if hasattr(message, 'structured_output'):
            # Validate and get fully typed result
            output = MigrationOutput.model_validate(message.structured_output)
            spinner.stop()
            apply_migration(output, migration_dir)
    print()
    return session_id

def apply_migration(migration: MigrationOutput, migration_dir: str):
    spinner = Spinner("applying migration")
    spinner.start()
    with open(os.path.join(migration_dir, "workflow.py"), "w") as f:
        f.write(migration.workflow_file)
    with open(os.path.join(migration_dir, "activities.py"), "w") as f:
        f.write(migration.activities_file)
    spinner.stop()

def migrate_using_claude(graph: Graph):
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back
        migration_dir = os.path.abspath(caller_frame.f_code.co_filename)
    finally:
        # Avoid reference cycles
        del frame

    # Make sure workflow and activities files don't exist yet.
    workflow_file = os.path.join(migration_dir, "workflow.py")
    activities_file = os.path.join(migration_dir, "activities.py")
    
    already_exists = False
    if os.path.exists(workflow_file):
        already_exists = True
    if os.path.exists(activities_file):
        already_exists = True
    
    if already_exists:
        response = input(f"Workflow and activities files already exist in {migration_dir}. Continue (will overwrite)? (y/N)")
        if response != "y":
            print("Aborting migration.")
            return
    
    session_id = asyncio.run(migrate_using_claude_async(graph, migration_dir))

    print(f"Migration completed! Files saved to {migration_dir}/workflow.py and {migration_dir}/activities.py.")
    print(f"Would you like to continue the conversion with Claude? (Y/n)")
    response = input()
    if response == "n":
        return
    else:
        os.execvp("claude", ["claude", "--resume", session_id])
    