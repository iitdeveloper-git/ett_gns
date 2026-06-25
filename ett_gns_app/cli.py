from __future__ import annotations

import argparse
import logging
import time

from ett_gns_app.tasks import publish_outbox, reconcile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gns.cli")


def run_outbox(interval_seconds: float) -> None:
    while True:
        try:
            published = publish_outbox.run()
            if published:
                logger.info("Published %s outbox events", published)
        except Exception:
            logger.exception("Outbox publication cycle failed")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["outbox", "reconcile"])
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.service == "outbox":
        run_outbox(args.interval)
    else:
        print(reconcile.run())


if __name__ == "__main__":
    main()
