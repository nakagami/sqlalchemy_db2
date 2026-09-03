# sqlalchemy_db2/reflection.py
# Copyright (C) 2026 Hajime Nakagami
#
# This module is released under the MIT License: http://www.opensource.org/licenses/mit-license.php
"""Reflection support for IBM DB2."""
import re

from sqlalchemy import Column, MetaData, Table, sql
from sqlalchemy import types as sa_types
from sqlalchemy.engine import reflection
from sqlalchemy.sql import and_, join, not_


class DB2Reflector:
    ischema = MetaData()

    sys_schemas = Table(
        "SCHEMATA",
        ischema,
        Column("SCHEMANAME", sa_types.Unicode(128), key="schemaname"),
        schema="SYSCAT",
    )

    sys_tables = Table(
        "TABLES",
        ischema,
        Column("TABSCHEMA", sa_types.Unicode(128), key="tabschema"),
        Column("TABNAME", sa_types.Unicode(128), key="tabname"),
        Column("TYPE", sa_types.Unicode(1), key="type"),
        Column("REMARKS", sa_types.Unicode(254), key="remarks"),
        schema="SYSCAT",
    )

    sys_indexes = Table(
        "INDEXES",
        ischema,
        Column("TABSCHEMA", sa_types.Unicode(128), key="tabschema"),
        Column("TABNAME", sa_types.Unicode(128), key="tabname"),
        Column("INDNAME", sa_types.Unicode(128), key="indname"),
        Column("COLNAMES", sa_types.Unicode(1024), key="colnames"),
        Column("UNIQUERULE", sa_types.Unicode(1), key="uniquerule"),
        Column("SYSTEM_REQUIRED", sa_types.SMALLINT, key="system_required"),
        schema="SYSCAT",
    )

    sys_tabconst = Table(
        "TABCONST",
        ischema,
        Column("TABSCHEMA", sa_types.Unicode(128), key="tabschema"),
        Column("TABNAME", sa_types.Unicode(128), key="tabname"),
        Column("CONSTNAME", sa_types.Unicode(128), key="constname"),
        Column("TYPE", sa_types.Unicode(1), key="type"),
        schema="SYSCAT",
    )

    sys_keycoluse = Table(
        "KEYCOLUSE",
        ischema,
        Column("TABSCHEMA", sa_types.Unicode(128), key="tabschema"),
        Column("TABNAME", sa_types.Unicode(128), key="tabname"),
        Column("CONSTNAME", sa_types.Unicode(128), key="constname"),
        Column("COLNAME", sa_types.Unicode(128), key="colname"),
        Column("COLSEQ", sa_types.SMALLINT, key="colseq"),
        schema="SYSCAT",
    )

    sys_foreignkeys = Table(
        "SQLFOREIGNKEYS",
        ischema,
        Column("FK_NAME", sa_types.Unicode(128), key="fkname"),
        Column("FKTABLE_SCHEM", sa_types.Unicode(128), key="fktabschema"),
        Column("FKTABLE_NAME", sa_types.Unicode(128), key="fktabname"),
        Column("FKCOLUMN_NAME", sa_types.Unicode(128), key="fkcolname"),
        Column("PK_NAME", sa_types.Unicode(128), key="pkname"),
        Column("PKTABLE_SCHEM", sa_types.Unicode(128), key="pktabschema"),
        Column("PKTABLE_NAME", sa_types.Unicode(128), key="pktabname"),
        Column("PKCOLUMN_NAME", sa_types.Unicode(128), key="pkcolname"),
        Column("KEY_SEQ", sa_types.Integer, key="colno"),
        schema="SYSIBM",
    )

    sys_columns = Table(
        "COLUMNS",
        ischema,
        Column("TABSCHEMA", sa_types.Unicode(128), key="tabschema"),
        Column("TABNAME", sa_types.Unicode(128), key="tabname"),
        Column("COLNAME", sa_types.Unicode(128), key="colname"),
        Column("COLNO", sa_types.Integer, key="colno"),
        Column("TYPENAME", sa_types.Unicode(128), key="typename"),
        Column("LENGTH", sa_types.Integer, key="length"),
        Column("SCALE", sa_types.Integer, key="scale"),
        Column("DEFAULT", sa_types.Unicode(254), key="defaultval"),
        Column("NULLS", sa_types.Unicode(1), key="nullable"),
        Column("KEYSEQ", sa_types.SMALLINT, key="keyseq"),
        Column("IDENTITY", sa_types.Unicode(1), key="identity"),
        Column("GENERATED", sa_types.Unicode(1), key="generated"),
        Column("REMARKS", sa_types.Unicode(254), key="remarks"),
        schema="SYSCAT",
    )

    sys_views = Table(
        "VIEWS",
        ischema,
        Column("VIEWSCHEMA", sa_types.Unicode(128), key="viewschema"),
        Column("VIEWNAME", sa_types.Unicode(128), key="viewname"),
        Column("TEXT", sa_types.UnicodeText, key="text"),
        schema="SYSCAT",
    )

    sys_sequences = Table(
        "SEQUENCES",
        ischema,
        Column("SEQSCHEMA", sa_types.Unicode(128), key="seqschema"),
        Column("SEQNAME", sa_types.Unicode(128), key="seqname"),
        schema="SYSCAT",
    )

    def __init__(self, dialect):
        self.dialect = dialect
        self.ischema_names = dialect.ischema_names
        self.identifier_preparer = dialect.identifier_preparer

    def normalize_name(self, name):
        if not name:
            return name
        requires_quotes = self.identifier_preparer._requires_quotes(
            name.lower()
        )
        return (
            name.lower()
            if name.upper() == name and not requires_quotes
            else name
        )

    def denormalize_name(self, name):
        if not name:
            return name
        lower_name = name.lower()
        requires_quotes = self.identifier_preparer._requires_quotes(lower_name)
        if lower_name == name and not requires_quotes:
            return name.upper()
        return name

    @property
    def default_schema_name(self):
        return self.dialect.default_schema_name

    def has_table(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        if table_name.startswith("'") and table_name.endswith("'"):
            table_name = table_name.replace("'", "")
            table_name = self.normalize_name(table_name)
        else:
            table_name = self.denormalize_name(table_name)
        if current_schema:
            whereclause = and_(
                self.sys_tables.c.tabschema == current_schema,
                self.sys_tables.c.tabname == table_name,
            )
        else:
            whereclause = self.sys_tables.c.tabname == table_name
        s = sql.select(self.sys_tables.c.tabname).where(whereclause)
        return connection.execute(s).first() is not None

    def has_sequence(self, connection, sequence_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        sequence_name = self.denormalize_name(sequence_name)
        if current_schema:
            whereclause = and_(
                self.sys_sequences.c.seqschema == current_schema,
                self.sys_sequences.c.seqname == sequence_name,
            )
        else:
            whereclause = self.sys_sequences.c.seqname == sequence_name
        s = sql.select(self.sys_sequences.c.seqname).where(whereclause)
        return connection.execute(s).first() is not None

    @reflection.cache
    def get_sequence_names(self, connection, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        sys_seq = self.sys_sequences
        query = (
            sql.select(sys_seq.c.seqname)
            .where(sys_seq.c.seqschema == current_schema)
            .order_by(sys_seq.c.seqschema, sys_seq.c.seqname)
        )
        return [self.normalize_name(r[0]) for r in connection.execute(query)]

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        sysschema = self.sys_schemas
        query = (
            sql.select(sysschema.c.schemaname)
            .where(not_(sysschema.c.schemaname.like("SYS%")))
            .order_by(sysschema.c.schemaname)
        )
        return [
            self.normalize_name(r[0].rstrip())
            for r in connection.execute(query)
        ]

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        systbl = self.sys_tables
        query = (
            sql.select(systbl.c.tabname)
            .where(systbl.c.type == "T")
            .where(systbl.c.tabschema == current_schema)
            .order_by(systbl.c.tabname)
        )
        return [self.normalize_name(r[0]) for r in connection.execute(query)]

    @reflection.cache
    def get_table_comment(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        systbl = self.sys_tables
        query = (
            sql.select(systbl.c.remarks)
            .where(systbl.c.tabschema == current_schema)
            .where(systbl.c.tabname == table_name)
        )
        comment = connection.execute(query).scalar()
        return {"text": comment}

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        query = (
            sql.select(self.sys_views.c.viewname)
            .where(self.sys_views.c.viewschema == current_schema)
            .order_by(self.sys_views.c.viewname)
        )
        return [self.normalize_name(r[0]) for r in connection.execute(query)]

    @reflection.cache
    def get_view_definition(self, connection, viewname, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        viewname = self.denormalize_name(viewname)
        query = (
            sql.select(self.sys_views.c.text)
            .where(self.sys_views.c.viewschema == current_schema)
            .where(self.sys_views.c.viewname == viewname)
        )
        return connection.execute(query).scalar()

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        syscols = self.sys_columns
        query = (
            sql.select(
                syscols.c.colname,
                syscols.c.typename,
                syscols.c.defaultval,
                syscols.c.nullable,
                syscols.c.length,
                syscols.c.scale,
                syscols.c.identity,
                syscols.c.generated,
                syscols.c.remarks,
            )
            .where(
                and_(
                    syscols.c.tabschema == current_schema,
                    syscols.c.tabname == table_name,
                )
            )
            .order_by(syscols.c.colno)
        )
        sa_columns = []
        for r in connection.execute(query):
            raw_type = r[1].upper()
            if raw_type in ("DECIMAL", "NUMERIC"):
                coltype = self.ischema_names.get(raw_type)(
                    int(r[4]), int(r[5])
                )
            elif raw_type in (
                "CHARACTER",
                "CHAR",
                "VARCHAR",
                "GRAPHIC",
                "VARGRAPHIC",
            ):
                coltype = self.ischema_names.get(raw_type)(int(r[4]))
            else:
                coltype_entry = self.ischema_names.get(
                    raw_type, sa_types.NullType
                )
                if isinstance(coltype_entry, type):
                    coltype = coltype_entry()
                else:
                    coltype = coltype_entry
            column_info = {
                "name": self.normalize_name(r[0]),
                "type": coltype,
                "nullable": r[3] == "Y",
                "default": r[2] or None,
                "autoincrement": (r[6] == "Y") and (r[7] != " "),
                "comment": r[8] or None,
            }
            sa_columns.append(column_info)
        return sa_columns

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        sysindexes = self.sys_indexes
        query = (
            sql.select(sysindexes.c.colnames, sysindexes.c.indname)
            .where(
                and_(
                    sysindexes.c.tabschema == current_schema,
                    sysindexes.c.tabname == table_name,
                    sysindexes.c.uniquerule == "P",
                )
            )
            .order_by(sysindexes.c.tabschema, sysindexes.c.tabname)
        )
        pk_columns = []
        pk_name = None
        for r in connection.execute(query):
            cols = [col for col in re.split(r"[+-]", r[0]) if col]
            pk_columns.extend(cols)
            if not pk_name:
                pk_name = self.normalize_name(r[1])
        return {
            "constrained_columns": [
                self.normalize_name(col) for col in pk_columns
            ],
            "name": pk_name,
        }

    @reflection.cache
    def get_primary_keys(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        syscols = self.sys_columns
        query = (
            sql.select(syscols.c.colname)
            .where(
                and_(
                    syscols.c.tabschema == current_schema,
                    syscols.c.tabname == table_name,
                    syscols.c.keyseq > 0,
                )
            )
            .order_by(syscols.c.keyseq)
        )
        return [self.normalize_name(r[0]) for r in connection.execute(query)]

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        default_schema = self.default_schema_name
        current_schema = self.denormalize_name(schema or default_schema)
        normalized_default_schema = self.normalize_name(default_schema)
        table_name = self.denormalize_name(table_name)
        sysfkeys = self.sys_foreignkeys
        query = (
            sql.select(
                sysfkeys.c.fkname,
                sysfkeys.c.fktabschema,
                sysfkeys.c.fktabname,
                sysfkeys.c.fkcolname,
                sysfkeys.c.pkname,
                sysfkeys.c.pktabschema,
                sysfkeys.c.pktabname,
                sysfkeys.c.pkcolname,
            )
            .where(
                and_(
                    sysfkeys.c.fktabschema == current_schema,
                    sysfkeys.c.fktabname == table_name,
                )
            )
            .order_by(sysfkeys.c.fkname, sysfkeys.c.colno)
        )
        fschema = {}
        for r in connection.execute(query):
            fk_name = r[0]
            if fk_name not in fschema:
                referred_schema = self.normalize_name(r[5])
                if schema is None and referred_schema == normalized_default_schema:
                    referred_schema = None
                fschema[fk_name] = {
                    "name": self.normalize_name(fk_name),
                    "constrained_columns": [self.normalize_name(r[3])],
                    "referred_schema": referred_schema,
                    "referred_table": self.normalize_name(r[6]),
                    "referred_columns": [self.normalize_name(r[7])],
                }
            else:
                fschema[fk_name]["constrained_columns"].append(
                    self.normalize_name(r[3])
                )
                fschema[fk_name]["referred_columns"].append(
                    self.normalize_name(r[7])
                )
        return list(fschema.values())

    @reflection.cache
    def get_incoming_foreign_keys(
        self, connection, table_name, schema=None, **kw
    ):
        default_schema = self.default_schema_name
        current_schema = self.denormalize_name(schema or default_schema)
        normalized_default_schema = self.normalize_name(default_schema)
        table_name = self.denormalize_name(table_name)
        sysfkeys = self.sys_foreignkeys
        query = (
            sql.select(
                sysfkeys.c.fkname,
                sysfkeys.c.fktabschema,
                sysfkeys.c.fktabname,
                sysfkeys.c.fkcolname,
                sysfkeys.c.pkname,
                sysfkeys.c.pktabschema,
                sysfkeys.c.pktabname,
                sysfkeys.c.pkcolname,
            )
            .where(
                and_(
                    sysfkeys.c.pktabschema == current_schema,
                    sysfkeys.c.pktabname == table_name,
                )
            )
            .order_by(sysfkeys.c.colno)
        )
        fschema = {}
        for r in connection.execute(query):
            fk_name = r[0]
            if fk_name not in fschema:
                constrained_schema = self.normalize_name(r[1])
                if (
                    schema is None
                    and constrained_schema == normalized_default_schema
                ):
                    constrained_schema = None
                fschema[fk_name] = {
                    "name": self.normalize_name(fk_name),
                    "constrained_schema": constrained_schema,
                    "constrained_table": self.normalize_name(r[2]),
                    "constrained_columns": [self.normalize_name(r[3])],
                    "referred_schema": schema,
                    "referred_table": self.normalize_name(r[6]),
                    "referred_columns": [self.normalize_name(r[7])],
                }
            else:
                fschema[fk_name]["constrained_columns"].append(
                    self.normalize_name(r[3])
                )
                fschema[fk_name]["referred_columns"].append(
                    self.normalize_name(r[7])
                )
        return list(fschema.values())

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        sysidx = self.sys_indexes
        query = (
            sql.select(
                sysidx.c.indname,
                sysidx.c.colnames,
                sysidx.c.uniquerule,
                sysidx.c.system_required,
            )
            .where(
                and_(
                    sysidx.c.tabschema == current_schema,
                    sysidx.c.tabname == table_name,
                )
            )
            .order_by(sysidx.c.tabname)
        )
        indexes = []
        for r in connection.execute(query):
            index_name = r[0]
            column_text = r[1]
            unique_rule = r[2]
            system_required = r[3]
            if unique_rule == "P":
                continue
            if unique_rule == "U" and system_required != 0:
                continue
            if "sqlnotapplicable" in column_text.lower():
                continue
            normalized_columns = [
                self.normalize_name(col)
                for col in re.split(r"[+-]", column_text)
                if col
            ]
            indexes.append({
                "name": self.normalize_name(index_name),
                "column_names": normalized_columns,
                "unique": unique_rule == "U",
            })
        return indexes

    @reflection.cache
    def get_unique_constraints(self, connection, table_name, schema=None, **kw):
        current_schema = self.denormalize_name(
            schema or self.default_schema_name
        )
        table_name = self.denormalize_name(table_name)
        syskeycol = self.sys_keycoluse
        sysconst = self.sys_tabconst
        query = (
            sql.select(syskeycol.c.constname, syskeycol.c.colname)
            .select_from(
                join(
                    syskeycol,
                    sysconst,
                    and_(
                        syskeycol.c.constname == sysconst.c.constname,
                        syskeycol.c.tabschema == sysconst.c.tabschema,
                        syskeycol.c.tabname == sysconst.c.tabname,
                    ),
                )
            )
            .where(
                and_(
                    sysconst.c.tabname == table_name,
                    sysconst.c.tabschema == current_schema,
                    sysconst.c.type == "U",
                )
            )
            .order_by(syskeycol.c.constname, syskeycol.c.colseq)
        )
        unique_consts = []
        curr_const = None
        for r in connection.execute(query):
            constraint_name = r[0]
            column_name = self.normalize_name(r[1])
            if curr_const == constraint_name:
                unique_consts[-1]["column_names"].append(column_name)
            else:
                curr_const = constraint_name
                unique_consts.append({
                    "name": self.normalize_name(curr_const),
                    "column_names": [column_name],
                })
        return unique_consts
