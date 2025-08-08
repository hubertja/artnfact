from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from dotenv import load_dotenv
from database import Database
from utils import load_db_config

load_dotenv()


@dataclass
class AppContext:
    dbs: dict[str, Database]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    # Load database configuration from JSON file
    config = load_db_config()
    databases_config = config["databases"]
    
    app_context_dbs = {}
    db_connections = []
    
    try:
        # Connect to all databases
        for db_name, db_config in databases_config.items():
            db_connection = Database.connect(
                host=db_config["host"],
                user=db_config["user"],
                password=db_config["password"],
                dbname=db_config["dbname"],
                port=db_config["port"]
            )
            connected_db = await db_connection.__aenter__()
            app_context_dbs[db_name] = connected_db
            db_connections.append((db_connection, connected_db))
        
        # Yield the app context with all connections
        yield AppContext(dbs=app_context_dbs)
    
    finally:
        # Clean up all database connections
        for db_connection, _ in db_connections:
            try:
                await db_connection.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing database connection: {e}")


mcp = FastMCP("Artnfact", lifespan=app_lifespan)


@mcp.tool()
async def query_db(db_name: str, sql_query: str, ctx: Context) -> list[dict[str, str]]:
    """Run the provided SQL query on the provided PostgreSQL DB and returns the results."""
    db = ctx.request_context.lifespan_context.dbs[db_name]
    return await db.query(sql_query)


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
