"""Real native/exemplar parity over production graph inputs."""

from pathlib import Path

import pytest

from fensu.config.main.build_config import build_config
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.main._resolve_rule_spec import resolve_rule_spec
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.exemplars.constants import NATIVE_CUSTOM_RULE_EQUIVALENTS
from fensu.rules.layers.main._dead_code_rules import dead_code_rules
from tests.integration.src.fensu.rules.exemplars._test_types import ReachabilityTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        ReachabilityTestCase(
            "module-level alias preserves member references",
            (
                (
                    "src/orders/__main__.py",
                    "import orders.handlers as handlers\nalias = handlers\nalias.run_orders()\n",
                ),
                ("src/orders/handlers.py", "def run_orders(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
        ),
        ReachabilityTestCase(
            "empty production surface still checks roots",
            (),
            (0, 1, 0),
            roots=(("orders.missing", "*"),),
        ),
        ReachabilityTestCase(
            "dead helper chain",
            (("src/orders/internal.py", "def tail(): pass\ndef head(): tail()\n"),),
            (2, 0, 1),
        ),
        ReachabilityTestCase(
            "import executes without rooting definitions",
            (
                ("src/orders/__init__.py", "from . import internal\n"),
                ("src/orders/internal.py", "def orphan(): pass\n"),
            ),
            (1, 0, 0),
        ),
        ReachabilityTestCase(
            "parameter shadows imported callable",
            (
                (
                    "src/orders/cli.py",
                    "from .helpers import live as call\nfrom .helpers import unused\ndef main(unused):\n    call()\n    unused()\n",
                ),
                ("src/orders/helpers.py", "def live(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "constant identity and deferred initializer",
            (
                ("src/orders/__init__.py", "from .a import VALUE\n__all__ = ['VALUE']\n"),
                ("src/orders/a.py", "VALUE = 1\n"),
                ("src/orders/b.py", "VALUE = 2\nDEAD = lambda: DEAD\n"),
            ),
            (2, 0, 1),
        ),
        ReachabilityTestCase(
            "recursive annotation is not a root",
            (
                ("src/orders/__init__.py", "from . import shapes\n"),
                (
                    "src/orders/shapes.py",
                    "class Node:\n    child: 'Node'\ndef recursive() -> 'recursive': pass\n",
                ),
            ),
            (2, 0, 0),
        ),
        ReachabilityTestCase(
            "literal importlib direct member",
            (
                (
                    "src/orders/__main__.py",
                    "import importlib\nimportlib.import_module('orders.handlers').run_orders()\n",
                ),
                ("src/orders/handlers.py", "def run_orders(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
        ),
        ReachabilityTestCase(
            "arbitrary decorator is not registration",
            (
                ("src/orders/__init__.py", "from . import internal\n"),
                (
                    "src/orders/internal.py",
                    "from functools import lru_cache\n@lru_cache\ndef unused(): pass\n",
                ),
            ),
            (1, 0, 0),
        ),
        ReachabilityTestCase(
            "public and private main placement",
            (
                ("src/orders/main/_parse.py", "def parse(): pass\n"),
                ("src/orders/main/parse.py", "def parse(): pass\n"),
            ),
            (2, 0, 2),
        ),
        ReachabilityTestCase(
            "initializers execute but lambdas defer",
            (
                ("src/orders/__init__.py", "from . import internal\n"),
                (
                    "src/orders/internal.py",
                    "def setup(): pass\ndef deferred(): pass\nUNUSED = setup()\nLATER = lambda: deferred()\n",
                ),
            ),
            (3, 0, 0),
        ),
        ReachabilityTestCase(
            "atexit decorator registers callback",
            (
                ("src/orders/__init__.py", "from . import callbacks\n"),
                (
                    "src/orders/callbacks.py",
                    "from atexit import register as on_exit\ndef helper(): pass\n@on_exit\ndef shutdown(): helper()\n",
                ),
            ),
            (0, 0, 0),
        ),
        ReachabilityTestCase(
            "nested initializer exports",
            (
                (
                    "src/orders/api/__init__.py",
                    "from .parser import parse_orders\n__all__ = ['parse_orders']\n",
                ),
                ("src/orders/api/parser.py", "def parse_orders(): pass\n"),
            ),
            (0, 0, 0),
        ),
        ReachabilityTestCase(
            "literal importlib local alias",
            (
                (
                    "src/orders/cli.py",
                    "from importlib import import_module as load\ndef main():\n    handlers = load('orders.handlers')\n    handlers.run_orders()\n",
                ),
                ("src/orders/handlers.py", "def run_orders(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "application registration depends on application",
            (
                (
                    "src/orders/web.py",
                    "from fastapi import FastAPI\napp = FastAPI()\ndef helper(): pass\n@app.get('/orders')\ndef list_orders(): helper()\ndef unused(): pass\n",
                ),
            ),
            (1, 0, 0),
            "[project.entry-points.'orders.apps']\napp = 'orders.web:app'\n",
        ),
        ReachabilityTestCase(
            "uncalled closure does not retain helper",
            (
                (
                    "src/orders/cli.py",
                    "def helper(): pass\ndef main():\n    def never_called(): helper()\n    return 1\n",
                ),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "returned closure retains helper",
            (
                (
                    "src/orders/cli.py",
                    "def helper(): pass\ndef main():\n    def callback(): helper()\n    return callback\n",
                ),
            ),
            (0, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "cross-module application callbacks",
            (
                (
                    "src/orders/api/callbacks.py",
                    "from .application import app\n@app.get('/orders')\ndef list_orders(): pass\n",
                ),
                (
                    "src/orders/api/application.py",
                    "from fastapi import FastAPI\napp = FastAPI()\nfrom . import callbacks\n",
                ),
            ),
            (0, 0, 0),
            "[project.entry-points.'orders.apps']\napp = 'orders.api.application:app'\n",
        ),
        ReachabilityTestCase(
            "conditional aliases preserve both bindings",
            (
                (
                    "src/orders/cli.py",
                    "if condition:\n    from .a import parse as handler\nelse:\n    from .b import parse as handler\ndef main(): handler()\n",
                ),
                ("src/orders/a.py", "def parse(): pass\n"),
                ("src/orders/b.py", "def parse(): pass\n"),
            ),
            (0, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "final import shadows declaration",
            (
                (
                    "src/orders/cli.py",
                    "def handler(): pass\nfrom .handlers import run_orders as handler\ndef main(): handler()\n",
                ),
                ("src/orders/handlers.py", "def run_orders(): pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "wildcard import resolves actual references",
            (
                ("src/orders/cli.py", "from .handlers import *\ndef main(): run_orders()\n"),
                ("src/orders/handlers.py", "def run_orders(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "entry and child module have separate identities",
            (
                ("src/orders/api/__init__.py", "def cli(): pass\n"),
                ("src/orders/api/cli.py", "def main(): pass\n"),
            ),
            (1, 0, 1),
            "[project.scripts]\norders = 'orders.api:cli'\n",
        ),
        ReachabilityTestCase(
            "facade wrapper reaches same-named child",
            (
                (
                    "src/orders/api/__init__.py",
                    "def cli():\n    from .cli import main\n    main()\n",
                ),
                ("src/orders/api/cli.py", "def main(): pass\ndef unused(): pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.api:cli'\n",
        ),
        ReachabilityTestCase(
            "global read before rebinding",
            (
                (
                    "src/orders/cli.py",
                    "from .handlers import run_orders\ndef main():\n    global run_orders\n    run_orders()\n    run_orders = None\n",
                ),
                ("src/orders/handlers.py", "def run_orders(): pass\n"),
            ),
            (0, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "script executes parents and quoted annotations",
            (
                ("src/orders/service/__init__.py", "def setup(): pass\nsetup()\n"),
                (
                    "src/orders/service/cli.py",
                    "class Result: pass\ndef main() -> 'list[Result]': return []\n",
                ),
            ),
            (0, 0, 0),
            "[project.scripts]\norders = 'orders.service.cli:main'\n",
        ),
        ReachabilityTestCase(
            "unrooted cycle",
            (
                (
                    "src/orders/internal.py",
                    "def first():\n    second()\ndef second():\n    first()\n",
                ),
            ),
            (2, 0, 1),
        ),
        ReachabilityTestCase(
            "script aliases and unused declaration",
            (
                (
                    "src/orders/cli.py",
                    "from orders.helpers import live as alias\ndef main():\n    alias()\n",
                ),
                ("src/orders/helpers.py", "def live():\n    pass\ndef dead():\n    pass\n"),
            ),
            (1, 0, 0),
            "[project.scripts]\norders = 'orders.cli:main'\n",
        ),
        ReachabilityTestCase(
            "reasoned root and stale root",
            (("src/orders/internal.py", "def entry():\n    helper()\ndef helper():\n    pass\n"),),
            (0, 1, 0),
            roots=(("orders.internal", "entry"), ("orders.missing", "*")),
        ),
        ReachabilityTestCase(
            "tests do not root main",
            (
                ("src/orders/main/parse.py", "def parse():\n    pass\n"),
                ("tests/test_parse.py", "from orders.main.parse import parse\nparse()\n"),
            ),
            (1, 0, 1),
        ),
        ReachabilityTestCase(
            "public reexport",
            (
                ("src/orders/__init__.py", "from orders.internal import api\n__all__ = ['api']\n"),
                ("src/orders/internal.py", "def api():\n    pass\ndef dead():\n    pass\n"),
            ),
            (1, 0, 0),
        ),
        ReachabilityTestCase(
            "plugin annotations defaults and contracts",
            (
                (
                    "src/orders/plugin.py",
                    "class Model:\n    def contract(self):\n        helper()\ndef helper():\n    pass\nDEFAULT = Model()\ndef entry(value: 'Model' = DEFAULT):\n    pass\n",
                ),
            ),
            (0, 0, 0),
            "[project.entry-points.'orders.plugins']\nplugin = 'orders.plugin:entry'\n",
        ),
        ReachabilityTestCase(
            "main literal dynamic import",
            (
                (
                    "src/orders/__main__.py",
                    "import importlib\nplugin = importlib.import_module('orders.plugin')\nplugin.entry()\n",
                ),
                ("src/orders/plugin.py", "def entry():\n    pass\ndef dead():\n    pass\n"),
            ),
            (1, 0, 0),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_production_graph_when_evaluating_then_public_traversal_matches_native(
    test_case: ReachabilityTestCase,
    tmp_path: Path,
) -> None:
    (tmp_path / "src/orders").mkdir(parents=True, exist_ok=True)
    for relative, source in test_case.files:
        path: Path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    (tmp_path / "pyproject.toml").write_text(test_case.metadata)
    config: Config = build_config(
        raw={
            "roots": ["src/orders"],
            "tests": ["tests"],
            "dead_code": {
                "enabled": True,
                "roots": [
                    {"modules": [module], "symbols": [symbol], "reason": "External registration."}
                    for module, symbol in test_case.roots
                ],
            },
        }
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=tmp_path)
    counts: list[int] = []
    for core in dead_code_rules():
        exemplar: RuleSpec = resolve_rule_spec(value=NATIVE_CUSTOM_RULE_EQUIVALENTS[core.code])
        native: EvaluationResult = evaluate(tree=tree, ruleset=(core,), config=config)
        custom: EvaluationResult = evaluate(tree=tree, ruleset=(exemplar,), config=config)
        native_findings: list[tuple[str, int | None, int | None, str]] = sorted(
            (str(f.path), f.line, f.column, f.message) for f in native.faults
        )
        custom_findings: list[tuple[str, int | None, int | None, str]] = sorted(
            (str(f.path), f.line, f.column, f.message) for f in custom.faults
        )
        assert custom_findings == native_findings
        counts.append(len(native.faults))
    assert tuple(counts) == test_case.expected_counts


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
