"""Temporal Activities for the basic_static graph migration.

Each activity wraps the corresponding LangGraph node function.
"""

from dataclasses import dataclass
from typing import List

from temporalio import activity

# Import the original node functions from the graph module
from graph import greet, farewell, State


@dataclass
class GreetInput:
    """Input for the greet activity."""

    messages: List[str]


@dataclass
class GreetOutput:
    """Output from the greet activity."""

    messages: List[str]


@dataclass
class FarewellInput:
    """Input for the farewell activity."""

    messages: List[str]


@dataclass
class FarewellOutput:
    """Output from the farewell activity."""

    messages: List[str]


@activity.defn
def greet_activity(input: GreetInput) -> GreetOutput:
    """Activity wrapper for the greet node.

    Calls the original greet function from the LangGraph definition.
    """
    # Assemble the state dictionary expected by the original node function
    state: State = {"messages": list(input.messages)}

    # Call the original node function
    new_state = greet(state)

    # Return the outputs needed by the workflow
    return GreetOutput(messages=new_state["messages"])


@activity.defn
def farewell_activity(input: FarewellInput) -> FarewellOutput:
    """Activity wrapper for the farewell node.

    Calls the original farewell function from the LangGraph definition.
    """
    # Assemble the state dictionary expected by the original node function
    state: State = {"messages": list(input.messages)}

    # Call the original node function
    new_state = farewell(state)

    # Return the outputs needed by the workflow
    return FarewellOutput(messages=new_state["messages"])
