"""MAF Foundry hosted notes agent (Responses protocol 2.0.0)."""

from __future__ import annotations

import os
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from notes import list_notes as list_notes_fs
from notes import read_note as read_note_fs
from notes import save_note as save_note_fs
from pydantic import Field

load_dotenv()

INSTRUCTIONS = """You are a notes assistant for a Foundry hosted session.

When the user asks to save a note:
- Choose a short descriptive filename slug from the note
  content (letters, digits, '-', '_', '.').
- Call save_note with that filename and the note body.
- Your user-visible reply MUST be exactly the tool return
  value with no extra words, punctuation, or commentary.
  Example: saved note as meeting-notes.txt

When the user asks to retrieve prior notes in this session,
use read_note and/or list_notes.
Do not invent note contents. Prefer list_notes if the
filename is unclear.
"""


def _model_deployment_name() -> str:
    name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.environ.get(
        "MICROSOFT_FOUNDRY_MODEL_DEPLOYMENT_NAME"
    )
    if not name:
        raise RuntimeError(
            "Set AZURE_AI_MODEL_DEPLOYMENT_NAME or "
            "MICROSOFT_FOUNDRY_MODEL_DEPLOYMENT_NAME"
        )
    return name


@tool(approval_mode="never_require")
def save_note(
    filename: Annotated[
        str, Field(description="Safe basename for the note under $HOME.")
    ],
    content: Annotated[str, Field(description="UTF-8 note body to write.")],
) -> str:
    """Save one note file under the session $HOME. Overwrites if it exists."""
    return save_note_fs(filename, content)


@tool(approval_mode="never_require")
def read_note(
    filename: Annotated[
        str, Field(description="Safe basename of the note to read under $HOME.")
    ],
) -> str:
    """Read a previously saved note from the session $HOME."""
    return read_note_fs(filename)


@tool(approval_mode="never_require")
def list_notes() -> str:
    """List note filenames stored under the session $HOME."""
    return list_notes_fs()


def main() -> None:
    project_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not project_endpoint:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is required")

    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=_model_deployment_name(),
        credential=DefaultAzureCredential(),
    )
    agent = Agent(
        client=client,
        instructions=INSTRUCTIONS,
        tools=[save_note, read_note, list_notes],
        default_options={"store": False},
    )
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()
