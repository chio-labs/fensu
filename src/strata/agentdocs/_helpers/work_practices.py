"""Render mandatory project-work and testing guidance."""

from __future__ import annotations


def work_practice_lines() -> tuple[str, ...]:
    """Return scope, refactor, testing, infrastructure, and isolation guidance."""

    return (
        "## Working With Existing Drift",
        "",
        "The user request defines the scope of remediation. A large fault count is an "
        "architectural baseline, not authorization to fix unrelated code.",
        "",
        "- If the user requests one change, do not expand into unrelated fault remediation.",
        "- If the user explicitly requests a broader refactor, particular fault families, or "
        "zero faults, treat that broader target as authorized scope.",
        "- Satisfy faults by improving code under the current policy. Do not weaken selection, "
        "thresholds, exceptions, or custom rules unless the user explicitly requests a policy "
        "change.",
        "- Before moving or splitting behavior, map the affected call flow and run the existing "
        "tests.",
        "- When coverage around changed behavior is weak or unknown, add focused "
        "characterization tests before refactoring.",
        "- Preserve behavior first and improve structure in verifiable slices.",
        "- Distinguish pre-existing faults from regressions introduced by the current work.",
        "",
        "For an explicitly authorized broad refactor, capture the baseline, map affected flows, "
        "establish characterization coverage, work in coherent slices, verify each slice, and "
        "run full final verification. A request to make `strata check` pass means fix the code "
        "under the current policy, not edit configuration until findings disappear.",
        "",
        "## Testing Refactors Safely",
        "",
        "Before materially restructuring behavior, inspect the existing tests. When the affected "
        "behavior is weakly covered or its coverage is uncertain, add focused characterization "
        "tests before moving code.",
        "",
        "Use the cheapest test that faithfully exercises the risk:",
        "",
        "- Unit tests for isolated decisions, transformations, and error handling.",
        "- Integration tests for storage, messaging, process, and adapter boundaries.",
        "- End-to-end tests for user-visible commands and workflows.",
        "- Real local dependencies when they are deterministic and reasonably inexpensive.",
        "",
        "Prefer faithful local infrastructure over mocks when behavior depends on the real "
        "system. Useful options include PostgreSQL, Redis, Kafka or Redpanda, RabbitMQ, NATS, "
        "MinIO, OpenSearch, and similar services available through testcontainers.",
        "",
        "Before using testcontainers, check whether a functioning container runtime is available. "
        "Prefer `docker info`; if Docker is unavailable, check `podman info` and whether a "
        "compatible Docker API socket is configured. Finding the executable alone is not enough: "
        "verify the runtime can actually start containers. When a functioning runtime is "
        "available, testcontainers is an appropriate default for integration behavior that mocks "
        "cannot faithfully represent. Record the container-runtime requirement in the test "
        "documentation or final change summary.",
        "",
        "Use SQLite or DuckDB when they faithfully represent the tested contract. Do not use "
        "SQLite as evidence for PostgreSQL-specific SQL, transactions, locking, concurrency, "
        "extensions, or type behavior.",
        "",
        "Tests requiring real remote credentials or services such as Salesforce or Snowflake "
        "remain a user and project decision.",
        "",
        "When concurrency, retries, duplicate delivery, locking, or shared mutable state are real "
        "risks, add deterministic race-oriented tests where practical. Force relevant "
        "interleavings with barriers, events, controlled workers, or transactional locks rather "
        "than relying on sleeps. Assert atomicity, idempotency, ordering, uniqueness, and retry "
        "behavior as appropriate.",
        "",
        "Do not duplicate every assertion at unit, integration, and end-to-end levels. Each layer "
        "should prove a boundary that cheaper tests cannot prove faithfully.",
        "",
        "## Test Execution And Isolation",
        "",
        "Use the repository's established verification commands first. When pytest-xdist is "
        "installed and the relevant suite supports parallel execution, prefer:",
        "",
        "```bash",
        "pytest -n auto",
        "```",
        "",
        "Write new tests so they can execute independently whenever practical:",
        "",
        "- Use unique temporary paths, databases, schemas, ports, and resource names.",
        "- Do not depend on test execution order.",
        "- Isolate environment changes with fixtures such as monkeypatch.",
        "- Avoid shared process-global mutation.",
        "- Give each worker independent external state where concurrent access would alter the "
        "result.",
        "- Make cleanup safe after both success and failure.",
        "",
        "When some tests genuinely require sequential execution, separate them from the "
        "parallel-safe suite. Run independent batches concurrently only when they do not share "
        "mutable resources. Otherwise run the required batches in sequence, while still using "
        "xdist inside each parallel-safe batch.",
        "",
        "If failures suggest broken isolation, rerun the failing tests sequentially and then rerun "
        "the relevant suite sequentially. A sequential pass does not make the problem acceptable: "
        "identify and correct the shared state, ordering dependency, port collision, database "
        "collision, or timing assumption where reasonable.",
        "",
    )


def custom_rule_authority_lines() -> tuple[str, ...]:
    """Return the mandatory policy-authority boundary."""

    return (
        "## Custom Rule Authority",
        "",
        "Never create, configure, enable, disable, or materially change a custom rule unless the "
        "user explicitly requested it or explicitly approved your proposal.",
        "",
        'An explicit request such as "create a custom rule preventing this" or "make Strata '
        'enforce this convention" is already sufficient authorization. Do not ask for a '
        "redundant second confirmation.",
        "",
        "When work reveals a recurring enforceable convention:",
        "",
        "1. Complete the requested change under the existing policy.",
        "2. Explain the recurring pattern or risk.",
        "3. Suggest a possible custom rule and its intended boundaries.",
        "4. Wait for explicit user approval before implementing it.",
        "",
        "Never add or change policy merely because the current task exposed a possible convention, "
        "similar code appears more than once, a stricter architecture seems preferable, a core "
        "rule is inconvenient, or changing policy would make `strata check` pass. Fix code under "
        "current policy rather than weakening or rewriting policy to avoid the work.",
        "",
    )
