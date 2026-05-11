"""
percentiles.py — position mapping, peer group filtering, percentile computation.

Public functions:
  map_position(fbref_pos_string) -> str
      Maps a raw FBref position string (e.g. "RB", "CB,RB") to a position bucket
      (CB | FB | DM | CM | AM | W | CF). Uses the primary position (first listed).

  get_position_profile(position_bucket) -> PositionProfile
      Returns the ordered, category-grouped metric list for the given position bucket.
      Source of truth: .claude/shared-references/metrics/position-matrix.md (hardcoded here).

  compute_percentiles(player_stats, league_stats_list, position_bucket, min_minutes=900)
      -> list[MetricResult]
      1. Filters league_stats_list to peers with same position bucket and >= min_minutes
      2. Computes raw metric values for player and all peers via metrics.compute_metric_values
      3. Computes percentile rank for each metric via scipy.stats.percentileofscore(kind="rank")
      4. Returns list of MetricResult objects in profile order

See .claude/shared-references/metrics/position-matrix.md for the hardcoded mapping tables.
"""

# Implementation: hardcode POSITION_MAP and POSITION_MATRIX dicts from position-matrix.md.
# Use scipy.stats.percentileofscore with kind="rank". Clamp result to 0–99 (int).
