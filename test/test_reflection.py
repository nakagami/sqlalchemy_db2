"""Reflection tests (cf. sqlalchemy_firebirdsql test/test_reflection.py)."""
import unittest

import sqlalchemy as sa

from .util import SYNC_URL


class ReflectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = sa.create_engine(SYNC_URL)
        cls.metadata = sa.MetaData()
        sa.Table(
            "test_reflect_parent", cls.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(50), nullable=False,
                      index=True),
        )
        sa.Table(
            "test_reflect_child", cls.metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("parent_id", sa.Integer,
                      sa.ForeignKey("test_reflect_parent.id")),
        )
        with cls.engine.begin() as conn:
            cls.metadata.drop_all(conn, checkfirst=True)
            cls.metadata.create_all(conn)
            conn.execute(sa.text(
                "CREATE VIEW test_reflect_view AS "
                "SELECT id, name FROM test_reflect_parent"
            ))

    @classmethod
    def tearDownClass(cls):
        with cls.engine.begin() as conn:
            conn.execute(sa.text("DROP VIEW test_reflect_view"))
            cls.metadata.drop_all(conn, checkfirst=True)
        cls.engine.dispose()

    def test_table_names(self):
        insp = sa.inspect(self.engine)
        names = insp.get_table_names()
        self.assertIn("test_reflect_parent", names)
        self.assertIn("test_reflect_child", names)

    def test_view_names(self):
        insp = sa.inspect(self.engine)
        self.assertIn("test_reflect_view", insp.get_view_names())

    def test_columns(self):
        insp = sa.inspect(self.engine)
        cols = {c["name"]: c for c in insp.get_columns("test_reflect_parent")}
        self.assertEqual(set(cols), {"id", "name"})
        self.assertIsInstance(cols["id"]["type"], sa.Integer)
        self.assertIsInstance(cols["name"]["type"], sa.String)
        self.assertFalse(cols["name"]["nullable"])

    def test_pk_constraint(self):
        insp = sa.inspect(self.engine)
        pk = insp.get_pk_constraint("test_reflect_child")
        self.assertEqual(pk["constrained_columns"], ["id"])

    def test_foreign_keys(self):
        insp = sa.inspect(self.engine)
        fks = insp.get_foreign_keys("test_reflect_child")
        self.assertEqual(len(fks), 1)
        self.assertEqual(fks[0]["constrained_columns"], ["parent_id"])
        self.assertEqual(fks[0]["referred_table"], "test_reflect_parent")
        self.assertEqual(fks[0]["referred_columns"], ["id"])

    def test_indexes(self):
        insp = sa.inspect(self.engine)
        indexes = insp.get_indexes("test_reflect_parent")
        self.assertTrue(
            any(ix["column_names"] == ["name"] for ix in indexes)
        )

    def test_autoload(self):
        m2 = sa.MetaData()
        t2 = sa.Table("test_reflect_parent", m2, autoload_with=self.engine)
        self.assertEqual(set(t2.c.keys()), {"id", "name"})

    def test_has_table(self):
        with self.engine.connect() as conn:
            self.assertTrue(
                conn.dialect.has_table(conn, "test_reflect_parent")
            )
            self.assertFalse(
                conn.dialect.has_table(conn, "no_such_table")
            )


if __name__ == "__main__":
    unittest.main()
