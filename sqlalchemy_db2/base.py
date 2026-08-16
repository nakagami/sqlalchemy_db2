# sqlalchemy_db2/base.py
# Copyright (C) 2026 Hajime Nakagami
#
# This module is released under the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Shared base for the pydrda DB2 dialects."""
from sqlalchemy import schema as sa_schema
from sqlalchemy import types as sa_types
from sqlalchemy import util
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler, operators

import drda

from .reflection import DB2Reflector

RESERVED_WORDS = {
    "activate", "disallow", "locale", "result", "add", "disconnect",
    "localtime", "result_set_locator", "after", "distinct", "localtimestamp",
    "return", "alias", "do", "locator", "returns", "all", "double",
    "locators", "revoke", "allocate", "drop", "lock", "right", "allow",
    "dssize", "lockmax", "rollback", "alter", "dynamic", "locksize",
    "routine", "and", "each", "long", "row", "any", "editproc", "loop",
    "row_number", "as", "else", "maintained", "rownumber", "asensitive",
    "elseif", "materialized", "rows", "associate", "enable", "maxvalue",
    "rowset", "asutime", "encoding", "microsecond", "rrn", "at",
    "encryption", "microseconds", "run", "attributes", "end", "minute",
    "savepoint", "audit", "end-exec", "minutes", "schema", "authorization",
    "ending", "minvalue", "scratchpad", "aux", "erase", "mode", "scroll",
    "auxiliary", "escape", "modifies", "search", "before", "every", "month",
    "second", "begin", "except", "months", "seconds", "between",
    "exception", "new", "secqty", "binary", "excluding", "new_table",
    "security", "bufferpool", "exclusive", "nextval", "select", "by",
    "execute", "no", "sensitive", "cache", "exists", "nocache", "sequence",
    "call", "exit", "nocycle", "session", "called", "explain", "nodename",
    "session_user", "capture", "external", "nodenumber", "set",
    "cardinality", "extract", "nomaxvalue", "signal", "cascaded", "fenced",
    "nominvalue", "simple", "case", "fetch", "none", "some", "cast",
    "fieldproc", "noorder", "source", "ccsid", "file", "normalized",
    "specific", "char", "final", "not", "sql", "character", "for", "null",
    "sqlid", "check", "foreign", "nulls", "stacked", "close", "free",
    "numparts", "standard", "cluster", "from", "obid", "start",
    "collection", "full", "of", "starting", "collid", "function", "old",
    "statement", "column", "general", "old_table", "static", "comment",
    "generated", "on", "stay", "commit", "get", "open", "stogroup",
    "concat", "global", "optimization", "stores", "condition", "go",
    "optimize", "style", "connect", "goto", "option", "substring",
    "connection", "grant", "or", "summary", "constraint", "graphic",
    "order", "synonym", "contains", "group", "out", "sysfun", "continue",
    "handler", "outer", "sysibm", "count", "hash", "over", "sysproc",
    "count_big", "hashed_value", "overriding", "system", "create",
    "having", "package", "system_user", "cross", "hint", "padded",
    "table", "current", "hold", "pagesize", "tablespace", "current_date",
    "hour", "parameter", "then", "current_lc_ctype", "hours", "part",
    "time", "current_path", "identity", "partition", "timestamp",
    "current_schema", "if", "partitioned", "to", "current_server",
    "immediate", "partitioning", "transaction", "current_time", "in",
    "partitions", "trigger", "current_timestamp", "including", "password",
    "trim", "current_timezone", "inclusive", "path", "type",
    "current_user", "increment", "piecesize", "undo", "cursor", "index",
    "plan", "union", "cycle", "indicator", "position", "unique", "data",
    "inherit", "precision", "until", "database", "inner", "prepare",
    "update", "datapartitionname", "inout", "prevval", "usage",
    "datapartitionnum", "insensitive", "primary", "user", "date",
    "insert", "priqty", "using", "day", "integrity", "privileges",
    "validproc", "days", "intersect", "procedure", "value", "db2general",
    "into", "program", "values", "db2genrl", "is", "psid", "variable",
    "db2sql", "isobid", "query", "variant", "dbinfo", "isolation",
    "queryno", "vcat", "dbpartitionname", "iterate", "range", "version",
    "dbpartitionnum", "jar", "rank", "view", "deallocate", "java", "read",
    "volatile", "declare", "join", "reads", "volumes", "default", "key",
    "recovery", "when", "defaults", "label", "references", "whenever",
    "definition", "language", "referencing", "where", "delete", "lateral",
    "refresh", "while", "dense_rank", "lc_ctype", "release", "with",
    "denserank", "leave", "rename", "without", "describe", "left",
    "repeat", "wlm", "descriptor", "like", "reset", "write",
    "deterministic", "linktype", "resignal", "xmlelement", "diagnostics",
    "local", "restart", "year", "disable", "localdate", "restrict",
    "years", "abs", "grouping", "regr_intercept", "are", "int", "regr_r2",
    "array", "integer", "regr_slope", "asymmetric", "intersection",
    "regr_sxx", "atomic", "interval", "regr_sxy", "avg", "large",
    "regr_syy", "bigint", "leading", "rollup", "blob", "ln", "scope",
    "boolean", "lower", "similar", "both", "match", "smallint", "ceil",
    "max", "specifictype", "ceiling", "member", "sqlexception",
    "char_length", "merge", "sqlstate", "character_length", "method",
    "sqlwarning", "clob", "min", "sqrt", "coalesce", "mod", "stddev_pop",
    "collate", "module", "stddev_samp", "collect", "multiset",
    "submultiset", "convert", "national", "sum", "corr", "natural",
    "symmetric", "corresponding", "nchar", "tablesample", "covar_pop",
    "nclob", "timezone_hour", "covar_samp", "normalize", "timezone_minute",
    "cube", "nullif", "trailing", "cume_dist", "numeric", "translate",
    "current_default_transform_group", "octet_length", "translation",
    "current_role", "only", "treat", "current_transform_group_for_type",
    "overlaps", "true", "dec", "overlay", "uescape", "decimal",
    "percent_rank", "unknown", "deref", "percentile_cont", "unnest",
    "element", "percentile_disc", "upper", "exec", "power", "var_pop",
    "exp", "real", "var_samp", "false", "recursive", "varchar", "filter",
    "ref", "varying", "float", "regr_avgx", "width_bucket", "floor",
    "regr_avgy", "window", "fusion", "regr_count", "within", "asc",
}


