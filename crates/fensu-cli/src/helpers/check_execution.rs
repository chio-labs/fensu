use std::env;
use std::fs;
use std::io::{self, IsTerminal};
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use walkdir::WalkDir;

use crate::configuration::main::load;
use crate::helpers::cache;
use crate::helpers::check_evaluation::evaluate_and_render;
use crate::helpers::check_policy::{
    check_identity, hex_digest, path_matches, python_version, validate_package_names,
};
use crate::models::{CachedOutput, CheckOptions, CliOutput, Config, ScopedSource};
use crate::skills::main::core_freshness;

const CHECK_HELP: &str = "usage: fensu check [-h] [--no-color] [--warn] [--cache | --no-cache] [--cache-stats] [--jobs JOBS] [paths ...]\n";

pub(crate) fn execute_check(arguments: &[String]) -> Result<CliOutput, String> {
    if arguments
        .iter()
        .any(|argument| matches!(argument.as_str(), "--help" | "-h"))
    {
        return Ok(CliOutput::success(CHECK_HELP.to_owned()));
    }
    let options = parse_options(arguments)?;
    let mut stderr = String::new();
    let invocation = env::current_dir()
        .map_err(|error| error.to_string())?
        .canonicalize()
        .map_err(|error| error.to_string())?;
    let (config_path, mut config) = load::load(&invocation)?;
    let _memory_enabled = config.memory_enabled;
    let root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?
        .canonicalize()
        .map_err(|error| error.to_string())?;
    if !options.paths.is_empty() {
        config.roots = options
            .paths
            .iter()
            .map(|path| {
                invocation
                    .join(path)
                    .canonicalize()
                    .map_err(|error| error.to_string())?
                    .strip_prefix(&root)
                    .map_err(|error| error.to_string())
                    .map(|path| path.to_string_lossy().replace('\\', "/"))
            })
            .collect::<Result<Vec<_>, String>>()?;
    }
    validate_package_names(&root, &config)?;
    let discovered = discover(&root, &config)?;
    let (mut sources, excluded) = select_sources(discovered, &config);
    let cache_enabled = options.cache_enabled.unwrap_or(config.cache_enabled);
    let color =
        !options.no_color && env::var_os("NO_COLOR").is_none() && io::stdout().is_terminal();
    let identity = check_identity(&root, &config, &sources, options.warn);
    if cache_enabled {
        if let Some(cached) = cache::read(&root, &identity, &sources, color) {
            if options.cache_stats {
                stderr.push_str(&format!(
                    "Cache: hits={} misses=0 invalidations=0 writes=0 non_cacheable=0\n",
                    sources.len()
                ));
            }
            stderr.push_str(&core_freshness::core_freshness(&invocation).unwrap_or_default());
            return Ok(CliOutput {
                stdout: cached.output,
                stderr,
                exit_code: cached.exit_code,
            });
        }
    }
    parse_sources(&mut sources)?;
    let (output, exit_code) =
        evaluate_and_render(&root, &config, &sources, excluded, options.warn, color)?;
    stderr.push_str(&core_freshness::core_freshness(&invocation).unwrap_or_default());
    if cache_enabled {
        let cached = CachedOutput {
            identity,
            output: output.clone(),
            exit_code,
            file_count: sources.len(),
        };
        if !cache::write(&root, &cached, &sources, color) {
            stderr.push_str("Cache disabled for this run: cache publication failed\n");
        } else if options.cache_stats {
            stderr.push_str(&format!(
                "Cache: hits=0 misses={} invalidations=0 writes={} non_cacheable=0\n",
                sources.len(),
                sources.len()
            ));
        }
    }
    Ok(CliOutput {
        stdout: output,
        stderr,
        exit_code,
    })
}

fn parse_options(arguments: &[String]) -> Result<CheckOptions, String> {
    let mut options = CheckOptions {
        no_color: false,
        warn: false,
        cache_enabled: None,
        cache_stats: false,
        paths: Vec::new(),
    };
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--no-color" => options.no_color = true,
            "--warn" => options.warn = true,
            "--cache" => options.cache_enabled = Some(true),
            "--no-cache" => options.cache_enabled = Some(false),
            "--cache-stats" => options.cache_stats = true,
            "--jobs" => {
                index += 1;
                let jobs = arguments
                    .get(index)
                    .ok_or_else(|| "argument --jobs: expected one argument".to_owned())?;
                if jobs
                    .parse::<usize>()
                    .ok()
                    .filter(|jobs| *jobs > 0)
                    .is_none()
                {
                    return Err("argument --jobs: jobs must be at least 1".to_owned());
                }
            }
            argument if argument.starts_with('-') => {
                return Err(format!("unrecognized arguments: {argument}"));
            }
            path => options.paths.push(path.to_owned()),
        }
        index += 1;
    }
    Ok(options)
}

fn discover(root: &Path, config: &Config) -> Result<Vec<ScopedSource>, String> {
    let mut sources = Vec::new();
    for (scope, configured_root) in config
        .roots
        .iter()
        .map(|path| ("root", path))
        .chain(config.tests.iter().map(|path| ("test", path)))
        .chain(config.tooling.iter().map(|path| ("tooling", path)))
    {
        let source_root = root.join(configured_root);
        if !source_root.exists() {
            continue;
        }
        for entry in WalkDir::new(&source_root)
            .into_iter()
            .filter_map(Result::ok)
        {
            if !entry.file_type().is_file()
                || entry.path().extension().and_then(|value| value.to_str()) != Some("py")
            {
                continue;
            }
            let path = entry.path().to_path_buf();
            let content = fs::read(&path).map_err(|error| error.to_string())?;
            let repository_path = path
                .strip_prefix(root)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let relative_parts = path
                .strip_prefix(&source_root)
                .map_err(|error| error.to_string())?
                .components()
                .map(|part| part.as_os_str().to_string_lossy().into_owned())
                .collect();
            sources.push(ScopedSource {
                path,
                repository_path,
                root: source_root.clone(),
                root_text: configured_root.clone(),
                scope: scope.to_owned(),
                relative_parts,
                fingerprint: hex_digest(&content),
                content,
                program: None,
            });
        }
    }
    sources.sort_by(|left, right| {
        left.repository_path
            .cmp(&right.repository_path)
            .then_with(|| {
                right
                    .root
                    .components()
                    .count()
                    .cmp(&left.root.components().count())
            })
    });
    sources.dedup_by(|left, right| left.repository_path == right.repository_path);
    Ok(sources)
}

fn parse_sources(sources: &mut [ScopedSource]) -> Result<(), String> {
    let parsed = ProgramHandle::parse_many(
        sources
            .iter()
            .map(|source| String::from_utf8_lossy(&source.content).into_owned())
            .collect(),
        python_version(),
    );
    for (source, program) in sources.iter_mut().zip(parsed) {
        source.program =
            Some(program.ok_or_else(|| {
                format!("Could not parse Python source: {}", source.repository_path)
            })?);
    }
    Ok(())
}

fn select_sources(sources: Vec<ScopedSource>, config: &Config) -> (Vec<ScopedSource>, usize) {
    let discovered = sources.len();
    let selected = sources
        .into_iter()
        .filter(|source| {
            (config.evaluation_include.is_empty()
                || config
                    .evaluation_include
                    .iter()
                    .any(|pattern| path_matches(&source.repository_path, pattern)))
                && !config
                    .evaluation_exclude
                    .iter()
                    .any(|pattern| path_matches(&source.repository_path, pattern))
        })
        .collect::<Vec<_>>();
    let excluded = discovered - selected.len();
    (selected, excluded)
}
