"""Render agent navigation and completion-handoff guidance."""

from __future__ import annotations


def navigation_workflow_lines() -> tuple[str, ...]:
    """Return guidance for exploring and explaining architecture-relevant work."""

    return (
        "## Navigation And Work Handoffs",
        "",
        (
            "Use `strata map <symbol> --depth 4` when tracing an unfamiliar flow, locating "
            "behavior across package boundaries, or recovering the surrounding architecture. "
            "Skip it for trivial, isolated edits."
        ),
        "",
        (
            "Treat the map as a deterministic call skeleton. Read the relevant source to explain "
            "purpose and branches, use the diff to identify changes, and use checks and tests to "
            "state what was verified. Never guess through unresolved calls."
        ),
        "",
        (
            "After a substantial chunk of work, rerun `strata check` and the relevant map. Prefer "
            "a concise guided walkthrough when the work crosses phases or the user is building a "
            "mental model of the subsystem:"
        ),
        "",
        "```text",
        "1. run_command(...)                         cli/main/run.py",
        "   Resolves the invocation and enters the workflow.",
        "",
        "2. build_result(...)                        domain/main/build.py",
        "   ├── resolve_inputs(...)                  unchanged context",
        "   ├── assemble_result(...)                 CHANGED: explain the completed work",
        "   └── validate_result(...)                 VERIFIED: name the supporting check",
        "",
        "3. Back in run_command(...)",
        "   Connect the changed flow to its final user-visible outcome.",
        "```",
        "",
        (
            "Replace the template with facts from the repository. Include the entrypoint, "
            "important phases in execution order, file locations, changed nodes, verified "
            "boundaries, relevant branch decisions, and where control returns. `DONE`, `PENDING`, "
            "and `WE ARE HERE` are agent-authored work-state annotations, not Strata output."
        ),
        "",
        (
            "For narrow or familiar changes, show only the affected map branch with enough parent "
            "context to orient the user. Do not paste the full call tree when a smaller view "
            "communicates the work clearly."
        ),
        "",
    )
