"""Prepare restricted service roles after Flyway, preserving existing credentials."""
import os

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


def initialize():
    database = os.environ["POSTGRES_DB"]
    roles = {}
    for key, role in (("DATABASE_URL", "agent"), ("RAG_DATABASE_URL", "rag_ro"),
                      ("RAG_INDEX_DATABASE_URL", "rag_indexer")):
        dsn = os.environ[key]
        info = conninfo_to_dict(dsn)
        if (info.get("user") != role or info.get("dbname") != database
                or info.get("host") != "postgres" or not info.get("password")):
            raise ValueError(f"{key} must use {role}, the configured DB, host postgres and a password")
        roles[role] = (dsn, info["password"])

    with psycopg.connect(host="postgres", dbname=database, user=os.environ["POSTGRES_USER"],
                         password=os.environ["POSTGRES_PASSWORD"]) as conn:
        if conn.execute("SELECT to_regclass('rag.chunks')").fetchone()[0] is None:
            raise RuntimeError("Flyway must finish before service accounts are initialized")
        vector_schema = conn.execute("""
            SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            WHERE e.extname='vector'
        """).fetchone()[0]
        for role, (_, password) in roles.items():
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)))
        conn.execute("GRANT USAGE, CREATE ON SCHEMA agent TO agent")
        conn.execute("ALTER ROLE agent SET search_path TO agent, pg_catalog")
        conn.execute("GRANT USAGE ON SCHEMA rag TO rag_ro, rag_indexer")
        conn.execute("GRANT SELECT ON ALL TABLES IN SCHEMA rag TO rag_ro, rag_indexer")
        conn.execute("GRANT INSERT, UPDATE, DELETE ON rag.documents, rag.chunks TO rag_indexer")
        conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rag TO rag_indexer")
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO rag_ro, rag_indexer").format(
            sql.Identifier(vector_schema)))
        for role in ("rag_ro", "rag_indexer"):
            conn.execute(sql.SQL("ALTER ROLE {} SET search_path TO pg_catalog, rag, {}, public").format(
                sql.Identifier(role), sql.Identifier(vector_schema)))
        conn.execute("ALTER ROLE rag_ro SET default_transaction_read_only = on")

    # Verify effective access using each service's actual credentials, including on repeated startup.
    for role, (dsn, _) in roles.items():
        with psycopg.connect(dsn, connect_timeout=10) as conn:
            assert not conn.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='app' AND c.relkind IN ('r', 'p')
                      AND has_table_privilege(current_user, c.oid, 'SELECT,INSERT,UPDATE,DELETE')
                )
            """).fetchone()[0]
            if role == "agent":
                assert conn.execute("SELECT current_schema()").fetchone()[0] == "agent"
                assert conn.execute("SELECT has_schema_privilege(current_user, 'agent', 'CREATE')").fetchone()[0]
            else:
                assert conn.execute("SELECT has_table_privilege(current_user, 'rag.chunks', 'SELECT')").fetchone()[0]
                writable = conn.execute("SELECT has_table_privilege(current_user, 'rag.chunks', 'INSERT')").fetchone()[0]
                assert writable == (role == "rag_indexer")
    print("Service DB roles and permissions verified")


if __name__ == "__main__":
    initialize()
