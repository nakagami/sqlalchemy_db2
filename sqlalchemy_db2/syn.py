# sqlalchemy_db2/syn.py
# Copyright (C) 2026 Hajime Nakagami
#
# This module is released under the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
.. dialect:: db2+syn
    :name: db2
    :dbapi: drda (pydrda)
    :connectstring: db2+syn://user:pass@host:port/database[?key=value&key=value...]
"""  # noqa

from .base import DB2Dialect_pydrda_base

import drda


class DB2Dialect_syn(DB2Dialect_pydrda_base):
    driver = "syn"
    supports_statement_cache = True

    @classmethod
    def import_dbapi(cls):
        return drda

    def do_rollback(self, dbapi_connection):
        dbapi_connection.rollback()

    def do_commit(self, dbapi_connection):
        dbapi_connection.commit()


dialect = DB2Dialect_syn
