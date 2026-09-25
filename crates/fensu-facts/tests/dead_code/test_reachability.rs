use fensu_facts::dead_code::main::analyze::analyze;
use fensu_facts::dead_code::models::{ProjectEntryPoint, Root};

use crate::helpers::{module, package};
use crate::test_types::ReachabilityTestCase;

#[test]
fn given_python_entry_mechanisms_when_traversing_then_only_production_reachability_keeps_definitions(
) {
    let test_cases = [
        ReachabilityTestCase {
            description: "tuple and list assignments execute their RHS",
            modules: vec![module("orders", "from . import assignments\n"), module("orders.assignments", "def tuple_setup(): return (1, 2)\ndef list_setup(): return (3, 4)\nfirst, second = tuple_setup()\n[third, fourth] = list_setup()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "attribute and subscript assignments execute RHS and target expressions",
            modules: vec![module("orders", "from . import assignments\n"), module("orders.assignments", "def attribute_setup(): return 1\ndef subscript_setup(): return 1\ndef store(): return object()\ndef items(): return {}\ndef index(): return 0\nstore().value = attribute_setup()\nitems()[index()] = subscript_setup()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "annotated assignments execute targets and RHS",
            modules: vec![module("orders", "from . import assignments\n"), module("orders.assignments", "def attribute_setup(): return 1\ndef subscript_setup(): return 1\ndef store(): return object()\ndef items(): return {}\ndef index(): return 0\nstore().value: int = attribute_setup()\nitems()[index()]: int = subscript_setup()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "augmented assignments read targets and execute RHS",
            modules: vec![module("orders", "from . import assignments\n"), module("orders.assignments", "def attribute_setup(): return 1\ndef subscript_setup(): return 1\ndef count_setup(): return 1\ndef store(): return object()\ndef items(): return {}\ndef index(): return 0\nstore().value += attribute_setup()\nitems()[index()] += subscript_setup()\ncount = 0\ncount += count_setup()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "methods skip class bindings while headers and class bodies retain them",
            modules: vec![module("orders", "from .classes import Public\n"), module("orders.classes", "def helper(): pass\ndef header(): pass\ndef decorate(): pass\nclass Public:\n    helper = None\n    header = lambda: None\n    decorate = lambda method: method\n    header()\n    @decorate\n    def run(self, value=header()): return helper()\n")],
            expected_dead: &["orders.classes:header", "orders.classes:decorate"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "methods preserve enclosing function bindings and their own local shadows",
            modules: vec![module("orders", "from .classes import factory\n"), module("orders.classes", "def helper(): pass\ndef local_helper(): pass\ndef factory():\n    def helper(): return 1\n    class Public:\n        helper = None\n        def run(self): return helper()\n        def local(self):\n            local_helper = lambda: None\n            return local_helper()\n    return Public\n")],
            expected_dead: &["orders.classes:helper", "orders.classes:local_helper"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "package wildcard exports traverse facades and terminate cycles",
            modules: vec![module("orders", "from .facade import *\n"), module("orders.facade", "from .handlers import *\n"), module("orders.handlers", "from .facade import *\ndef run_orders(): pass\ndef _private(): pass\n")],
            expected_dead: &["orders.handlers:_private"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "wildcard exports respect explicit all at an intermediate facade",
            modules: vec![module("orders", "from .facade import *\n"), module("orders.facade", "from .handlers import *\n__all__ = ['run_orders']\n"), module("orders.handlers", "def run_orders(): pass\ndef unused(): pass\n")],
            expected_dead: &["orders.handlers:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "empty all blocks wildcard exports",
            modules: vec![module("orders", "from .facade import *\n"), module("orders.facade", "from .handlers import *\n__all__ = []\n"), module("orders.handlers", "def unused(): pass\n")],
            expected_dead: &["orders.handlers:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "orphan and unreachable helper chain",
            modules: vec![module("orders", ""), module("orders.internal", "def _orphan(): pass\ndef tail(): pass\ndef head(): tail()\n")],
            expected_dead: &["orders.internal:", "orders.internal:_orphan", "orders.internal:tail", "orders.internal:head"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "import executes a module without rooting every definition",
            modules: vec![module("orders", "from . import internal\n"), module("orders.internal", "def _orphan(): pass\n")],
            expected_dead: &["orders.internal:_orphan"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "dead import cycle",
            modules: vec![module("orders", ""), module("orders.a", "from .b import second\ndef first(): second()\n"), module("orders.b", "from .a import first\ndef second(): first()\n")],
            expected_dead: &["orders.a:", "orders.a:first", "orders.b:", "orders.b:second"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "script aliases and parameter shadowing",
            modules: vec![module("orders", ""), module("orders.cli", "from .internal import live as call\nfrom .internal import unused\ndef main(unused):\n    call()\n    unused()\n"), module("orders.internal", "def live(): pass\ndef unused(): pass\n")],
            entries: &["orders.cli:main"],
            expected_dead: &["orders.internal:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "public class exports preserve dunders and contracts",
            modules: vec![module("orders", "from .internal import Adapter\n__all__ = ['Adapter']\n"), module("orders.internal", "def helper(): pass\nclass Adapter:\n    def __call__(self): helper()\n    def contract(self): helper()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "constant identity and dead self initializer",
            modules: vec![module("orders", "from .a import VALUE\n__all__ = ['VALUE']\n"), module("orders.a", "VALUE = 1\n"), module("orders.b", "VALUE = 2\nDEAD = lambda: DEAD\n")],
            expected_dead: &["orders.b:", "orders.b:VALUE", "orders.b:DEAD"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "configured roots match before reachability",
            modules: vec![module("orders", ""), module("orders.handlers", "def run_orders(): pass\n")],
            roots: vec![Root { modules: vec!["orders.handlers".to_owned()], symbols: vec!["run_*".to_owned()] }],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "recursive annotations do not self-root dead declarations",
            modules: vec![module("orders", "from . import shapes\n"), module("orders.shapes", "class Node:\n    child: 'Node'\ndef recursive() -> 'recursive': pass\n")],
            expected_dead: &["orders.shapes:Node", "orders.shapes:recursive"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "removed declaration makes its root stale",
            modules: vec![module("orders", "")],
            roots: vec![Root { modules: vec!["orders.handlers".to_owned()], symbols: vec!["run_*".to_owned()] }],
            expected_stale: &[0],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "literal importlib member access",
            modules: vec![module("orders", ""), module("orders.cli", "import importlib\ndef main():\n    importlib.import_module('orders.handlers').run_orders()\n"), module("orders.handlers", "def run_orders(): pass\ndef unused(): pass\n")],
            entries: &["orders.cli:main"], expected_dead: &["orders.handlers:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "arbitrary decorator is not registration",
            modules: vec![module("orders", "from . import internal\n"), module("orders.internal", "from functools import lru_cache\n@lru_cache\ndef unused(): pass\n")],
            expected_dead: &["orders.internal:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "private and public main placement are not roots",
            modules: vec![module("orders", ""), module("orders.service.main._parse", "def parse_orders(): pass\n"), module("orders.service.main.parse", "def parse_orders(): pass\n")],
            expected_dead: &["orders.service.main._parse:", "orders.service.main._parse:parse_orders", "orders.service.main.parse:", "orders.service.main.parse:parse_orders"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "exported and registered main entries",
            modules: vec![module("orders", "from .service.main._parse import parse_orders\n__all__ = ['parse_orders']\n"), module("orders.service.main._parse", "def parse_orders(): pass\n"), module("orders.service.main.parse", "def parse_orders(): pass\n")],
            entries: &["orders.service.main.parse:parse_orders"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "initializers execute but lambda bodies are deferred",
            modules: vec![module("orders", "from . import internal\n"), module("orders.internal", "def setup(): pass\ndef deferred(): pass\nUNUSED = setup()\nLATER = lambda: deferred()\n")],
            expected_dead: &["orders.internal:deferred", "orders.internal:UNUSED", "orders.internal:LATER"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "atexit callback registration",
            modules: vec![module("orders", "from . import callbacks\n"), module("orders.callbacks", "from atexit import register as on_exit\ndef helper(): pass\n@on_exit\ndef shutdown(): helper()\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "nested initializer relative imports",
            modules: vec![module("orders", ""), package("orders.api", "from .parser import parse_orders\n__all__ = ['parse_orders']\n"), module("orders.api.parser", "def parse_orders(): pass\n")],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "literal importlib local alias",
            modules: vec![module("orders", ""), module("orders.cli", "from importlib import import_module as load\ndef main():\n    handlers = load('orders.handlers')\n    handlers.run_orders()\n"), module("orders.handlers", "def run_orders(): pass\ndef unused(): pass\n")],
            entries: &["orders.cli:main"], expected_dead: &["orders.handlers:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "application registrations depend on the live application",
            modules: vec![module("orders", ""), module("orders.web", "from fastapi import FastAPI\napp = FastAPI()\ndef helper(): pass\n@app.get('/orders')\ndef list_orders(): helper()\ndef unused(): pass\n")],
            entries: &["orders.web:app"], expected_dead: &["orders.web:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "uncalled local closure does not root its helper",
            modules: vec![module("orders", ""), module("orders.cli", "def helper(): pass\ndef main():\n    def never_called(): helper()\n    return 1\n")],
            entries: &["orders.cli:main"], expected_dead: &["orders.cli:helper"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "cross-module callback registration is independent of discovery order",
            modules: vec![module("orders", ""), module("orders.api.callbacks", "from .application import app\n@app.get('/orders')\ndef list_orders(): pass\n"), module("orders.api.application", "from fastapi import FastAPI\napp = FastAPI()\nfrom . import callbacks\n")],
            entries: &["orders.api.application:app"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "returned local closure retains its dependencies",
            modules: vec![module("orders", ""), module("orders.cli", "def helper(): pass\ndef main():\n    def callback(): helper()\n    return callback\n")],
            entries: &["orders.cli:main"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "conditional imports preserve both possible bindings",
            modules: vec![module("orders", ""), module("orders.cli", "if condition:\n    from .a import parse as handler\nelse:\n    from .b import parse as handler\ndef main(): handler()\n"), module("orders.a", "def parse(): pass\n"), module("orders.b", "def parse(): pass\n")],
            entries: &["orders.cli:main"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "a final import shadows an earlier declaration",
            modules: vec![module("orders", ""), module("orders.cli", "def handler(): pass\nfrom .handlers import run_orders as handler\ndef main(): handler()\n"), module("orders.handlers", "def run_orders(): pass\n")],
            entries: &["orders.cli:main"], expected_dead: &["orders.cli:handler"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "wildcard imports resolve actual symbol references",
            modules: vec![module("orders", ""), module("orders.cli", "from .handlers import *\ndef main(): run_orders()\n"), module("orders.handlers", "def run_orders(): pass\ndef unused(): pass\n")],
            entries: &["orders.cli:main"], expected_dead: &["orders.handlers:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "entrypoint declaration is distinct from a same-named child module",
            modules: vec![module("orders", ""), package("orders.api", "def cli(): pass\n"), module("orders.api.cli", "def main(): pass\n")],
            entries: &["orders.api:cli"], expected_dead: &["orders.api.cli:", "orders.api.cli:main"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "a facade wrapper can reach a same-named child module without merging them",
            modules: vec![module("orders", ""), package("orders.api", "def cli():\n    from .cli import main\n    main()\n"), module("orders.api.cli", "def main(): pass\ndef unused(): pass\n")],
            entries: &["orders.api:cli"], expected_dead: &["orders.api.cli:unused"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "global reads before rebinding retain the original callable",
            modules: vec![module("orders", ""), module("orders.cli", "from .handlers import run_orders\ndef main():\n    global run_orders\n    run_orders()\n    run_orders = None\n"), module("orders.handlers", "def run_orders(): pass\n")],
            entries: &["orders.cli:main"],
            ..Default::default()
        },
        ReachabilityTestCase {
            description: "script executes parents and preserves quoted type references",
            modules: vec![module("orders", ""), package("orders.service", "def setup(): pass\nsetup()\n"), module("orders.service.cli", "class Result: pass\ndef main() -> 'list[Result]': return []\n")],
            entries: &["orders.service.cli:main"],
            ..Default::default()
        },
    ];
    for test_case in test_cases {
        let entries = test_case
            .entries
            .iter()
            .map(|entry| ProjectEntryPoint {
                kind: "script".to_owned(),
                reference: (*entry).to_owned(),
            })
            .collect::<Vec<_>>();
        let result = analyze(&test_case.modules, &entries, &test_case.roots);
        let dead = result
            .dead
            .into_iter()
            .map(|declaration| {
                format!(
                    "{}:{}",
                    test_case.modules[declaration.module].name, declaration.name
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(dead, test_case.expected_dead, "{}", test_case.description);
        assert_eq!(
            result.stale_roots, test_case.expected_stale,
            "{}",
            test_case.description
        );
    }
}