class BOOLEAN(sa_types.Boolean):
    __visit_name__ = "BOOLEAN"


class DOUBLE(sa_types.Numeric):
    __visit_name__ = "DOUBLE"


class LONGVARCHAR(sa_types.VARCHAR):
    __visit_name__ = "LONGVARCHAR"


class DBCLOB(sa_types.CLOB):
    __visit_name__ = "DBCLOB"


class GRAPHIC(sa_types.CHAR):
    __visit_name__ = "GRAPHIC"


class VARGRAPHIC(sa_types.Unicode):
    __visit_name__ = "VARGRAPHIC"


class LONGVARGRAPHIC(sa_types.UnicodeText):
    __visit_name__ = "LONGVARGRAPHIC"


class XML(sa_types.Text):
    __visit_name__ = "XML"


colspecs = {}

ischema_names = {
    "BOOLEAN": BOOLEAN,
    "BLOB": sa_types.BLOB,
    "CHAR": sa_types.CHAR,
    "CHARACTER": sa_types.CHAR,
    "CLOB": sa_types.CLOB,
    "DATE": sa_types.DATE,
    "DATETIME": sa_types.DATETIME,
    "INTEGER": sa_types.INTEGER,
    "SMALLINT": sa_types.SMALLINT,
    "BIGINT": sa_types.BIGINT,
    "DECIMAL": sa_types.DECIMAL,
    "NUMERIC": sa_types.NUMERIC,
    "REAL": sa_types.REAL,
    "DOUBLE": DOUBLE,
    "FLOAT": sa_types.FLOAT,
    "TIME": sa_types.TIME,
    "TIMESTAMP": sa_types.TIMESTAMP,
    "TIMESTMP": sa_types.TIMESTAMP,
    "VARCHAR": sa_types.VARCHAR,
    "LONGVARCHAR": LONGVARCHAR,
    "XML": XML,
    "GRAPHIC": GRAPHIC,
    "VARGRAPHIC": VARGRAPHIC,
    "LONGVARGRAPHIC": LONGVARGRAPHIC,
    "DBCLOB": DBCLOB,
}


