//! Native complete-generation validation and rendered-output replay.

use crate::cache::_helpers::replay::{build_replay_generation, ReplayGenerationRequest};
use crate::cache::models::{CacheMetrics, NativeReplay};

pub(in crate::cache) fn replay_generation(
    request: ReplayGenerationRequest<'_>,
) -> Option<(NativeReplay, CacheMetrics)> {
    build_replay_generation(request)
}
