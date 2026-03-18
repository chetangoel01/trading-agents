"""CLI entrypoint for single/continuous/backtest modes."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from config import RUN_MODE, WATCHLIST, validate_config
from state import FeedbackState, PortfolioSnapshot, RunMetadata
from utils.logger import get_logger


def bootstrap_metadata(trigger: str = "manual") -> RunMetadata:
    return RunMetadata(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(UTC),
        tickers=WATCHLIST,
        trigger=trigger,
        run_mode=RUN_MODE,
    )


def main() -> None:
    validate_config()
    logger = get_logger("main")
    metadata = bootstrap_metadata()
    logger.info(
        "bootstrap_complete",
        extra={
            "extra": {
                "run_id": metadata.run_id,
                "run_mode": RUN_MODE,
                "tickers": WATCHLIST,
                "portfolio_seed": PortfolioSnapshot().model_dump(),
                "feedback_seed": FeedbackState().model_dump(),
            }
        },
    )


if __name__ == "__main__":
    main()
