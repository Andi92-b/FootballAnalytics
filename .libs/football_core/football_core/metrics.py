"""
metrics.py — metric formula implementations.

One function per metric. Each function takes a flat player stat dict
(keyed "<table>.<column>") and returns a float raw value.

Public functions:
  compute_metric_values(player_stats, metric_names) -> dict[str, float]
      Iterates over the requested metric names, calls the corresponding
      formula function, and returns a dict of { metric_name: raw_value }.

Metric formula functions (one per metric from metric-definitions.md):
  front_foot_defending(stats) -> float
  tackle_success(stats) -> float
  back_foot_defending(stats) -> float
  loose_ball_recoveries(stats) -> float
  aerial_volume(stats) -> float
  aerial_success(stats) -> float
  one_v_one_defending(stats) -> float
  link_up_play(stats) -> float
  ball_retention(stats) -> float
  launched_passes(stats) -> float
  creative_threat(stats) -> float
  cross_volume(stats) -> float
  dribble_volume(stats) -> float
  pass_progression(stats) -> float
  carry_progression(stats) -> float
  progressive_receptions(stats) -> float
  goal_threat(stats) -> float
  shot_frequency(stats) -> float
  box_threat(stats) -> float
  shot_quality(stats) -> float

See .claude/shared-references/metrics/metric-definitions.md for all formulae.
Do not deviate from those formulae.
"""

# Implementation: one function per metric listed above. Handle ZeroDivisionError
# (return 0.0 when denominators are zero). Possession-adjusted metrics use
# stats["standard.team_poss"] as the team possession decimal.
