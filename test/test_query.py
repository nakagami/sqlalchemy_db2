"""Query tests (cf. sqlalchemy_firebirdsql test/test_query.py)."""
import unittest

import sqlalchemy as sa
from sqlalchemy import func, select

from .util import SYNC_URL


class QueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = sa.create_engine(SYNC_URL)
        cls.metadata = sa.MetaData()
        cls.t1 = sa.Table(
            "test_query_t1", cls.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(50)),
            sa.Column("val", sa.Integer),
        )
        cls.t2 = sa.Table(
            "test_query_t2", cls.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("t1_id", sa.Integer,
                      sa.ForeignKey("test_query_t1.id")),
            sa.Column("note", sa.String(50)),
        )
        with cls.engine.begin() as conn:
            cls.metadata.drop_all(conn, checkfirst=True)
            cls.metadata.create_all(conn)
            conn.execute(
                cls.t1.insert(),
                [
                    {"id": 1, "name": "apple", "val": 10},
                    {"id": 2, "name": "banana", "val": 20},
                    {"id": 3, "name": "cherry", "val": 30},
                ],
            )
            conn.execute(
                cls.t2.insert(),
                [
                    {"id": 1, "t1_id": 1, "note": "a1"},
                    {"id": 2, "t1_id": 1, "note": "a2"},
                    {"id": 3, "t1_id": 2, "note": "b1"},
                ],
            )

    @classmethod
    def tearDownClass(cls):
        with cls.engine.begin() as conn:
            cls.metadata.drop_all(conn, checkfirst=True)
        cls.engine.dispose()

    def test_where(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(self.t1).where(self.t1.c.val > 15)
                .order_by(self.t1.c.id)
            ).fetchall()
        self.assertEqual(rows, [(2, "banana", 20), (3, "cherry", 30)])

    def test_like(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(self.t1.c.name).where(self.t1.c.name.like("a%"))
            ).fetchall()
        self.assertEqual(rows, [("apple",)])

    def test_limit_offset(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(self.t1).order_by(self.t1.c.id).limit(1).offset(1)
            ).fetchall()
        self.assertEqual(rows, [(2, "banana", 20)])

    def test_count(self):
        with self.engine.connect() as conn:
            self.assertEqual(
                conn.scalar(select(func.count()).select_from(self.t1)), 3
            )

    def test_join(self):
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(self.t1.c.name, self.t2.c.note)
                .join(self.t2, self.t1.c.id == self.t2.c.t1_id)
                .order_by(self.t2.c.id)
            ).fetchall()
        self.assertEqual(
            rows,
            [("apple", "a1"), ("apple", "a2"), ("banana", "b1")],
        )

    def test_update(self):
        with self.engine.begin() as conn:
            conn.execute(
                self.t1.update().where(self.t1.c.id == 3).values(val=99)
            )
            self.assertEqual(
                conn.scalar(
                    select(self.t1.c.val).where(self.t1.c.id == 3)
                ),
                99,
            )
            conn.execute(
                self.t1.update().where(self.t1.c.id == 3).values(val=30)
            )

    def test_delete(self):
        with self.engine.begin() as conn:
            conn.execute(self.t2.insert().values(id=99, t1_id=3, note="x"))
            conn.execute(self.t2.delete().where(self.t2.c.id == 99))
            self.assertEqual(
                conn.scalar(select(func.count()).select_from(self.t2)), 3
            )


if __name__ == "__main__":
    unittest.main()
