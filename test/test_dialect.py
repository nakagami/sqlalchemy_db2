"""Dialect level tests (cf. sqlalchemy_firebirdsql test/test_dialect.py)."""
import unittest

import sqlalchemy as sa
from sqlalchemy.engine.url import make_url

from .util import SYNC_URL


class ConnectArgsTest(unittest.TestCase):
    def test_create_connect_args(self):
        from sqlalchemy_db2.syn import DB2Dialect_syn

        dialect = DB2Dialect_syn()
        args, kw = dialect.create_connect_args(
            make_url("db2+syn://someone:s3cr3t@example.com:50000/somedb")
        )
        self.assertEqual(args, [])
        self.assertEqual(kw["host"], "example.com")
        self.assertEqual(kw["port"], 50000)
        self.assertEqual(kw["database"], "somedb")
        self.assertEqual(kw["user"], "someone")
        self.assertEqual(kw["password"], "s3cr3t")

    def test_create_connect_args_query(self):
        from sqlalchemy_db2.syn import DB2Dialect_syn

        dialect = DB2Dialect_syn()
        _, kw = dialect.create_connect_args(
            make_url(
                "db2+syn://u:p@h/d?use_ssl=true&timeout=10"
                "&ssl_client_cert_path=/tmp/cert.pem"
            )
        )
        self.assertIs(kw["use_ssl"], True)
        self.assertEqual(kw["timeout"], 10)
        self.assertEqual(kw["ssl_client_cert_path"], "/tmp/cert.pem")

    def test_async_dialect_attrs(self):
        from sqlalchemy_db2.asyn import DB2Dialect_asyn

        self.assertTrue(DB2Dialect_asyn.is_async)
        self.assertEqual(DB2Dialect_asyn.driver, "asyn")
        dbapi = DB2Dialect_asyn.import_dbapi()
        self.assertEqual(dbapi.paramstyle, "qmark")
        self.assertTrue(hasattr(dbapi, "OperationalError"))


class IsolationLevelTest(unittest.TestCase):
    def test_isolation_level(self):
        engine = sa.create_engine(SYNC_URL)
        with engine.connect() as conn:
            self.assertEqual(conn.get_isolation_level(), "READ COMMITTED")

        with engine.connect().execution_options(
            isolation_level="READ UNCOMMITTED"
        ) as conn:
            self.assertEqual(
                conn.get_isolation_level(), "READ UNCOMMITTED"
            )
        engine.dispose()

    def test_isolation_level_values(self):
        engine = sa.create_engine(SYNC_URL)
        with engine.connect() as conn:
            values = conn.dialect.get_isolation_level_values(
                conn.connection.dbapi_connection
            )
        self.assertEqual(
            sorted(values),
            sorted([
                "READ UNCOMMITTED", "READ COMMITTED",
                "REPEATABLE READ", "SERIALIZABLE",
            ]),
        )
        engine.dispose()


class PingTest(unittest.TestCase):
    def test_pre_ping(self):
        engine = sa.create_engine(SYNC_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            self.assertEqual(
                conn.scalar(sa.text("SELECT 1 FROM SYSIBM.SYSDUMMY1")), 1
            )
        engine.dispose()


class LastrowidTest(unittest.TestCase):
    def test_inserted_primary_key(self):
        engine = sa.create_engine(SYNC_URL)
        metadata = sa.MetaData()
        t = sa.Table(
            "test_dialect_lastrowid", metadata,
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("s", sa.String(30)),
        )
        with engine.begin() as conn:
            metadata.drop_all(conn, checkfirst=True)
            metadata.create_all(conn)
            r = conn.execute(t.insert().values(s="x"))
            self.assertEqual(r.inserted_primary_key, (1,))
            r = conn.execute(t.insert().values(s="y"))
            self.assertEqual(r.inserted_primary_key, (2,))
            metadata.drop_all(conn)
        engine.dispose()


class ExecuteManyTest(unittest.TestCase):
    def test_executemany(self):
        engine = sa.create_engine(SYNC_URL)
        metadata = sa.MetaData()
        t = sa.Table(
            "test_dialect_many", metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("x", sa.String(30)),
            sa.Column("y", sa.String(30)),
        )
        with engine.begin() as conn:
            metadata.drop_all(conn, checkfirst=True)
            metadata.create_all(conn)
            conn.execute(
                t.insert(),
                [
                    {"id": 1, "x": "x1", "y": "y1"},
                    {"id": 2, "x": "x2", "y": "y2"},
                    {"id": 3, "x": "x3", "y": "y3"},
                ],
            )
            rows = conn.execute(t.select().order_by(t.c.id)).fetchall()
            self.assertEqual(
                rows, [(1, "x1", "y1"), (2, "x2", "y2"), (3, "x3", "y3")]
            )
            metadata.drop_all(conn)
        engine.dispose()

    def test_insert_unicode(self):
        engine = sa.create_engine(SYNC_URL)
        metadata = sa.MetaData()
        t = sa.Table(
            "test_dialect_unicode", metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("s", sa.String(30)),
        )
        with engine.begin() as conn:
            metadata.drop_all(conn, checkfirst=True)
            metadata.create_all(conn)
            conn.execute(
                t.insert(),
                [
                    {"id": 1, "s": "méil"},
                    {"id": 2, "s": "日本語"},
                ],
            )
            rows = conn.execute(t.select().order_by(t.c.id)).fetchall()
            self.assertEqual(rows, [(1, "méil"), (2, "日本語")])
            metadata.drop_all(conn)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
