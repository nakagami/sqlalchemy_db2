sqlalchemy_db2
==============

A `SQLAlchemy <https://www.sqlalchemy.org/>`_ dialect for IBM DB2,
backed by `pydrda <https://github.com/nakagami/pydrda>`_ (a pure Python
DRDA protocol driver).

The SQL compilation and reflection layer is reused from
`ibm_db_sa <https://github.com/ibmdb/python-ibmdbsa>`_, so no IBM CLI
driver is required.

Usage
-----

Sync::

    from sqlalchemy import create_engine

    engine = create_engine(
        "db2+syn://user:pass@host:50000/database"
    )

Async::

    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        "db2+asyn://user:pass@host:50000/database"
    )

Optional connect parameters may be passed in the query string, e.g.
``?use_ssl=true&timeout=10&ssl_client_cert_path=/path/to/cert.pem``.
