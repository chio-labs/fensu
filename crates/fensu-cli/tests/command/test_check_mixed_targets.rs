use crate::helpers::write;

#[test]
fn given_custom_python_and_rust_options_when_checking_then_native_and_hosted_targets_merge() {
    let test_cases = [crate::test_types::RustMixedTargetTestCase {
        description: "custom Python target and native Rust options coexist",
        expected_exit_code: 1,
        expected_codes: &["FFA001", "FPRSS010"],
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("temporary repository");
        write(
            repository.path().join("Cargo.toml"),
            "[package]\nname = \"example\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            repository.path().join("src/lib.rs"),
            "pub fn sum(left: usize, right: usize) -> usize { left + right }\n",
        );
        write(
            repository.path().join("python/value.py"),
            "def value(item):\n    return item\n",
        );
        write(repository.path().join("rules/custom.py"), "import ast\nfrom fensu import Family, Fault, RuleContext, rule\n@rule(code='XMIX001', family=Family.CUSTOM, slug='mixed', message='mixed')\ndef mixed(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n    return []\n");
        write(repository.path().join("fensu.toml"), "[targets.python]\nanalyzer = \"python\"\nroots = [\"python\"]\ntests = []\ntooling = []\nselect = [\"FFA001\", \"XMIX001\"]\nrule_paths = [\"rules/custom.py\"]\n[targets.rust]\nanalyzer = \"rust\"\nroots = [\"src\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"FPRSS010\"]\n[targets.rust.rule_options.FPRSS010]\nmax_arguments = 1\n");
        let output = std::process::Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-color", "--no-cache"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", crate::helpers::workspace_python())
            .output()
            .expect("mixed check runs");
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        assert_eq!(
            output.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {stdout} {stderr}",
            test_case.description
        );
        for code in test_case.expected_codes {
            assert!(stdout.contains(code), "{}: {stdout}", test_case.description);
        }
    }
}
