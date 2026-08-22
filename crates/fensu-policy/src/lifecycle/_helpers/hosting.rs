//! Isolated process transport for custom-rule hosts.

use std::io::{Read, Write};
use std::path::Path;
use std::process::{Command, Output, Stdio};
use std::sync::mpsc;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::thread;
use std::time::{Duration, Instant};

use command_group::CommandGroup;

use crate::lifecycle::constants::CUSTOM_HOST_CLEANUP_MILLIS;
use crate::lifecycle::errors::LifecycleError;

type StdinReceiver = mpsc::Receiver<std::io::Result<()>>;
type OutputReceiver = mpsc::Receiver<std::io::Result<Vec<u8>>>;

struct HostChannels {
    stdin: StdinReceiver,
    stdout: OutputReceiver,
    stderr: OutputReceiver,
}

struct HostWorkers {
    stdin: Arc<AtomicBool>,
    stdout: Arc<AtomicBool>,
    stderr: Arc<AtomicBool>,
}

impl HostWorkers {
    fn completed(&self) -> bool {
        self.stdin.load(Ordering::Acquire)
            && self.stdout.load(Ordering::Acquire)
            && self.stderr.load(Ordering::Acquire)
    }
}

struct HostStreams {
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    stdin: std::io::Result<()>,
}

pub(crate) fn exchange(
    program: &Path,
    arguments: &[String],
    input: &[u8],
    timeout: Duration,
) -> Result<Output, LifecycleError> {
    let deadline = Instant::now().checked_add(timeout).ok_or_else(|| {
        LifecycleError::InvalidConfiguration {
            message: "custom host timeout is too large".to_owned(),
        }
    })?;
    let mut command = Command::new(program);
    command
        .args(arguments)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command.group_spawn().map_err(launch_error)?;
    let stdin = child
        .inner()
        .stdin
        .take()
        .ok_or_else(|| LifecycleError::HostLaunch {
            message: "custom host stdin was unavailable".to_owned(),
        })?;
    let stdout = child
        .inner()
        .stdout
        .take()
        .ok_or_else(|| LifecycleError::HostLaunch {
            message: "custom host stdout was unavailable".to_owned(),
        })?;
    let stderr = child
        .inner()
        .stderr
        .take()
        .ok_or_else(|| LifecycleError::HostLaunch {
            message: "custom host stderr was unavailable".to_owned(),
        })?;
    let input = input.to_vec();
    let (stdin_sender, stdin_receiver) = mpsc::channel();
    let stdin_complete = Arc::new(AtomicBool::new(false));
    let stdin_worker_complete = Arc::clone(&stdin_complete);
    thread::spawn(move || {
        let mut stdin = stdin;
        let result = stdin
            .write_all(&input)
            .and_then(|()| stdin.write_all(b"\n"));
        drop(stdin);
        drop(input);
        stdin_worker_complete.store(true, Ordering::Release);
        let _ = stdin_sender.send(result);
    });
    let (stdout_receiver, stdout_complete) = read_pipe(stdout);
    let (stderr_receiver, stderr_complete) = read_pipe(stderr);
    let workers = HostWorkers {
        stdin: stdin_complete,
        stdout: stdout_complete,
        stderr: stderr_complete,
    };
    let channels = HostChannels {
        stdin: stdin_receiver,
        stdout: stdout_receiver,
        stderr: stderr_receiver,
    };
    let status = loop {
        match child.try_wait() {
            Err(error) => {
                drop(channels);
                terminate_and_cleanup(child, workers)?;
                return Err(launch_error(error));
            }
            Ok(Some(status)) => break status,
            Ok(None) if Instant::now() >= deadline => {
                drop(channels);
                terminate_and_cleanup(child, workers)?;
                return Err(timeout_error(timeout));
            }
            Ok(None) => thread::sleep(Duration::from_millis(10)),
        }
    };
    let streams = collect_streams(channels, deadline, timeout);
    let HostStreams {
        stdout,
        stderr,
        stdin: stdin_result,
    } = match streams {
        Ok(value) => value,
        Err(error) => {
            terminate_and_cleanup(child, workers)?;
            return Err(error);
        }
    };
    if status.success() {
        stdin_result.map_err(launch_error)?;
    }
    Ok(Output {
        status,
        stdout,
        stderr,
    })
}

