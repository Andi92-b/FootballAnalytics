/**
 * Short descriptions for each pizza chart metric, sourced from The Athletic's
 * player-style pizza chart glossary (Aug 2025).
 */
export const METRIC_DESCRIPTIONS: Record<string, string> = {
  // ── Defence ─────────────────────────────────────────────────────────────────
  "Front-foot defending":
    "How often a player hunts defensive actions: tackles + challenges + fouls + interceptions + blocked passes per 90, adjusted for team possession.",
  "Tackle success":
    "% of tackles won out of all tackles attempted, challenges attempted and fouls committed.",
  "Back-foot defending":
    "Reactive defensive actions — blocked shots and clearances per 90. Measures a player's last-line contribution to preventing shots and clearing danger.",
  "Ball recovery":
    "How often a player retrieves the ball when neither side has it. Proxy for anticipation and willingness to win loose balls.",
  "Aerial volume":
    "Aerial duels contested per 90 — how often a player competes in the air.",
  "Aerial success":
    "% of aerial duels won out of total aerial duels contested.",
  "One-v-one defending":
    "% of dribble challenges won — how often a player stops a dribbler in a direct 1v1 confrontation. Key indicator of defensive solidity for full-backs and defensive midfielders.",

  // ── Possession ───────────────────────────────────────────────────────────────
  "Link-up play":
    "% of passes that are short or medium — teases out the metronomic ball-players whose job is to keep things ticking over.",
  "Ball retention":
    "Pass completion % — a player's inclination (or tactical instruction) to look after possession.",
  "Launched passes":
    "% of long-distance passes out of total passes — how direct a player is. High = vertical/direct style; Low = short-passing build-up.",

  // ── Progression ──────────────────────────────────────────────────────────────
  "Creative threat":
    "Expected assists (80%) + actual assists (20%) per 90 — accurate view of creative process beyond pure assist outcomes.",
  "Cross volume":
    "Crosses per 90 minutes — delivery output. Identifies players who actively look to serve teammates from wide areas.",
  "Cross accuracy":
    "% of crosses that find a teammate. Separates precision deliverers from those who cross in hope. Combined with Cross volume, reveals both willingness and quality.",
  "Dribble volume":
    "Successful dribbles per 100 touches — accounts for involvement: highlights those who take on opponents regardless of how much they have the ball.",
  "Dribble success":
    "% of dribble attempts completed. Complements Dribble volume: volume shows how often a player tries to beat someone; success shows how good they are at it.",
  "Pass progression":
    "% of passes that reach the final third — how consistently a player drives play into dangerous areas. High = forward-thinking distributor.",
  "Carry progression":
    "Progressive carries as a share of total carries — tendency to drive forward with the ball.",
  "Progressive receptions":
    "Progressive passes received as a share of total receptions — proxy for staying high, ghosting between lines and asking for the ball in advanced areas.",

  // ── Attack ───────────────────────────────────────────────────────────────────
  "Goal threat":
    "Non-penalty xG (70%) + non-penalty goals (30%) per 90 — measures ability to generate and convert chances.",
  "Shot frequency":
    "Shots per 100 touches — separates those with eyes for goal from those who contribute more broadly to their team's attack.",
  "Shot accuracy":
    "% of shots on target — precision of attempts on goal.",
  "Box threat":
    "% of shots taken from inside the penalty box — separates penalty-box strikers from wide finishers and those who shoot from distance.",
  "Shot quality":
    "Average xG per shot — measures ability to get into high-quality positions.",

  // ── Custom / extended ────────────────────────────────────────────────────────
  "Foul drawing":
    "Fouls won per 90 — how often a player draws free kicks, often indicating dribble threat or clever movement.",
  "Runs in behind":
    "xA from runs in behind the defensive line per 90 — proxy for making penetrating runs to threaten the space behind defenders.",
};
