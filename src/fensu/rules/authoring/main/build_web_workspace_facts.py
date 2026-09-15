"""Approved construction boundary for serialized web facts."""

from fensu.rules.authoring._helpers.web_facts import web_workspace_facts
from fensu.rules.authoring.models import WebWorkspaceFacts


def build_web_workspace_facts(*, payload: object) -> WebWorkspaceFacts:
    """Build immutable public web facts from one strict native payload."""

    return web_workspace_facts(payload=payload)
