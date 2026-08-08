# sqlalchemy_db2/base.py
# Copyright (C) 2026 Hajime Nakagami
#
# This module is released under the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Shared base for the pydrda DB2 dialects.

The SQL compilation / reflection layer is reused from ibm_db_sa; this
module only adds the pydrda DBAPI level behaviour shared by the sync
and async drivers.
"""
from sqlalchemy import types as sa_types
from sqlalchemy import util

from ibm_db_sa.base import DB2Dialect as _IBMDB2Dialect
from ibm_db_sa.base import DB2TypeCompiler as _IBMDB2TypeCompiler
from ibm_db_sa.base import colspecs as _ibm_colspecs

import drda


class DB2TypeCompiler(_IBMDB2TypeCompiler):
    def visit_BOOLEAN(self, type_, **kw):
        # DB2's DRDA protocol cannot bind BOOLEAN parameters,
        # so store booleans in a SMALLINT column instead.
        return "SMALLINT"


class DB2Dialect_pydrda_base(_IBMDB2Dialect):
    name = "db2"
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False

    # pydrda transfers native Python date/bool values, so the ibm_db
    # specific processors (which stringify them) must not be applied
    colspecs = {
        k: v for k, v in _ibm_colspecs.items()
        if k not in (sa_types.Boolean, sa_types.Date)
    }

    _isolation_lookup = {
        "READ UNCOMMITTED": "UR",
        "READ COMMITTED": "CS",
        "REPEATABLE READ": "RS",
        "SERIALIZABLE": "RR",
    }

    type_compiler = DB2TypeCompiler

    # DB2 has no SELECT without FROM
    _dialect_specific_select_one = "1 FROM SYSIBM.SYSDUMMY1"

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username="user")
        qry = url.query

        opts.update(qry)
        if "use_ssl" in opts:
            opts["use_ssl"] = util.asbool(opts["use_ssl"])
        if "timeout" in opts:
            opts["timeout"] = int(opts["timeout"])
        return ([], opts)

    def _get_default_schema_name(self, connection):
        return self.normalize_name(
            connection.exec_driver_sql(
                "SELECT CURRENT SCHEMA FROM SYSIBM.SYSDUMMY1"
            ).scalar()
        )

    def get_isolation_level_values(self, dbapi_connection):
        return list(self._isolation_lookup)

    def set_isolation_level(self, dbapi_connection, level):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(
                "SET CURRENT ISOLATION = %s" % self._isolation_lookup[level]
            )
        finally:
            cursor.close()

    def get_isolation_level(self, dbapi_connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(
                "SELECT CURRENT ISOLATION FROM SYSIBM.SYSDUMMY1"
            )
            val = cursor.fetchone()[0].strip()
        finally:
            cursor.close()
        if not val:
            # blank means the default (CS) from the package bind
            val = "CS"
        for name, abbrev in self._isolation_lookup.items():
            if abbrev == val:
                return name
        return val

    def reset_isolation_level(self, dbapi_connection):
        self.set_isolation_level(dbapi_connection, "READ COMMITTED")

    def is_disconnect(self, e, connection, cursor):
        sqlstate = getattr(e, "sqlstate", None) or ""
        if sqlstate.startswith("08"):
            return True
        if connection is not None:
            raw = getattr(connection, "_connection", connection)
            is_connect = getattr(raw, "is_connect", None)
            if is_connect is not None and not is_connect():
                return True
        if isinstance(
            e, (drda.OperationalError, drda.InterfaceError, ConnectionError)
        ):
            str_e = str(e).lower()
            return "lost connection" in str_e or "not connected" in str_e
        return False
