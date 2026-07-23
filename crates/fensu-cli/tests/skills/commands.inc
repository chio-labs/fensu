use std::fs;
use std::process::{Command, Stdio};

use crate::helpers::{
    collide_skill, diverge_skill, malform_skill, native, native_with_python, project, remove_skill,
    stale_skill, target, text, workspace_python, write, CONFIG,
};
use crate::test_types::{
    ExceptionSymbolTestCase, FreshnessTestCase, PublicationRaceTestCase, SkillsCommandTestCase,
};

#[test]
fn given_destination_change_during_staging_when_publishing_then_rolls_back_prior_writes() {
    let test_cases = [PublicationRaceTestCase {
        description: "concurrent destination writer wins and prior transaction writes roll back",
        staged_payload_size: 64 * 1024 * 1024,
        expected_exit_code: 2,
    }];
    for test_case in test_cases {
        let repository = project();
        let source = repository.path().join(".ai/knowledge/repo/skills/alpha");
        write(source.join("SKILL.md"), b"# Alpha\n");
        write(source.join("assets/large.bin"), b"initial\n");
        let initial = native(repository.path(), &["--target", "agents"]);
        assert_eq!(initial.status.code(), Some(0), "{}", text(&initial.stderr));
        let generated = target(repository.path(), ".agents", "fensu-fixture");
        let generated_before = fs::read(&generated).expect("generated skill before race");
        let installed = repository
            .path()
            .join(".agents/skills/alpha/assets/large.bin");
        write(
            source.join("assets/large.bin"),
            vec![b'x'; test_case.staged_payload_size],
        );
        let mut child = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["skills", "--target", "agents"])
            .current_dir(repository.path())
            .env(
                "FENSU_PYTHON",
                repository.path().join("python-does-not-exist"),
            )
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("racing native update");
        let mut staging_observed = false;
        for _ in 0..10_000 {
            staging_observed = fs::read_dir(installed.parent().expect("installed parent"))
                .expect("installed directory")
                .filter_map(Result::ok)
                .any(|entry| {
                    entry
                        .file_name()
                        .to_string_lossy()
                        .starts_with(".fensu-stage-")
                });
            if staging_observed {
                break;
            }
            assert!(
                child.try_wait().expect("race process status").is_none(),
                "{}: process finished before staging was observed",
                test_case.description
            );
            std::thread::sleep(std::time::Duration::from_millis(1));
        }
        assert!(staging_observed, "{}", test_case.description);
        write(&installed, b"concurrent writer\n");

        let result = child.wait_with_output().expect("racing update result");

        assert_eq!(
            result.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(text(&result.stderr).contains("changed during update"));
        assert_eq!(
            fs::read(&installed).expect("concurrent destination"),
            b"concurrent writer\n"
        );
        assert_eq!(
            fs::read(generated).expect("rolled back generated skill"),
            generated_before
        );
    }
}

#[test]
fn given_missing_and_ambiguous_exception_symbols_when_updating_then_rejects_configuration() {
    let test_cases = [
        ExceptionSymbolTestCase {
            description: "missing function symbol",
            source: b"def present() -> None:\n    pass\n",
            symbol: "missing",
            expected_error: "Rule exception symbol does not exist",
        },
        ExceptionSymbolTestCase {
            description: "duplicate top-level function symbol",
            source: b"def duplicate() -> None:\n    pass\n\ndef duplicate() -> None:\n    pass\n",
            symbol: "duplicate",
            expected_error: "Rule exception symbol is ambiguous",
        },
    ];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("exception project");
        write(
            repository.path().join("fensu.toml"),
            format!(
                "roots = [\"src/pkg\"]\ntests = []\nselect = [\"FF\"]\n[[rule_exceptions]]\nrule = \"FFT001\"\npath = \"src/pkg/target.py\"\nsymbols = [\"{}\"]\nreason = \"required\"\n[skills]\nname = \"fixture\"\n",
                test_case.symbol
            ),
        );
        write(
            repository.path().join("src/pkg/target.py"),
            test_case.source,
        );

        let result = native(repository.path(), &["--target", "agents"]);

        assert!(
            text(&result.stderr).contains(test_case.expected_error),
            "{}: {}",
            test_case.description,
            text(&result.stderr)
        );
        assert!(!repository.path().join(".agents").exists());
    }
}

