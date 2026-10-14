"""Agent-editable phone helpers.

This file is copied to your agent workspace (~/.mphone/agent-workspace/agent_helpers.py) the
first time it is missing, and never overwritten after that. Add task-specific helpers here;
everything defined in this file is available in `mphone run` scripts next to the core helpers.

Write down what you learn: a helper that encodes a verified trick saves the next task from
rediscovering it. Say in the docstring how you verified it.
"""


def visible_texts(min_confidence: float = 0.3) -> list[str]:
    """Just the strings on screen, top to bottom — cheaper to print than full boxes."""
    from mphone_core.helpers import screen

    return [b["text"] for b in sorted(screen(min_confidence), key=lambda b: (b["y"], b["x"]))]
