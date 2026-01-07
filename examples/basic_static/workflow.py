"""Temporal Workflow for the basic_static graph migration.

This workflow mirrors the LangGraph control flow:
START -> greet -> farewell -> END
"""

from datetime import timedelta
from typing import List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import (
        greet_activity,
        GreetInput,
        farewell_activity,
        FarewellInput,
    )


@workflow.defn
class BasicStaticWorkflow:
    """Workflow that executes the greet -> farewell pipeline."""

    @workflow.run
    async def run(self, initial_messages: List[str]) -> List[str]:
        """Execute the workflow.

        Args:
            initial_messages: The initial list of messages to start with.

        Returns:
            The final list of messages after all nodes have executed.
        """
        # Workflow state - corresponds to State["messages"] in LangGraph
        messages = list(initial_messages)

        # Execute greet node (START -> greet)
        greet_result = await workflow.execute_activity(
            greet_activity,
            GreetInput(messages=messages),
            start_to_close_timeout=timedelta(seconds=60),
        )
        messages = greet_result.messages

        # Execute farewell node (greet -> farewell)
        farewell_result = await workflow.execute_activity(
            farewell_activity,
            FarewellInput(messages=messages),
            start_to_close_timeout=timedelta(seconds=60),
        )
        messages = farewell_result.messages

        # farewell -> END
        return messages
