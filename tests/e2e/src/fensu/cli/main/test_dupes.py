"""Installed-console end-to-end tests for the advisory dupes command."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import CliProjectFile, InstalledDupesCliTestCase
from tests.e2e.src.fensu.cli.main.helpers import installed_fensu_executable, write_project_files

_SUMMARY: str = """def summarize_orders(orders, threshold):
    total = 0
    count = 0
    skipped = []
    for order in orders:
        if order.amount > threshold:
            total += order.amount
            count += 1
        else:
            skipped.append(order.identifier)
            record_skip(order, "below threshold")
    average = total / count if count else 0
    report = {"total": total, "count": count, "average": average, "skipped": skipped}
    publish_summary(report, channel="orders")
    return report
"""
_FILES: tuple[CliProjectFile, ...] = (
    CliProjectFile(relative_path="fensu.toml", source='roots = ["src/shop"]\ntests = ["tests"]\n'),
    CliProjectFile(relative_path="src/shop/orders/summary.py", source=_SUMMARY),
    CliProjectFile(relative_path="src/shop/billing/summary.py", source=_SUMMARY),
)


@pytest.mark.parametrize(
    "test_case",
    [
        InstalledDupesCliTestCase(
            description="text output reports the copy as advisory and exits zero",
            files=_FILES,
            argv=("dupes",),
            expected_exit_code=0,
            expected_stdout_fragments=(
                "fensu dupes: 1 duplicated-code cluster (advisory; duplicated-code findings "
                "to review, not fensu check failures)\n",
                "  1. exact sim 1.00, ~113 duplicated tokens, 2 members\n",
                "     src/shop/billing/summary.py:1-15 summarize_orders (113 tokens)\n",
                "     src/shop/orders/summary.py:1-15 summarize_orders (113 tokens)\n",
            ),
        ),
        InstalledDupesCliTestCase(
            description="JSON output is machine readable",
            files=_FILES,
            argv=("dupes", "--json"),
            expected_exit_code=0,
            expected_stdout_fragments=('"advisory": true', '"total_clusters": 1'),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_seeded_copy_when_running_installed_dupes_then_reports_advisory_cluster(
    tmp_path: Path, test_case: InstalledDupesCliTestCase
) -> None:
    write_project_files(root=tmp_path, files=test_case.files)

    completed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(installed_fensu_executable()), *test_case.argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert completed.returncode == test_case.expected_exit_code, completed.stderr
    assert all(fragment in completed.stdout for fragment in test_case.expected_stdout_fragments)
