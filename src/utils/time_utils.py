from datetime import datetime, timezone  # utcnow yerine timezone ekledik


def get_utc_now():
    return datetime.now(timezone.utc)