class DB2TypeCompiler(compiler.GenericTypeCompiler):
    def visit_TIMESTAMP(self, type_, **kw):
        return "TIMESTAMP"

    def visit_DATE(self, type_, **kw):
        return "DATE"

    def visit_TIME(self, type_, **kw):
        return "TIME"

    def visit_DATETIME(self, type_, **kw):
        return "TIMESTAMP"

    def visit_SMALLINT(self, type_, **kw):
        return "SMALLINT"

    def visit_BOOLEAN(self, type_, **kw):
        # DB2's DRDA protocol cannot bind BOOLEAN parameters,
        # so store booleans in a SMALLINT column instead.
        return "SMALLINT"

    def visit_INT(self, type_, **kw):
        return "INT"

    def visit_BIGINT(self, type_, **kw):
        return "BIGINT"

    def visit_FLOAT(self, type_, **kw):
        if type_.precision is None:
            return "FLOAT"
        return f"FLOAT({type_.precision})"

    def visit_DOUBLE(self, type_, **kw):
        return "DOUBLE"

    def visit_XML(self, type_, **kw):
        return "XML"

    def visit_CLOB(self, type_, **kw):
        length = getattr(type_, "length", None)
        return f"CLOB({length})" if length else "CLOB"

    def visit_BLOB(self, type_, **kw):
        length = getattr(type_, "length", None)
        return "BLOB(1M)" if length in (None, 0) else f"BLOB({length})"

    def visit_DBCLOB(self, type_, **kw):
        length = getattr(type_, "length", None)
        return "DBCLOB(1M)" if length in (None, 0) else f"DBCLOB({length})"

    def visit_VARCHAR(self, type_, **kw):
        return f"VARCHAR({type_.length})"

    def visit_LONGVARCHAR(self, type_, **kw):
        return "LONG VARCHAR"

    def visit_VARGRAPHIC(self, type_, **kw):
        return f"VARGRAPHIC({type_.length})"

    def visit_LONGVARGRAPHIC(self, type_, **kw):
        return "LONG VARGRAPHIC"

    def visit_CHAR(self, type_, **kw):
        length = getattr(type_, "length", None)
        return "CHAR" if length in (None, 0) else f"CHAR({length})"

    def visit_GRAPHIC(self, type_, **kw):
        length = getattr(type_, "length", None)
        return "GRAPHIC" if length in (None, 0) else f"GRAPHIC({length})"

    def visit_DECIMAL(self, type_, **kw):
        if not type_.precision:
            return "DECIMAL(31, 0)"
        elif not type_.scale:
            return f"DECIMAL({type_.precision}, 0)"
        else:
            return f"DECIMAL({type_.precision}, {type_.scale})"

    def visit_numeric(self, type_, **kw):
        return self.visit_DECIMAL(type_, **kw)

    def visit_datetime(self, type_, **kw):
        return self.visit_TIMESTAMP(type_, **kw)

    def visit_date(self, type_, **kw):
        return self.visit_DATE(type_, **kw)

    def visit_time(self, type_, **kw):
        return self.visit_TIME(type_, **kw)

    def visit_integer(self, type_, **kw):
        return self.visit_INT(type_, **kw)

    def visit_boolean(self, type_, **kw):
        return self.visit_BOOLEAN(type_, **kw)

    def visit_float(self, type_, **kw):
        return self.visit_FLOAT(type_, **kw)

    def visit_unicode(self, type_, **kw):
        return self.visit_VARGRAPHIC(type_, **kw)

    def visit_unicode_text(self, type_, **kw):
        return self.visit_LONGVARGRAPHIC(type_, **kw)

    def visit_string(self, type_, **kw):
        return self.visit_VARCHAR(type_, **kw)

    def visit_TEXT(self, type_, **kw):
        return self.visit_CLOB(type_, **kw)

    def visit_large_binary(self, type_, **kw):
        return self.visit_BLOB(type_, **kw)


