import time

from sqlalchemy import create_engine, text


def wait_for_startup(database_url):
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            break
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(0.5)
