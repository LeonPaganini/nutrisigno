"""Schedule publication queue."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional

from .config import AppConfig, load_config
from .db import PostStatus, get_posts_due as db_get_posts_due, get_posts_without_schedule, update_post_status

LOGGER = logging.getLogger(__name__)



def _parse_date(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def schedule_posts_for_range(start_date: date | str, end_date: date | str, publish_time: time = time(hour=9), config: Optional[AppConfig] = None) -> None:
    """Assign planned publication datetime for renderized posts."""

    cfg = config or load_config()
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if end < start:
        raise ValueError("end_date must be after start_date")

    posts = get_posts_without_schedule(config=cfg)
    if not posts:
        LOGGER.info("No posts to schedule")
        return

    current_date = start
    for post in posts:
        if current_date > end:
            LOGGER.info("Reached end of scheduling window")
            break

        publish_dt = datetime.combine(current_date, publish_time)
        update_post_status(
            post["id"],
            PostStatus.AGENDADO,
            config=cfg,
            data_publicacao_planejada=publish_dt.isoformat(),
        )
        LOGGER.info("Scheduled post %s for %s", post["id"], publish_dt.isoformat())

        current_date += timedelta(days=1)



def get_posts_due(now: Optional[datetime] = None, config: Optional[AppConfig] = None) -> list[dict]:
    """Return posts ready for publication."""

    cfg = config or load_config()
    now_iso = (now or datetime.now()).isoformat()
    return db_get_posts_due(now_iso, config=cfg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Schedule posts for publication")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--hour", type=int, default=9, help="Publish hour (0-23)")
    args = parser.parse_args()

    schedule_posts_for_range(args.start, args.end, publish_time=time(hour=args.hour))
