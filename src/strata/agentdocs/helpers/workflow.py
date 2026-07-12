"""Render agent navigation and completion-handoff guidance."""

from __future__ import annotations


def navigation_workflow_lines() -> tuple[str, ...]:
    """Return guidance for exploring and explaining architecture-relevant work."""

    return (
        "## Navigation And Work Handoffs",
        "",
        (
            "For any non-trivial change that crosses module or package boundaries, run "
            "`strata map <symbol> --depth 4` before editing. Rerun the same map after "
            "implementation to explain the changed flow. Skip only isolated single-file edits."
        ),
        "",
        (
            "Treat the map as a deterministic call skeleton whose primary benefit is helping the "
            "user understand the system, not proving that the agent explored it. Do not paste a "
            "raw map as the handoff. Read the relevant source to explain purpose and branches, "
            "use the diff to identify what changed and why, and use checks and tests to state what "
            "was verified. Never guess through unresolved calls. If the map cannot resolve the "
            "flow, state that and continue with direct source inspection."
        ),
        "",
        (
            "After a substantial chunk of work, rerun `strata check` and the same map. Include a "
            "user-facing walkthrough only when it materially clarifies a multi-module change. "
            "Default to the smallest affected branch, normally three to eight lines:"
        ),
        "",
        "```text",
        "build_result(...)                           domain/main/build.py:24",
        "└── assemble_result(...)                    domain/helpers/assemble.py:41",
        "    CHANGED: state the behavioral difference and why it was made.",
        "VERIFIED: name the check that proves the changed boundary.",
        "```",
        "",
        (
            "Replace the template with facts from the repository. Preserve enough parent context "
            "to orient the user, but omit unchanged branches that do not aid understanding. Use a "
            "full before/after walkthrough only when ownership or phase boundaries changed "
            "substantially. `DONE`, `PENDING`, and `WE ARE HERE` are agent-authored work-state "
            "annotations, not Strata output."
        ),
        "",
        (
            "Every displayed function must include its repository-relative path and line when "
            "available. Mark changed nodes with `CHANGED` and explain the behavioral difference "
            "and reason, not merely that a file changed. Mark supporting evidence with `VERIFIED`. "
            "When static mapping omits protocol or dynamic dispatch, stitch in the continuation "
            "only after confirming it from source and label it `SOURCE-RESOLVED DYNAMIC BOUNDARY` "
            "so the user can distinguish map output from inspected runtime wiring."
        ),
        "",
        (
            "Do not force a graph into a handoff when one sentence with a clickable `path:line` "
            "communicates the change more clearly."
        ),
        "",
    )