fn read_pipe<Reader: Read + Send + 'static>(
    mut reader: Reader,
) -> (mpsc::Receiver<std::io::Result<Vec<u8>>>, Arc<AtomicBool>) {
    let (sender, receiver) = mpsc::channel();
    let complete = Arc::new(AtomicBool::new(false));
    let worker_complete = Arc::clone(&complete);
    thread::spawn(move || {
        let mut output: Vec<u8> = Vec::new();
        let result = reader.read_to_end(&mut output).map(|_| output);
        drop(reader);
        worker_complete.store(true, Ordering::Release);
        let _ = sender.send(result);
    });
    (receiver, complete)
}

fn collect_streams(
    channels: HostChannels,
    deadline: Instant,
    timeout: Duration,
) -> Result<HostStreams, LifecycleError> {
    let stdout = receive_before(channels.stdout, deadline, timeout)?;
    let stderr = receive_before(channels.stderr, deadline, timeout)?;
    let stdin = receive_result_before(channels.stdin, deadline, timeout)?;
    Ok(HostStreams {
        stdout,
        stderr,
        stdin,
    })
}

fn receive_before<T>(
    receiver: mpsc::Receiver<std::io::Result<T>>,
    deadline: Instant,
    timeout: Duration,
) -> Result<T, LifecycleError> {
    let remaining = deadline.saturating_duration_since(Instant::now());
    match receiver.recv_timeout(remaining) {
        Ok(Ok(value)) => Ok(value),
        Ok(Err(error)) => Err(launch_error(error)),
        Err(mpsc::RecvTimeoutError::Timeout) => Err(timeout_error(timeout)),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err(disconnected_worker_error()),
    }
}

fn receive_result_before<T>(
    receiver: mpsc::Receiver<std::io::Result<T>>,
    deadline: Instant,
    timeout: Duration,
) -> Result<std::io::Result<T>, LifecycleError> {
    let remaining = deadline.saturating_duration_since(Instant::now());
    match receiver.recv_timeout(remaining) {
        Ok(value) => Ok(value),
        Err(mpsc::RecvTimeoutError::Timeout) => Err(timeout_error(timeout)),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err(disconnected_worker_error()),
    }
}

fn disconnected_worker_error() -> LifecycleError {
    LifecycleError::HostFailure {
        message: "custom host I/O worker stopped without a result".to_owned(),
    }
}

fn terminate_and_cleanup(
    child: command_group::GroupChild,
    workers: HostWorkers,
) -> Result<(), LifecycleError> {
    let cleanup = Duration::from_millis(CUSTOM_HOST_CLEANUP_MILLIS);
    let deadline =
        Instant::now()
            .checked_add(cleanup)
            .ok_or_else(|| LifecycleError::HostFailure {
                message: "could not establish custom host cleanup deadline".to_owned(),
            })?;
    let mut child = terminate_group(child)?;
    let (reap_sender, reap_receiver) = mpsc::channel();
    thread::spawn(move || {
        let result = child.wait();
        let _ = reap_sender.send(result);
    });
    while !workers.completed() {
        if Instant::now() >= deadline {
            return Err(cleanup_timeout_error());
        }
        thread::sleep(Duration::from_millis(10));
    }
    let remaining = deadline.saturating_duration_since(Instant::now());
    match reap_receiver.recv_timeout(remaining) {
        Ok(Ok(_)) => Ok(()),
        Ok(Err(error)) => Err(LifecycleError::HostFailure {
            message: format!("could not reap custom host process group: {error}"),
        }),
        Err(_) => Err(cleanup_timeout_error()),
    }
}

fn cleanup_timeout_error() -> LifecycleError {
    LifecycleError::HostFailure {
        message: format!(
            "custom host process group did not terminate within {CUSTOM_HOST_CLEANUP_MILLIS}ms"
        ),
    }
}

fn terminate_group(
    mut child: command_group::GroupChild,
) -> Result<command_group::GroupChild, LifecycleError> {
    match child.kill() {
        Ok(()) => Ok(child),
        Err(kill_error) => match child.try_wait() {
            Ok(Some(_)) => Ok(child),
            _ => Err(LifecycleError::HostFailure {
                message: format!("could not terminate custom host process group: {kill_error}"),
            }),
        },
    }
}

fn timeout_error(timeout: Duration) -> LifecycleError {
    LifecycleError::HostTimeout {
        timeout_millis: u64::try_from(timeout.as_millis()).unwrap_or(u64::MAX),
    }
}

fn launch_error(error: std::io::Error) -> LifecycleError {
    LifecycleError::HostLaunch {
        message: error.to_string(),
    }
}
