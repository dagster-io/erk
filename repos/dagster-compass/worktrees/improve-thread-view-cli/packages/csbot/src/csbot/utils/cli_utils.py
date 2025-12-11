from contextlib import contextmanager

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine

from csbot.utils.datadog import initialize_datadog
from csbot.utils.logging import configure_loggers


def preload_sqlalchemy_plugins():
    engine = create_engine("duckdb:///:memory:")
    engine.dispose()


@contextmanager
def cli_context():
    load_dotenv(find_dotenv(usecwd=True), override=True)
    initialize_datadog()
    configure_loggers()
    preload_sqlalchemy_plugins()
    yield