class DB2Compiler(compiler.SQLCompiler):
    def get_cte_preamble(self, recursive):
        return "WITH"

    def visit_now_func(self, fn, **kw):
        return "CURRENT_TIMESTAMP"

    def for_update_clause(self, select, **kw):
        if select._for_update_arg is not None:
            if select._for_update_arg.read:
                return " WITH RS USE AND KEEP SHARE LOCKS"
            return " WITH RS USE AND KEEP UPDATE LOCKS"
        return ""

    def visit_mod_binary(self, binary, operator, **kw):
        return f"mod({self.process(binary.left, **kw)}, {self.process(binary.right, **kw)})"

    def limit_clause(self, select, **kw):
        text = ""
        if select._limit_clause is not None:
            text += f" LIMIT {self.process(select._limit_clause, **kw)}"
        if select._offset_clause is not None:
            text += f" OFFSET {self.process(select._offset_clause, **kw)}"
        return text

    def visit_sequence(self, sequence, **kw):
        return f"NEXT VALUE FOR {self.preparer.format_sequence(sequence)}"

    def default_from(self):
        return " FROM SYSIBM.SYSDUMMY1"

    def visit_function(self, func, result_map=None, **kwargs):
        func_name = func.name.upper()
        if func_name == "AVG":
            args = self.function_argspec(func, **kwargs)
            return f"AVG(DOUBLE({args}))"
        elif func_name == "CHAR_LENGTH":
            args = self.function_argspec(func, **kwargs)
            return f"CHAR_LENGTH({args}, OCTETS)"
        return super().visit_function(func, **kwargs)

    def visit_savepoint(self, savepoint_stmt):
        sid = self.preparer.format_savepoint(savepoint_stmt)
        return f"SAVEPOINT {sid} ON ROLLBACK RETAIN CURSORS"

    def visit_rollback_to_savepoint(self, savepoint_stmt):
        sid = self.preparer.format_savepoint(savepoint_stmt)
        return f"ROLLBACK TO SAVEPOINT {sid}"

    def visit_release_savepoint(self, savepoint_stmt):
        sid = self.preparer.format_savepoint(savepoint_stmt)
        return f"RELEASE TO SAVEPOINT {sid}"

    def visit_unary(self, unary, **kw):
        if unary.operator == operators.exists and kw.get(
            "within_columns_clause", False
        ):
            usql = super().visit_unary(unary, **kw)
            return f"CASE WHEN {usql} THEN 1 ELSE 0 END"
        return super().visit_unary(unary, **kw)


class DB2DDLCompiler(compiler.DDLCompiler):
    def get_column_specification(self, column, **kw):
        col_spec = [
            self.preparer.format_column(column),
            self.dialect.type_compiler.process(
                column.type, type_expression=column
            ),
        ]
        if not column.nullable or column.primary_key:
            col_spec.append("NOT NULL")
        default = self.get_column_default_string(column)
        if default is not None:
            col_spec.extend(["WITH DEFAULT", default])
        auto_column = column.table._autoincrement_column
        if column is auto_column:
            col_spec.extend([
                "GENERATED BY DEFAULT",
                "AS IDENTITY",
                "(START WITH 1)",
            ])
        return " ".join(col_spec)

    def define_constraint_cascades(self, constraint):
        text = ""
        if constraint.ondelete is not None:
            text += f" ON DELETE {constraint.ondelete}"
        if constraint.onupdate is not None:
            util.warn("DB2 does not support UPDATE CASCADE for foreign keys.")
        return text

    def visit_drop_constraint(self, drop, **kw):
        constraint = drop.element
        if isinstance(constraint, sa_schema.ForeignKeyConstraint):
            qual = "FOREIGN KEY "
            const = self.preparer.format_constraint(constraint)
        elif isinstance(constraint, sa_schema.PrimaryKeyConstraint):
            qual = "PRIMARY KEY "
            const = ""
        elif isinstance(constraint, sa_schema.UniqueConstraint):
            qual = "UNIQUE "
            const = self.preparer.format_constraint(constraint)
        else:
            qual = ""
            const = self.preparer.format_constraint(constraint)
        table_name = self.preparer.format_table(constraint.table)
        return f"ALTER TABLE {table_name} DROP {qual}{const}"


class DB2IdentifierPreparer(compiler.IdentifierPreparer):
    reserved_words = RESERVED_WORDS
    illegal_initial_characters = set(range(0, 10)).union(["_", "$"])


class DB2ExecutionContext(default.DefaultExecutionContext):
    _select_lastrowid = False
    _lastrowid = None

    def get_lastrowid(self):
        return self._lastrowid

    def pre_exec(self):
        super().pre_exec()
        if not self.isinsert:
            return
        compiled = self.compiled
        statement = compiled.statement
        table = statement.table
        seq_column = getattr(table, "_autoincrement_column", None)
        self._select_lastrowid = (
            seq_column is not None
            and not compiled.returning
            and not getattr(compiled, "inline", False)
        )

    def post_exec(self):
        super().post_exec()
        if not self._select_lastrowid:
            return
        conn = self.root_connection
        cursor = self.cursor
        identity_sql = "SELECT IDENTITY_VAL_LOCAL() FROM SYSIBM.SYSDUMMY1"
        conn._cursor_execute(cursor, identity_sql, (), self)
        row = cursor.fetchall()[0]
        if row[0] is not None:
            self._lastrowid = int(row[0])

    def fire_sequence(self, seq, type_):
        formatted_seq = self.dialect.identifier_preparer.format_sequence(seq)
        sql = f"SELECT NEXTVAL FOR {formatted_seq} FROM SYSIBM.SYSDUMMY1"
        return self._execute_scalar(sql, type_)


