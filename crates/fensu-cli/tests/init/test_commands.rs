use crate::helpers;
use crate::test_types::InitScenarioTestCase;

#[test]
fn given_sveltekit_only_repository_when_initializing_then_writes_explicit_web_target() {
    let test_cases = [InitScenarioTestCase {
        description: "SvelteKit-only initialization",
        expected_success: true,
        run: helpers::sveltekit_only_repository_writes_explicit_web_target,
    }];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[test]
fn given_incomplete_evidence_when_initializing_then_detection_is_conservative() {
    let test_cases = [
        InitScenarioTestCase {
            description: "generic Node and incomplete Svelte evidence",
            expected_success: true,
            run: helpers::generic_node_and_incomplete_svelte_evidence_do_not_detect_target,
        },
        InitScenarioTestCase {
            description: "Svelte config without Kit dependency",
            expected_success: true,
            run: helpers::svelte_config_without_kit_dependency_does_not_detect_target,
        },
    ];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[test]
fn given_mixed_repository_when_initializing_then_names_and_exclusions_are_deterministic() {
    let test_cases = [
        InitScenarioTestCase {
            description: "mixed target name disambiguation",
            expected_success: true,
            run: helpers::mixed_repository_with_colliding_web_names_is_deterministic,
        },
        InitScenarioTestCase {
            description: "detected target exclusion",
            expected_success: true,
            run: helpers::detected_target_exclusion_keeps_remaining_targets,
        },
    ];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[test]
fn given_explicit_setup_when_initializing_then_presets_and_addition_are_safe() {
    let test_cases = [
        InitScenarioTestCase {
            description: "empty SvelteKit preset",
            expected_success: true,
            run: helpers::empty_sveltekit_preset_runs_without_external_runtime,
        },
        InitScenarioTestCase {
            description: "safe explicit target addition",
            expected_success: true,
            run: helpers::explicit_config_addition_preserves_comments_and_refuses_unsafe_cases,
        },
    ];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[test]
fn given_artifact_and_example_names_when_initializing_then_exclusions_are_analyzer_specific() {
    let test_cases = [
        InitScenarioTestCase {
            description: "Python coverage package",
            expected_success: true,
            run: helpers::python_coverage_package_is_detected,
        },
        InitScenarioTestCase {
            description: "invalid Kit versions and demo auto-exclusion",
            expected_success: true,
            run: helpers::invalid_kit_versions_and_demo_trees_stay_excluded,
        },
        InitScenarioTestCase {
            description: "explicit Python example root",
            expected_success: true,
            run: helpers::explicit_python_example_root_is_available,
        },
        InitScenarioTestCase {
            description: "SvelteKit demo preset recovery",
            expected_success: true,
            run: helpers::intentional_demo_sveltekit_is_recoverable_with_preset,
        },
    ];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[test]
fn given_existing_pyproject_when_initializing_then_manual_action_is_accurate() {
    let test_cases = [InitScenarioTestCase {
        description: "pyproject target options",
        expected_success: true,
        run: helpers::pyproject_target_options_require_manual_edit,
    }];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}

#[cfg(unix)]
#[test]
fn given_symlinks_and_concurrent_changes_when_writing_then_operations_fail_closed() {
    let test_cases = [
        InitScenarioTestCase {
            description: "symlink confinement",
            expected_success: true,
            run: helpers::symlinked_paths_never_follow_outside_repository,
        },
        InitScenarioTestCase {
            description: "operation lock and editor identity race",
            expected_success: true,
            run: helpers::concurrent_fensu_and_editor_changes_fail_closed,
        },
    ];
    for test_case in &test_cases {
        (test_case.run)();
        assert!(test_case.expected_success, "{}", test_case.description);
    }
}
