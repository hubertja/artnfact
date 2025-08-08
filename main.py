import sys
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

# Add the current directory to Python path to find local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "db_conf.json"
    )
    config = load_db_config(config_path)
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
                port=db_config["port"],
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


@mcp.tool()
def plan_answer_to_data_question() -> str:
    """Returns the optimal plan to answer Data Analysis questions that requires checking our internal DBs data.
    Leverage this when asked about "users" without any other context, about M1, AskM1, "chats", "texts", "calls", "meetings", "todos", "emails", "notes", "contacts", "etc."""
    artnfact_md_content = None
    if os.path.exists("artnfact.md"):
        with open("artnfact.md", "r") as file:
            artnfact_md_content = file.read()
    plan = """I see the question is a Data Analysis question that requires checking our internal DBs data. I will:
* Think deeply on the right SQL query given our internal data context (See below).
* Execute the SQL query/queries on the relevant DBs using the dedicated tool I have for this
* Think about the best chart or table to display the results. I keep things simple and efficient (bar chart, line chart, table, etc.)
* Provide the result in a simple code snippet"""
    if artnfact_md_content:
        plan += f"""
---------------------------------
INTERNAL DATA CONTEXT
---------------------------------
{artnfact_md_content}
"""
    return plan


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
