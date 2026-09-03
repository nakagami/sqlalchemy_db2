# sqlalchemy_db2/asyn.py
# Copyright (C) 2026 Hajime Nakagami
#
# This module is released under the MIT License: http://www.opensource.org/licenses/mit-license.php
# mypy: ignore-errors
r"""
.. dialect:: db2+asyn
    :name: db2
    :dbapi: drda (pydrda)
    :connectstring: db2+asyn://user:pass@host:port/database[?key=value&key=value...]

This dialect should normally be used only with the
:func:`_asyncio.create_async_engine` engine creation function::

    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "db2+asyn://user:pass@host:port/database"
    )

"""  # noqa
from collections import deque

from .base import DB2Dialect_pydrda_base
from sqlalchemy import pool
from sqlalchemy import util
from sqlalchemy.engine import AdaptedConnection
from sqlalchemy.util.concurrency import asyncio
from sqlalchemy.util.concurrency import await_fallback
from sqlalchemy.util.concurrency import await_only

import drda
import drda.aio


def _await_fallback(awaitable):
    try:
        return await_fallback(awaitable)
    except RuntimeError:
        # Python 3.14 no longer creates an implicit event loop, so
        # await_fallback() fails when there is no current loop in this
        # thread.  Run the awaitable on a fresh loop instead.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(awaitable)
        finally:
            loop.close()


class AsyncAdapt_drda_cursor:
    server_side = False
    __slots__ = (
        "_adapt_connection",
        "_connection",
        "await_",
        "_cursor",
        "_rows",
    )

    def __init__(self, adapt_connection):
        self._adapt_connection = adapt_connection
        self._connection = adapt_connection._connection
        self.await_ = adapt_connection.await_

        self._cursor = self._connection.cursor()
        self._rows = deque()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def arraysize(self):
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    def close(self):
        # note we aren't actually closing the cursor here,
        # we are just letting GC do it.   to allow this to be async
        # we would need the Result to change how it does "Safe close cursor".
        self._rows.clear()

    async def _async_soft_close(self):
        """close the cursor but keep the results pending.

        Rows are already buffered client side by pydrda at execute
        time, and the cursor holds no server side resources, so there
        is nothing to do.
        """

    def execute(self, operation, parameters=None):
        return self.await_(self._execute_async(operation, parameters))

    def executemany(self, operation, seq_of_parameters):
        return self.await_(
            self._executemany_async(operation, seq_of_parameters)
        )

    async def _execute_async(self, operation, parameters):
        async with self._adapt_connection._execute_mutex:
            result = await self._cursor.execute(
                operation, parameters if parameters is not None else []
            )

            # pydrda has a "fake" async result, so we have to pull it out
            # of that here since our default result is not async.
            self._rows = deque(self._cursor._rows)
            return result

    async def _executemany_async(self, operation, seq_of_parameters):
        async with self._adapt_connection._execute_mutex:
            return await self._cursor.executemany(operation, seq_of_parameters)

    def setinputsizes(self, *inputsizes):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        r = self.fetchone()
        if r is None:
            raise StopIteration
        return r

    def fetchone(self):
        if self._rows:
            return self._rows.popleft()
        else:
            return None

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize

        rr = self._rows
        return [rr.popleft() for _ in range(min(size, len(rr)))]

    def fetchall(self):
        retval = list(self._rows)
        self._rows.clear()
        return retval


class AsyncAdapt_drda_connection(AdaptedConnection):
    await_ = staticmethod(await_only)
    __slots__ = ("dbapi", "_execute_mutex")

    def __init__(self, dbapi, connection):
        self.dbapi = dbapi
        self._connection = connection
        self._execute_mutex = asyncio.Lock()

    def ping(self, reconnect=False):
        return self._connection.is_connect()

    def autocommit(self, value):
        raise NotImplementedError(
            "pydrda does not support autocommit"
        )

    def cursor(self):
        return AsyncAdapt_drda_cursor(self)

    def rollback(self):
        self.await_(self._connection.rollback())

    def commit(self):
        self.await_(self._connection.commit())

    def terminate(self):
        # it's not awaitable.
        sock = getattr(self._connection, "sock", None)
        if sock is not None:
            writer = getattr(sock, "_writer", None)
            if writer is not None:
                try:
                    writer.close()
                except Exception:
                    pass
            sock._reader = None
            sock._writer = None

    def close(self) -> None:
        self.await_(self._connection.close())


class AsyncAdaptFallback_drda_connection(AsyncAdapt_drda_connection):
    __slots__ = ()

    await_ = staticmethod(_await_fallback)


class AsyncAdapt_drda_dbapi:
    def __init__(self, asyn, syn):
        self.asyn = asyn
        self.syn = syn
        self.paramstyle = "qmark"
        self.apilevel = "2.0"
        self.threadsafety = 1
        self._init_dbapi_attributes()

    def _init_dbapi_attributes(self):
        for name in (
            "Warning",
            "Error",
            "InterfaceError",
            "DataError",
            "DatabaseError",
            "OperationalError",
            "IntegrityError",
            "ProgrammingError",
            "InternalError",
            "NotSupportedError",
        ):
            setattr(self, name, getattr(drda, name))

        for name in (
            "NUMBER",
            "STRING",
            "DATETIME",
            "BINARY",
            "DATE",
            "TIME",
            "ROWID",
            "Date",
            "Time",
            "Timestamp",
            "Binary",
        ):
            setattr(self, name, getattr(drda, name))

    def connect(self, *arg, **kw):
        async_fallback = kw.pop("async_fallback", False)
        creator_fn = kw.pop("async_creator_fn", self.asyn.connect)

        if util.asbool(async_fallback):
            # SQLAlchemy's fallback machinery awaits coroutines on the
            # thread's current event loop.  Python 3.14 no longer creates
            # one implicitly, so make sure it exists.
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
            return AsyncAdaptFallback_drda_connection(
                self,
                _await_fallback(creator_fn(*arg, **kw)),
            )
        else:
            return AsyncAdapt_drda_connection(
                self,
                await_only(creator_fn(*arg, **kw)),
            )


class DB2Dialect_asyn(DB2Dialect_pydrda_base):
    driver = "asyn"
    supports_statement_cache = True

    is_async = True
    has_terminate = True

    @classmethod
    def import_dbapi(cls):
        return AsyncAdapt_drda_dbapi(drda.aio, drda)

    @classmethod
    def get_pool_class(cls, url):
        async_fallback = url.query.get("async_fallback", False)

        if util.asbool(async_fallback):
            return pool.FallbackAsyncAdaptedQueuePool
        else:
            return pool.AsyncAdaptedQueuePool

    def do_terminate(self, dbapi_connection) -> None:
        dbapi_connection.terminate()

    def get_driver_connection(self, connection):
        return connection._connection


dialect = DB2Dialect_asyn
