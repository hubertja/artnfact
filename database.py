import logging
from typing import Any
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from psycopg_pool import AsyncConnectionPool
from psycopg.conninfo import make_conninfo


class Database:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, host: str, user: str, password: str, dbname: str, port: int
    ) -> AsyncIterator["Database"]:
        dsn = make_conninfo(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
        )

        try:
            async with AsyncConnectionPool(
                conninfo=dsn,
                min_size=1,
                max_size=10,
                timeout=10,
                max_idle=60,
            ) as pool:
                # Health check so failures happen on boot
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()

                yield cls(pool)
        except Exception as exc:  # noqa: BLE001
            logging.error(
                "Failed to open PostgreSQL pool. Check DATABASE_URL/PG* env vars. Error: %s",
                exc,
            )
            # Re-raise to fail fast
            raise

    async def query(
        self, sql: str = "SELECT 'Query result'::text", *params: Any
    ) -> list[dict[str, str]]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params if params else None)
                rows = await cur.fetchall()
                if not rows:
                    return []
                return [
                    {str(col.name): str(val) for col, val in zip(cur.description, row)}
                    for row in rows
                ]
