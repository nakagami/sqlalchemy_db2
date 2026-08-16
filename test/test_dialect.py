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


class CompilationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy_db2.syn import DB2Dialect_syn
        cls.dialect = DB2Dialect_syn()

    def test_create_table_ddl(self):
        from sqlalchemy.schema import CreateTable
        metadata = sa.MetaData()
        table = sa.Table(
            "test_tbl", metadata,
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("b", sa.Boolean),
            sa.Column("d", sa.Date),
            sa.Column("dt", sa.DateTime),
            sa.Column("n", sa.Numeric(10, 2)),
            sa.Column("s", sa.String(50)),
            sa.Column("t", sa.Text),
            sa.Column("bl", sa.LargeBinary),
        )
        sql = str(CreateTable(table).compile(dialect=self.dialect))
        self.assertIn("id INT NOT NULL GENERATED BY DEFAULT AS IDENTITY (START WITH 1)", sql)
        self.assertIn("b SMALLINT", sql)
        self.assertIn("d DATE", sql)
        self.assertIn("dt TIMESTAMP", sql)
        self.assertIn("n DECIMAL(10, 2)", sql)
        self.assertIn("s VARCHAR(50)", sql)
        self.assertIn("t CLOB", sql)
        self.assertIn("bl BLOB(1M)", sql)

    def test_select_limit_offset(self):
        metadata = sa.MetaData()
        table = sa.Table("test_tbl", metadata, sa.Column("id", sa.Integer))
        stmt = sa.select(table).order_by(table.c.id).limit(10).offset(5)
        sql = str(stmt.compile(dialect=self.dialect))
        self.assertIn("LIMIT ?", sql)
        self.assertIn("OFFSET ?", sql)

    def test_select_now(self):
        stmt = sa.select(sa.func.now())
        sql = str(stmt.compile(dialect=self.dialect))
        self.assertIn("CURRENT_TIMESTAMP", sql)
        self.assertIn("FROM SYSIBM.SYSDUMMY1", sql)

    def test_select_mod(self):
        table = sa.Table("t", sa.MetaData(), sa.Column("x", sa.Integer), sa.Column("y", sa.Integer))
        stmt = sa.select(table.c.x % table.c.y)
        sql = str(stmt.compile(dialect=self.dialect))
        self.assertIn("mod(t.x, t.y)", sql)

    def test_sequence(self):
        seq = sa.Sequence("my_seq")
        stmt = sa.select(seq.next_value())
        sql = str(stmt.compile(dialect=self.dialect))
        self.assertIn("NEXT VALUE FOR my_seq", sql)

    def test_for_update(self):
        table = sa.Table("t", sa.MetaData(), sa.Column("id", sa.Integer))
        stmt = sa.select(table).with_for_update()
        sql = str(stmt.compile(dialect=self.dialect))
        self.assertIn("WITH RS USE AND KEEP UPDATE LOCKS", sql)

    def test_reflector_normalize_denormalize(self):
        from sqlalchemy_db2.reflection import DB2Reflector
        reflector = DB2Reflector(self.dialect)
        self.assertEqual(reflector.normalize_name("MY_TABLE"), "my_table")
        self.assertEqual(reflector.normalize_name("my_table"), "my_table")
        self.assertEqual(reflector.denormalize_name("my_table"), "MY_TABLE")
        self.assertEqual(reflector.denormalize_name("MY_TABLE"), "MY_TABLE")

    def test_reflector_mock_methods(self):
        from unittest.mock import MagicMock
        from sqlalchemy_db2.reflection import DB2Reflector

        reflector = DB2Reflector(self.dialect)
        conn = MagicMock()

        conn.execute.return_value = [("TBL1",), ("TBL2",)]
        self.assertEqual(reflector.get_table_names(conn), ["tbl1", "tbl2"])

        conn.execute.return_value = [("VW1",)]
        self.assertEqual(reflector.get_view_names(conn), ["vw1"])

        conn.execute.return_value = [
            ("ID", "INTEGER", None, "N", 4, 0, "Y", "A", None),
            ("NAME", "VARCHAR", None, "Y", 50, 0, "N", " ", "a remark"),
        ]
        cols = reflector.get_columns(conn, "tbl1")
        self.assertEqual(len(cols), 2)
        self.assertEqual(cols[0]["name"], "id")
        self.assertTrue(cols[0]["autoincrement"])
        self.assertFalse(cols[0]["nullable"])
        self.assertEqual(cols[1]["name"], "name")
        self.assertEqual(cols[1]["comment"], "a remark")

        conn.execute.return_value = [("+ID", "PK_TBL1")]
        pk = reflector.get_pk_constraint(conn, "tbl1")
        self.assertEqual(pk, {"constrained_columns": ["id"], "name": "pk_tbl1"})

        conn.execute.return_value = [
            ("FK_T2_T1", "MYSCHEMA", "T2", "T1_ID", "PK_T1", "MYSCHEMA", "T1", "ID")
        ]
        fks = reflector.get_foreign_keys(conn, "t2")
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0]["name"], "fk_t2_t1")
        self.assertEqual(fks[0]["constrained_columns"], ["t1_id"])
        self.assertEqual(fks[0]["referred_table"], "t1")
        self.assertEqual(fks[0]["referred_columns"], ["id"])

        conn.execute.return_value = [("IX_NAME", "+NAME", "D", 0)]
        indexes = reflector.get_indexes(conn, "tbl1")
        self.assertEqual(len(indexes), 1)
        self.assertEqual(indexes[0]["name"], "ix_name")
        self.assertEqual(indexes[0]["column_names"], ["name"])
        self.assertFalse(indexes[0]["unique"])

        conn.execute.return_value = [("UQ_CODE", "CODE")]
        uqs = reflector.get_unique_constraints(conn, "tbl1")
        self.assertEqual(len(uqs), 1)
        self.assertEqual(uqs[0]["name"], "uq_code")
        self.assertEqual(uqs[0]["column_names"], ["code"])



if __name__ == "__main__":
    unittest.main()
