"""Async dialect tests (cf. sqlalchemy_firebirdsql test/test_async.py)."""
import unittest

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from .util import ASYNC_URL


class AsyncDialectTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(ASYNC_URL)
        self.metadata = sa.MetaData()
        self.table = sa.Table(
            "test_async_t", self.metadata,
            sa.Column("id", sa.Integer, primary_key=True,
                      autoincrement=True),
            sa.Column("name", sa.String(50)),
            sa.Column("amount", sa.Numeric(10, 2)),
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(
                lambda c: self.metadata.drop_all(c, checkfirst=True)
            )
            await conn.run_sync(self.metadata.create_all)

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(
                lambda c: self.metadata.drop_all(c, checkfirst=True)
            )
        await self.engine.dispose()

    async def test_insert_and_select(self):
        async with self.engine.begin() as conn:
            r = await conn.execute(
                self.table.insert().values(name="hello", amount=12.34)
            )
            self.assertEqual(r.inserted_primary_key, (1,))
            await conn.execute(
                self.table.insert(),
                [{"name": "a", "amount": 1}, {"name": "b", "amount": 2}],
            )
        async with self.engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.select(self.table).order_by(self.table.c.id)
                )
            ).fetchall()
            self.assertEqual([r.name for r in rows], ["hello", "a", "b"])
            count = await conn.scalar(
                sa.select(sa.func.count()).select_from(self.table)
            )
            self.assertEqual(count, 3)

    async def test_iterate_result(self):
        async with self.engine.begin() as conn:
            await conn.execute(
                self.table.insert(),
                [{"name": f"n{i}", "amount": i} for i in range(5)],
            )
        async with self.engine.connect() as conn:
            result = await conn.execute(
                sa.select(self.table).order_by(self.table.c.id)
            )
            names = [r.name for r in result]
            self.assertEqual(names, [f"n{i}" for i in range(5)])

    async def test_isolation_level(self):
        async with self.engine.connect() as conn:
            self.assertEqual(
                await conn.get_isolation_level(), "READ COMMITTED"
            )

    async def test_reflection(self):
        async with self.engine.connect() as conn:
            names = await conn.run_sync(
                lambda c: sa.inspect(c).get_table_names()
            )
            self.assertIn("test_async_t", names)

    async def test_transaction_rollback(self):
        async with self.engine.connect() as conn:
            trans = await conn.begin()
            await conn.execute(
                self.table.insert().values(name="rollback", amount=0)
            )
            await trans.rollback()
            count = await conn.scalar(
                sa.select(sa.func.count()).select_from(self.table)
            )
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
