import sqlite3

import psycopg

ConnectionType = psycopg.Connection | sqlite3.Connection


def is_postgresql(conn: ConnectionType) -> bool:
    return not isinstance(conn, sqlite3.Connection)
