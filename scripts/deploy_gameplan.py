"""
Gameplan deployment script — validates and notifies.

Usage:
    poetry run python scripts/deploy_gameplan.py [--gameplan PATH]

Reads the daily gameplan JSON, validates it against the Crucible schema,
and fires a Discord confirmation webhook.  Intended to be run each morning
after the Morning Gauntlet verdict is recorded and before the market open.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Allow running from the project root without a full package install
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.gameplan import GameplanLoader
from src.notifications.discord import DiscordNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_GAMEPLAN_PATH = Path("data/daily_gameplan.json")
DEFAULT_SCHEMA_PATH = Path("schemas/daily_gameplan_schema.json")


def build_discord_message(gameplan: dict[str, Any]) -> str:
    """
    Build the human-readable Discord confirmation message.

    Args:
        gameplan: Validated gameplan dictionary.

    Returns:
        Formatted message string for Discord embed.
    """
    date = gameplan.get("date", "unknown")
    strategy = gameplan.get("strategy", "?")
    regime = gameplan.get("regime", "unknown")
    vix = gameplan.get("vix_at_analysis")
    bias = gameplan.get("bias", "unknown")
    geo_risk = gameplan.get("geo_risk", "unknown")
    alert = gameplan.get("alert_message", "")
    session_id = gameplan.get("session_id", "")

    vix_str = f"{vix:.2f}" if vix is not None else "N/A"

    lines = [
        f"**Strategy {strategy} deployed — {date}**",
        f"Session: `{session_id}`",
        f"Regime: **{regime}** | VIX: **{vix_str}** | Bias: {bias} | Geo-risk: {geo_risk}",
    ]

    if strategy == "C":
        lines.append("**Mode: CASH PRESERVATION — no new entries today**")

    if alert:
        lines.append(f"\n> {alert}")

    hard_limits = gameplan.get("hard_limits", {})
    if hard_limits:
        pdt = hard_limits.get("pdt_trades_remaining", "?")
        gov = hard_limits.get("weekly_drawdown_governor_active", False)
        lines.append(f"\nPDT remaining: {pdt} | Weekly governor: {'ACTIVE' if gov else 'off'}")

    return "\n".join(lines)


def main() -> int:
    """
    Deploy daily gameplan: validate, log, and notify Discord.

    Returns:
        0 on success, 1 on validation failure.
    """
    parser = argparse.ArgumentParser(description="Deploy daily trading gameplan")
    parser.add_argument(
        "--gameplan",
        type=Path,
        default=DEFAULT_GAMEPLAN_PATH,
        help="Path to daily_gameplan.json (default: data/daily_gameplan.json)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to JSON schema (default: schemas/daily_gameplan_schema.json)",
    )
    args = parser.parse_args()

    gameplan_path: Path = args.gameplan
    schema_path: Path = args.schema

    logger.info("=" * 60)
    logger.info("Charter & Stone Capital — Gameplan Deployment")
    logger.info("=" * 60)
    logger.info("Gameplan path : %s", gameplan_path.resolve())
    logger.info("Schema path   : %s", schema_path.resolve())

    # ── Validate gameplan ────────────────────────────────────────────────────
    loader = GameplanLoader(schema_path=schema_path)
    gameplan = loader.load(gameplan_path)

    if gameplan.get("_default_reason"):
        logger.error(
            "Gameplan validation FAILED — fell back to Strategy C default. Reason: %s",
            gameplan["_default_reason"],
        )
        logger.error("Fix data/daily_gameplan.json before resuming operations.")
        return 1

    strategy = gameplan.get("strategy", "?")
    date = gameplan.get("date", "unknown")
    logger.info("Gameplan loaded cleanly: Strategy %s | Date %s", strategy, date)

    # Echo key fields to stdout for logging/audit
    logger.info("  regime              : %s", gameplan.get("regime"))
    logger.info("  symbols             : %s", gameplan.get("symbols"))
    logger.info("  position_size_mult  : %s", gameplan.get("position_size_multiplier"))
    logger.info("  vix_at_analysis     : %s", gameplan.get("vix_at_analysis"))
    logger.info("  bias                : %s", gameplan.get("bias"))
    logger.info("  geo_risk            : %s", gameplan.get("geo_risk"))
    logger.info(
        "  pdt_trades_remaining: %s", gameplan.get("hard_limits", {}).get("pdt_trades_remaining")
    )
    logger.info(
        "  weekly_gov_active   : %s",
        gameplan.get("hard_limits", {}).get("weekly_drawdown_governor_active"),
    )

    # ── Discord notification ─────────────────────────────────────────────────
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        # Fall back to docker .env if main .env is not populated
        docker_env = Path("docker/.env")
        if docker_env.exists():
            for line in docker_env.read_text().splitlines():
                if line.startswith("DISCORD_WEBHOOK_URL="):
                    webhook_url = line.split("=", 1)[1].strip()
                    break

    notifier = DiscordNotifier(webhook_url=webhook_url)
    message = build_discord_message(gameplan)
    sent = notifier.send_info(message)

    if sent:
        logger.info("Discord notification sent successfully.")
    else:
        logger.warning("Discord notification NOT sent (webhook not configured or unreachable).")

    logger.info("=" * 60)
    logger.info("Deployment complete — Strategy %s active for %s", strategy, date)
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