class DB2Dialect_pydrda_base(default.DefaultDialect):
    name = "db2"
    max_identifier_length = 128
    encoding = "utf-8"
    default_paramstyle = "qmark"
    colspecs = colspecs
    ischema_names = ischema_names
    supports_char_length = False
    supports_unicode_statements = False
    supports_unicode_binds = False
    returns_unicode_strings = True
    postfetch_lastrowid = True
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False
    supports_native_decimal = False
    supports_native_boolean = False
    supports_statement_cache = True
    preexecute_sequences = False
    supports_alter = True
    supports_sequences = True
    sequences_optional = True

    requires_name_normalize = True

    supports_default_values = False
    supports_empty_insert = False

    two_phase_transactions = False
    savepoints = True

    statement_compiler = DB2Compiler
    ddl_compiler = DB2DDLCompiler
    type_compiler = DB2TypeCompiler
    preparer = DB2IdentifierPreparer
    execution_ctx_cls = DB2ExecutionContext

    # DB2 has no SELECT without FROM
    _dialect_specific_select_one = "1 FROM SYSIBM.SYSDUMMY1"

    _isolation_lookup = {
        "READ UNCOMMITTED": "UR",
        "READ COMMITTED": "CS",
        "REPEATABLE READ": "RS",
        "SERIALIZABLE": "RR",
    }

    def __init__(self, **kw):
        super().__init__(**kw)
        self._reflector = DB2Reflector(self)

    def _get_default_schema_name(self, connection):
        return self.normalize_name(
            connection.exec_driver_sql(
                "SELECT CURRENT SCHEMA FROM SYSIBM.SYSDUMMY1"
            ).scalar()
        )

    def normalize_name(self, name):
        return self._reflector.normalize_name(name)

    def denormalize_name(self, name):
        return self._reflector.denormalize_name(name)

    def has_table(self, connection, table_name, schema=None, **kw):
        return self._reflector.has_table(
            connection, table_name, schema=schema, **kw
        )

    def has_sequence(self, connection, sequence_name, schema=None, **kw):
        return self._reflector.has_sequence(
            connection, sequence_name, schema=schema, **kw
        )

    def get_sequence_names(self, connection, schema=None, **kw):
        return self._reflector.get_sequence_names(
            connection, schema=schema, **kw
        )

    def get_schema_names(self, connection, **kw):
        return self._reflector.get_schema_names(connection, **kw)

    def get_table_names(self, connection, schema=None, **kw):
        return self._reflector.get_table_names(connection, schema=schema, **kw)

    def get_view_names(self, connection, schema=None, **kw):
        return self._reflector.get_view_names(connection, schema=schema, **kw)

    def get_view_definition(self, connection, view_name, schema=None, **kw):
        return self._reflector.get_view_definition(
            connection, view_name, schema=schema, **kw
        )

    def get_columns(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_columns(
            connection, table_name, schema=schema, **kw
        )

    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_pk_constraint(
            connection, table_name, schema=schema, **kw
        )

    def get_primary_keys(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_primary_keys(
            connection, table_name, schema=schema, **kw
        )

    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_foreign_keys(
            connection, table_name, schema=schema, **kw
        )

    def get_incoming_foreign_keys(
        self, connection, table_name, schema=None, **kw
    ):
        return self._reflector.get_incoming_foreign_keys(
            connection, table_name, schema=schema, **kw
        )

    def get_indexes(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_indexes(
            connection, table_name, schema=schema, **kw
        )

    def get_unique_constraints(
        self, connection, table_name, schema=None, **kw
    ):
        return self._reflector.get_unique_constraints(
            connection, table_name, schema=schema, **kw
        )

    def get_table_comment(self, connection, table_name, schema=None, **kw):
        return self._reflector.get_table_comment(
            connection, table_name, schema=schema, **kw
        )

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username="user")
        qry = url.query

        opts.update(qry)
        if "use_ssl" in opts:
            opts["use_ssl"] = util.asbool(opts["use_ssl"])
        if "timeout" in opts:
            opts["timeout"] = int(opts["timeout"])
        return ([], opts)

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
