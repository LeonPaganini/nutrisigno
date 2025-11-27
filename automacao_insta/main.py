"""CLI orchestrator for NutriSigno automation."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, time

from .config import load_config
from .db import init_db
from .generate_calendar import generate_calendar, persist_calendar
from .generate_posts import generate_all_pending_posts
from .validate_posts import validate_all_pending_posts
from .render_images import render_all_validated_posts
from .schedule_queue import schedule_posts_for_range
from .post_instagram import publish_due_posts

LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="NutriSigno Instagram automation CLI")
    subparsers = parser.add_subparsers(dest="command")

    calendar_parser = subparsers.add_parser("generate-calendar", help="Generate editorial calendar")
    calendar_parser.add_argument("--days", type=int, default=7, help="Days ahead to generate")

    subparsers.add_parser("generate-posts", help="Generate text for drafts")
    subparsers.add_parser("validate-posts", help="Validate generated posts")
    subparsers.add_parser("render-images", help="Render images for validated posts")

    schedule_parser = subparsers.add_parser("schedule-posts", help="Schedule renderized posts")
    schedule_parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    schedule_parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    schedule_parser.add_argument("--hour", type=int, default=9, help="Hour of publication")

    subparsers.add_parser("publish-due", help="Publish posts due now")

    args = parser.parse_args()
    config = load_config()
    init_db(config)

    if args.command == "generate-calendar":
        entries = generate_calendar(args.days)
        persist_calendar(entries, config)
    elif args.command == "generate-posts":
        generate_all_pending_posts(config=config)
    elif args.command == "validate-posts":
        validate_all_pending_posts(config=config)
    elif args.command == "render-images":
        render_all_validated_posts(config=config)
    elif args.command == "schedule-posts":
        publish_time = time(hour=args.hour, minute=0)
        schedule_posts_for_range(args.start, args.end, publish_time=publish_time, config=config)
    elif args.command == "publish-due":
        publish_due_posts(config=config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