#[test]
fn given_built_in_rules_when_updating_and_checking_then_runs_without_python() {
    let test_cases = [SkillsCommandTestCase {
        description: "built-in update, check, help, and target deduplication stay native",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = project();
        let help = native(repository.path(), &["--help"]);
        assert_eq!(
            help.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(text(&help.stdout).starts_with("usage: fensu skills"));

        let update = native(
            repository.path(),
            &[
                "--target", "agents", "--target", "opencode", "--target", "agents",
            ],
        );
        assert_eq!(update.status.code(), Some(0), "{}", text(&update.stderr));
        assert_eq!(text(&update.stdout).matches("SKILL.md").count(), 2);
        assert!(target(repository.path(), ".agents", "fensu-fixture").is_file());
        assert!(target(repository.path(), ".opencode", "fensu-fixture").is_file());

        let check = native(
            repository.path(),
            &["--target", "agents", "--target", "opencode", "--check"],
        );
        assert_eq!(check.status.code(), Some(0), "{}", text(&check.stderr));
        assert!(text(&check.stdout).starts_with("Fensu skill files are current:\n"));
    }
}

#[test]
fn given_path_scoped_rule_ignores_when_generating_skill_then_renders_policy_and_tracks_freshness() {
    let repository = project();
    let configured = format!(
        "{CONFIG}\n[[rule_ignores]]\nrules = [\"FFA\"]\npaths = [\"src/pkg/generated/**\"]\nreason = \"Generated interfaces are checked upstream.\"\n"
    );
    write(repository.path().join("fensu.toml"), &configured);

    let update = native(repository.path(), &["--target", "agents"]);
    let skill_path = target(repository.path(), ".agents", "fensu-fixture");
    let skill = text(&fs::read(&skill_path).expect("generated skill"));

    assert_eq!(update.status.code(), Some(0), "{}", text(&update.stderr));
    assert!(skill.contains("### Configured Path-Scoped Rule Ignores"));
    assert!(skill.contains("src/pkg/generated/**"));
    assert!(skill.contains("Generated interfaces are checked upstream."));

    write(
        repository.path().join("fensu.toml"),
        configured.replace("checked upstream", "checked by generation tests"),
    );
    let check = native(repository.path(), &["--target", "agents", "--check"]);

    assert_eq!(check.status.code(), Some(1));
    assert!(text(&check.stdout).contains("stale"));
}

#[test]
fn given_installed_skill_states_when_checking_then_reports_status_without_writes() {
    let test_cases = [
        FreshnessTestCase {
            description: "missing generated skill",
            expected_state: "missing",
            expected_exit_code: 1,
            mutate: remove_skill,
        },
        FreshnessTestCase {
            description: "stale generated skill",
            expected_state: "stale",
            expected_exit_code: 1,
            mutate: stale_skill,
        },
        FreshnessTestCase {
            description: "divergent generated skill",
            expected_state: "divergent",
            expected_exit_code: 1,
            mutate: diverge_skill,
        },
        FreshnessTestCase {
            description: "malformed generated ownership marker",
            expected_state: "malformed-marker",
            expected_exit_code: 1,
            mutate: malform_skill,
        },
        FreshnessTestCase {
            description: "unmanaged generated skill collision",
            expected_state: "collision",
            expected_exit_code: 2,
            mutate: collide_skill,
        },
    ];
    for test_case in test_cases {
        let repository = project();
        let path = target(repository.path(), ".agents", "fensu-fixture");
        let update = native(repository.path(), &["--target", "agents"]);
        assert_eq!(update.status.code(), Some(0));
        let original = fs::read(&path).expect("installed skill");
        (test_case.mutate)(repository.path(), &path, &original);
        let before = fs::read(&path).ok();
        let check = native(repository.path(), &["--target", "agents", "--check"]);
        assert_eq!(
            check.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(
            text(&check.stdout).contains(&format!(": {}\n", test_case.expected_state)),
            "{}",
            test_case.description
        );
        assert_eq!(fs::read(&path).ok(), before);
    }
}

#[test]
fn given_project_bundle_when_synchronizing_then_preserves_bytes_modes_and_ownership() {
    let test_cases = [SkillsCommandTestCase {
        description: "project bundle sync preserves binary data and removes same-owner stale copy",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = project();
        let source = repository.path().join(".ai/knowledge/repo/skills/alpha");
        write(source.join("SKILL.md"), b"# Alpha\n");
        write(source.join("assets/data.bin"), b"\0\xffbinary\n");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(
                source.join("assets/data.bin"),
                fs::Permissions::from_mode(0o750),
            )
            .expect("source mode");
        }

        let update = native(repository.path(), &["--target", "agents"]);
        assert_eq!(
            update.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            text(&update.stderr)
        );
        let installed = repository
            .path()
            .join(".agents/skills/alpha/assets/data.bin");
        assert_eq!(
            fs::read(&installed).expect("installed binary"),
            b"\0\xffbinary\n"
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                fs::metadata(&installed)
                    .expect("installed metadata")
                    .permissions()
                    .mode()
                    & 0o7777,
                0o750
            );
        }

        write(&installed, b"drift\xff");
        let check = native(repository.path(), &["--target", "agents", "--check"]);
        assert_eq!(check.status.code(), Some(1));
        assert!(text(&check.stdout).contains("assets/data.bin: divergent"));

        fs::remove_dir_all(&source).expect("remove canonical bundle");
        let update = native(repository.path(), &["--target", "agents"]);
        assert_eq!(update.status.code(), Some(0), "{}", text(&update.stderr));
        assert!(!repository.path().join(".agents/skills/alpha").exists());
    }
}

#[test]
fn given_unmanaged_and_foreign_bundles_when_forcing_then_only_unmanaged_is_replaced() {
    let test_cases = [SkillsCommandTestCase {
        description: "force replaces unmanaged guidance but preserves another project's skill",
        expected_exit_code: 2,
    }];
    for test_case in test_cases {
        let repository = project();
        let unmanaged = target(repository.path(), ".agents", "fensu-fixture");
        write(&unmanaged, b"user guidance\n");
        let blocked = native(repository.path(), &["--target", "agents"]);
        assert_eq!(
            blocked.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert_eq!(
            fs::read(&unmanaged).expect("preserved unmanaged"),
            b"user guidance\n"
        );
        let forced = native(repository.path(), &["--target", "agents", "--force"]);
        assert_eq!(forced.status.code(), Some(0), "{}", text(&forced.stderr));

        let second = tempfile::tempdir().expect("second project");
        write(second.path().join("fensu.toml"), CONFIG);
        write(second.path().join("src/pkg/__init__.py"), b"");
        let shared = repository.path().join("shared");
        let first = native(
            repository.path(),
            &[
                "--target",
                "opencode",
                "--install-root",
                shared.to_str().expect("UTF-8 shared path"),
            ],
        );
        assert_eq!(first.status.code(), Some(0));
        let shared_target = target(&shared, ".opencode", "fensu-fixture");
        let original = fs::read(&shared_target).expect("shared skill");
        let foreign = native(
            second.path(),
            &[
                "--target",
                "opencode",
                "--install-root",
                shared.to_str().expect("UTF-8 shared path"),
                "--force",
            ],
        );
        assert_eq!(foreign.status.code(), Some(2));
        assert!(text(&foreign.stderr).contains("owned by another Fensu project"));
        assert_eq!(
            fs::read(shared_target).expect("preserved foreign skill"),
            original
        );
    }
}

#[cfg(unix)]
#[test]
fn given_symlink_and_case_collisions_when_updating_then_preflight_prevents_all_writes() {
    let test_cases = [SkillsCommandTestCase {
        description: "unsafe symlink and case-normalized identity collision fail before writes",
        expected_exit_code: 2,
    }];
    for test_case in test_cases {
        let repository = project();
        let outside = repository.path().join("outside");
        fs::create_dir(&outside).expect("outside directory");
        std::os::unix::fs::symlink(&outside, repository.path().join(".opencode"))
            .expect("unsafe symlink");
        let result = native(repository.path(), &[]);
        assert_eq!(
            result.status.code(),
            Some(test_case.expected_exit_code),
            "{}",
            test_case.description
        );
        assert!(text(&result.stderr).contains("unsafe skill target"));
        assert!(!repository.path().join(".claude").exists());
        assert!(!repository.path().join(".agents").exists());

        let collision = project();
        write(
            collision
                .path()
                .join(".agents/skills/Fensu-Fixture/user.txt"),
            b"user\n",
        );
        let result = native(collision.path(), &["--target", "agents", "--force"]);
        assert_eq!(result.status.code(), Some(2));
        assert!(text(&result.stderr).contains("normalization collides"));
        assert!(!target(collision.path(), ".agents", "fensu-fixture").exists());
    }
}

#[cfg(unix)]
#[test]
fn given_custom_rules_when_updating_then_one_compatible_metadata_host_is_required() {
    use std::os::unix::fs::PermissionsExt;

    let Some(python_executable) = workspace_python() else {
        return;
    };

    let test_cases = [SkillsCommandTestCase {
        description: "custom rules use one host and host failures leave targets untouched",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let repository = tempfile::tempdir().expect("custom-rule project");
        write(
            repository.path().join("fensu.toml"),
            b"roots = [\"src/pkg\"]\ntests = []\nselect = [\"XSK001\"]\nrule_paths = [\"rules/custom.py\"]\n[rule_options.XSK001]\nmode = \"strict\"\nlimit = 7\n[skills]\nname = \"fixture\"\n",
        );
        write(
            repository.path().join("src/pkg/target.py"),
            b"VALUE: int = 1\n",
        );
        write(
            repository.path().join("rules/custom.py"),
            br#"import ast
from fensu import Family, Fault, RuleContext, RuleOption, rule

@rule(
    code="XSK001",
    family=Family.CUSTOM,
    slug="always",
    message="custom fault",
    options=(
        RuleOption.string(
            name="mode",
            required=True,
            choices=("strict", "lenient"),
            description="Evaluation mode.",
        ),
        RuleOption.integer(
            name="limit",
            default=3,
            minimum=1,
            maximum=10,
            description="Maximum findings.",
        ),
        RuleOption.boolean(name="enabled", default=True),
        RuleOption.string_list(name="paths", default=("src",), minimum_items=1),
        RuleOption.integer_list(name="levels", default=(1, 2), minimum_items=1),
    ),
)
def always(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [ctx.fault(node=module.body[0])]
"#,
        );
        let count = repository.path().join("host.count");
        let wrapper = repository.path().join("python-wrapper");
        let wrapper_text = format!(
            "#!/bin/sh\nprintf x >> '{}'\nexec '{}' \"$@\"\n",
            count.display(),
            python_executable.display()
        );
        write(&wrapper, wrapper_text);
        fs::set_permissions(&wrapper, fs::Permissions::from_mode(0o755)).expect("wrapper mode");

        let update = native_with_python(repository.path(), &["--target", "agents"], &wrapper);
        assert_eq!(
            update.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            text(&update.stderr)
        );
        assert_eq!(fs::read(&count).expect("host count"), b"x");
        let guidance = text(
            &fs::read(target(repository.path(), ".agents", "fensu-fixture"))
                .expect("custom guidance"),
        );
        assert!(guidance.contains("### XSK001: always"));
        assert!(guidance.contains("#### `limit`"));
        assert!(guidance.contains("- Default: 3"));
        assert!(guidance.contains("- Current value: 7"));
        assert!(guidance.contains("- Minimum: 1"));
        assert!(guidance.contains("- Maximum: 10"));
        assert!(guidance.contains("#### `mode`"));
        assert!(guidance.contains("- Required: `true`"));
        assert!(guidance.contains("- Default: required"));
        assert!(guidance.contains("- Current value: \"strict\""));
        assert!(guidance.contains("- Choices: [\"strict\", \"lenient\"]"));
        assert!(guidance.contains("- Minimum items: 1"));
        assert!(guidance.contains("class CustomRuleTestCase"));
        assert!(guidance.contains("test_case=RuleCase("));
        assert!(guidance.contains("When FFT413 is active"));
        assert!(guidance.contains("Configure concrete `rule_modules`"));
        assert!(guidance.contains("sibling `_helpers/`"));
        assert!(guidance.contains("does not mean helpers belong beneath `rules/`"));
        assert!(!guidance.contains("test_case: RuleCase"));
        let rule_path = repository.path().join("rules/custom.py");
        let rule_source = fs::read(&rule_path).expect("custom rule source");
        write(
            &rule_path,
            text(&rule_source).replace("default=3", "default=4"),
        );
        let stale = native_with_python(
            repository.path(),
            &["--target", "agents", "--check"],
            &wrapper,
        );
        assert_eq!(stale.status.code(), Some(1));
        assert!(text(&stale.stdout).contains("stale"));
        assert_eq!(fs::read(&count).expect("host count after check"), b"xx");
        write(&rule_path, rule_source);
        let inspected = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["rule", "XSK001", "--color", "never"])
            .current_dir(repository.path())
            .env("FENSU_PYTHON", &wrapper)
            .output()
            .expect("native custom-rule inspection");
        assert_eq!(inspected.status.code(), Some(test_case.expected_exit_code));
        assert!(text(&inspected.stdout).contains("XSK001 always"));
        assert!(text(&inspected.stdout).contains("Kind: custom"));
        assert!(text(&inspected.stdout).contains("Source:"));
        assert!(text(&inspected.stdout).contains("rules/custom.py"));
        assert!(text(&inspected.stdout).contains("Default: 3"));
        assert!(text(&inspected.stdout).contains("Current value: 7"));
        assert!(text(&inspected.stdout).contains("Default: required"));
        assert!(text(&inspected.stdout).contains("Current value: \"strict\""));
        assert_eq!(fs::read(&count).expect("host count after rule"), b"xxx");

        let unavailable = tempfile::tempdir().expect("unavailable-host project");
        write(
            unavailable.path().join("fensu.toml"),
            fs::read(repository.path().join("fensu.toml")).expect("config"),
        );
        write(
            unavailable.path().join("src/pkg/target.py"),
            b"VALUE: int = 1\n",
        );
        write(
            unavailable.path().join("rules/custom.py"),
            fs::read(repository.path().join("rules/custom.py")).expect("rule"),
        );
        let failed = native(unavailable.path(), &["--target", "agents"]);
        assert_eq!(failed.status.code(), Some(2));
        assert!(text(&failed.stderr).contains("Could not launch Fensu's custom-rule metadata host"));
        assert!(!unavailable.path().join(".agents").exists());

        let incompatible = repository.path().join("incompatible-host");
        write(
            &incompatible,
            b"#!/bin/sh\nprintf '{\"protocol\":1,\"package_version\":\"0\",\"catalogue\":[],\"blocking\":[],\"warnings\":[],\"ignored\":[]}\\n'\n",
        );
        fs::set_permissions(&incompatible, fs::Permissions::from_mode(0o755))
            .expect("incompatible host mode");
        fs::remove_dir_all(repository.path().join(".agents")).expect("remove first installation");
        let failed = native_with_python(repository.path(), &["--target", "agents"], &incompatible);
        assert_eq!(failed.status.code(), Some(2));
        assert!(
            text(&failed.stderr).contains("Incompatible custom-rule metadata protocol"),
            "stderr: {}",
            text(&failed.stderr)
        );
        assert!(!repository.path().join(".agents").exists());
    }
}

#[test]
fn given_global_legacy_init_and_core_flows_when_running_then_they_remain_native() {
    let test_cases = [SkillsCommandTestCase {
        description: "global update, legacy migration, init skills, and core freshness stay native",
        expected_exit_code: 0,
    }];
    for test_case in test_cases {
        let global = project();
        let home = global.path().join("home");
        let update = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["skills", "--global", "--target", "agents"])
            .current_dir(global.path())
            .env("HOME", &home)
            .env("FENSU_PYTHON", global.path().join("missing-python"))
            .output()
            .expect("global native update");
        assert_eq!(
            update.status.code(),
            Some(test_case.expected_exit_code),
            "{}: {}",
            test_case.description,
            text(&update.stderr)
        );
        assert!(target(&home, ".agents", "fensu-fixture").is_file());

        let legacy = project();
        let legacy_document = legacy.path().join(".agents/skills/fensu/SKILL.md");
        write(
            &legacy_document,
            b"<!-- generated-by: fensu skills -->\nlegacy\n",
        );
        write(
            legacy.path().join(".agents/skills/fensu/user.txt"),
            b"preserve\n",
        );
        let migrated = native(legacy.path(), &["--target", "agents"]);
        assert_eq!(
            migrated.status.code(),
            Some(0),
            "{}",
            text(&migrated.stderr)
        );
        assert!(!legacy_document.exists());
        assert_eq!(
            fs::read(legacy.path().join(".agents/skills/fensu/user.txt")).expect("legacy sibling"),
            b"preserve\n"
        );

        let initialized = tempfile::tempdir().expect("empty init repository");
        let init = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["init", "--yes", "--name", "native_app"])
            .current_dir(initialized.path())
            .env("FENSU_PYTHON", initialized.path().join("missing-python"))
            .output()
            .expect("native init skills");
        assert_eq!(init.status.code(), Some(0), "{}", text(&init.stderr));
        for agent in [".agents", ".claude", ".opencode"] {
            let initialized_skills = fs::read_dir(initialized.path().join(agent).join("skills"))
                .expect("initialized skills")
                .collect::<Result<Vec<_>, _>>()
                .expect("initialized skill entries");
            assert_eq!(initialized_skills.len(), 1);
            assert!(initialized_skills[0].path().join("SKILL.md").is_file());
        }

        let check_project = project();
        let installed = native(check_project.path(), &["--target", "agents"]);
        assert_eq!(installed.status.code(), Some(0));
        write(
            check_project.path().join("fensu.toml"),
            CONFIG.replace("memory = true", "memory = false"),
        );
        let check = Command::new(env!("CARGO_BIN_EXE_fensu"))
            .args(["check", "--no-cache", "--no-color"])
            .current_dir(check_project.path())
            .env("FENSU_PYTHON", check_project.path().join("missing-python"))
            .output()
            .expect("native core check");
        assert_eq!(check.status.code(), Some(0), "{}", text(&check.stderr));
        assert!(text(&check.stderr).contains("Fensu skill files are out of date"));
    }
}
