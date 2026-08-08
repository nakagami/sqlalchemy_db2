"""Type roundtrip tests (cf. sqlalchemy_firebirdsql test/test_types.py)."""
import datetime
import decimal
import unittest

import sqlalchemy as sa

from .util import SYNC_URL


class TypesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = sa.create_engine(SYNC_URL)
        cls.metadata = sa.MetaData()
        cls.table = sa.Table(
            "test_types", cls.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("i", sa.Integer),
            sa.Column("bi", sa.BigInteger),
            sa.Column("si", sa.SmallInteger),
            sa.Column("n", sa.Numeric(10, 2)),
            sa.Column("f", sa.Float),
            sa.Column("s", sa.String(50)),
            sa.Column("t", sa.Text),
            sa.Column("d", sa.Date),
            sa.Column("tm", sa.Time),
            sa.Column("dt", sa.DateTime),
            sa.Column("b", sa.Boolean),
            sa.Column("bl", sa.LargeBinary),
        )
        with cls.engine.begin() as conn:
            cls.metadata.drop_all(conn, checkfirst=True)
            cls.metadata.create_all(conn)

    @classmethod
    def tearDownClass(cls):
        with cls.engine.begin() as conn:
            cls.metadata.drop_all(conn, checkfirst=True)
        cls.engine.dispose()

    def setUp(self):
        with self.engine.begin() as conn:
            conn.execute(self.table.delete())

    def _roundtrip(self, **values):
        with self.engine.begin() as conn:
            conn.execute(self.table.insert().values(**values))
            row = conn.execute(self.table.select()).fetchone()
        for k, v in values.items():
            self.assertEqual(row._mapping[k], v, f"column {k}")

    def test_integer(self):
        self._roundtrip(id=1, i=42, bi=2**40, si=-5)

    def test_numeric(self):
        self._roundtrip(id=1, n=decimal.Decimal("12.34"))

    def test_float(self):
        self._roundtrip(id=1, f=1.25)

    def test_string(self):
        self._roundtrip(id=1, s="hello", t="long text" * 100)

    def test_unicode(self):
        self._roundtrip(id=1, s="日本語メール")

    def test_date(self):
        self._roundtrip(id=1, d=datetime.date(2026, 8, 8))

    def test_time(self):
        self._roundtrip(id=1, tm=datetime.time(12, 34, 56))

    def test_datetime(self):
        self._roundtrip(id=1, dt=datetime.datetime(2026, 8, 8, 12, 34, 56))

    def test_boolean(self):
        with self.engine.begin() as conn:
            conn.execute(self.table.insert(), [
                {"id": 1, "b": True},
                {"id": 2, "b": False},
            ])
            rows = conn.execute(
                self.table.select().order_by(self.table.c.id)
            ).fetchall()
        self.assertEqual([r.b for r in rows], [True, False])

    def test_binary(self):
        self._roundtrip(id=1, bl=b"\x00\x01\x02\xff" * 100)

    def test_nulls(self):
        with self.engine.begin() as conn:
            conn.execute(self.table.insert().values(id=1))
            row = conn.execute(self.table.select()).fetchone()
        self.assertIsNone(row.i)
        self.assertIsNone(row.s)
        self.assertIsNone(row.dt)

    def test_reflected_types(self):
        m2 = sa.MetaData()
        t2 = sa.Table("test_types", m2, autoload_with=self.engine)
        for name, cls in [
            ("i", sa.Integer),
            ("bi", sa.BigInteger),
            ("n", sa.Numeric),
            ("s", sa.String),
            ("d", sa.Date),
            ("dt", sa.DateTime),
        ]:
            self.assertIsInstance(t2.c[name].type, cls, f"column {name}")


if __name__ == "__main__":
    unittest.main()
