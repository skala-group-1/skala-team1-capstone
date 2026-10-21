"""Create dedicated RAG roles after Flyway. Requires RAG_ADMIN_DATABASE_URL."""
import os
from pathlib import Path
import secrets
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


def bootstrap(admin_dsn, target):
    target = Path(target)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite credentials: {target}")
    info = conninfo_to_dict(admin_dsn)
    credentials = {}
    with psycopg.connect(admin_dsn) as conn:
        if conn.execute("SELECT to_regclass('rag.chunks')").fetchone()[0] is None:
            raise RuntimeError("Run docker compose run --rm db-seed first")
        vector_schema = conn.execute("""
            SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
            WHERE e.extname='vector'
        """).fetchone()[0]
        for role in ("rag_ro", "rag_indexer"):
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                raise RuntimeError(f"Role {role} already exists; configure its DSN manually")
            password = secrets.token_urlsafe(32)
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(password)))
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA rag TO {}").format(sql.Identifier(role)))
            conn.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA rag TO {}").format(
                sql.Identifier(role)))
            # Flyway may install the vector type/operators in app rather than public.
            # Schema USAGE grants no access to the business tables themselves.
            conn.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(vector_schema), sql.Identifier(role)))
            conn.execute(sql.SQL("ALTER ROLE {} SET search_path TO pg_catalog, rag, {}, public").format(
                sql.Identifier(role), sql.Identifier(vector_schema)))
            credentials[role] = password
        conn.execute("GRANT INSERT, UPDATE, DELETE ON rag.documents, rag.chunks TO rag_indexer")
        conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA rag TO rag_indexer")
        conn.execute("ALTER ROLE rag_ro SET default_transaction_read_only = on")
        lines = ["USE_STUB=false"]
        for key, role in (("RAG_DATABASE_URL", "rag_ro"), ("RAG_INDEX_DATABASE_URL", "rag_indexer")):
            lines.append(f"{key}=postgresql://{role}:{credentials[role]}@"
                         f"{info.get('host', 'localhost')}:{info.get('port', '5432')}/"
                         f"{quote(info['dbname'], safe='')}")
        # Credentials never appear in stdout and are excluded by .gitignore.
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write("\n".join(lines) + "\n")
    print("Created RAG reader/writer roles and private local configuration")


if __name__ == "__main__":
    bootstrap(os.environ["RAG_ADMIN_DATABASE_URL"],
              Path(__file__).resolve().parents[1] / ".env.rag")
