"""Example showing lifespan support with PostgreSQL using an async pool."""

import os
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from psycopg_pool import AsyncConnectionPool
from psycopg.conninfo import make_conninfo
from dotenv import load_dotenv


load_dotenv()

class Database:

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator["Database"]:
        dsn = make_conninfo(
            dbname=os.environ.get("PGDATABASE", "postgres"),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", "postgres"),
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
        )

        try:
            async with AsyncConnectionPool(
                conninfo=dsn,
                min_size=int(os.environ.get("PGPOOL_MIN_SIZE", "1")),
                max_size=int(os.environ.get("PGPOOL_MAX_SIZE", "10")),
                timeout=float(os.environ.get("PGPOOL_TIMEOUT", "10")),
                max_idle=int(os.environ.get("PGPOOL_MAX_IDLE", "60")),
            ) as pool:
                # Health check so failures happen on boot
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()
                
                yield cls(pool)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to open PostgreSQL pool. Check DATABASE_URL/PG* env vars. Error: %s", exc)
            # Re-raise to fail fast
            raise

    async def query(self, sql: str = "SELECT 'Query result'::text", *params: Any) -> list[dict[str, str]]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params if params else None)
                rows = await cur.fetchall()
                if not rows:
                    return []
                return [ {str(col.name): str(val) for col, val in zip(cur.description, row)} for row in rows ]



@dataclass
class AppContext:
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    async with Database.connect() as db:
        yield AppContext(db=db)



mcp = FastMCP("Artnfact", lifespan=app_lifespan)


@mcp.tool()
async def query_db(sql_query: str,ctx: Context) -> list[dict[str, str]]:
    """Run a test query against PostgreSQL and return its result."""
    db = ctx.request_context.lifespan_context.db
    return await db.query(sql_query)


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()