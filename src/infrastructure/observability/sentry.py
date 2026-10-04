import os

import sentry_sdk


def setup_sentry() -> None:
    dsn = os.environ.get("SENTRY_DSN") or None
    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
