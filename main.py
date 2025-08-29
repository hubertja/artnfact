import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
#import uuid

from mcp.server.fastmcp import Context, FastMCP
from dotenv import load_dotenv
from database import Database
from utils import load_db_config
#import pandas as pd

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


mcp = FastMCP("Artnfact", lifespan=app_lifespan, instructions="Use the tools provided when the user asks for questions that require structured data analysis (SQL queries on internal DBs).")

ANALYSIS_PROMPT = """# Identity
You are a top data scientist, very sharp and impact-driven. 

# Goal
Let's perform a data analysis answering the question below:
```
{query}
```

# Instructions

* Explain how you will approach the question, with the trade off decisions you make

* Execute the SQL queries on the relevant DBs using the dedicated query_db tool
  Keep the queries as simple as possible.
  Make sure to leverage the contextual knowledge provided by the relevant tool before executing any SQL queries.
  Never use `created_at` or `updated_at` as meaningful columns business-wise: they are technical artefacts only.

* Show the results:
  - If on Cursor: as a table with a title and a subtitle
  - Otherwise: as a code canvas implementing a chart (with a title and a subtitle as well)
    The chart should be simple ("The Economist"-style): line or bar chart will do in 99% of cases.
  In each case:
    - The title is short and shows the takeaway.
    - The subtitle is also short and gives a bit more details.
    - There's nothing more and things are kept minimal.

"""


@mcp.prompt(title="Analyze", description="Run a data analysis")
def analyze(query: str) -> str:
    return ANALYSIS_PROMPT.format(query=query)


@mcp.tool()
def get_behavioral_instructions_to_answer_data_questions(query: str) -> str:
    """Provides key information to answer data questions in an optimal way in the context of the company.
    Run this tool before executing SQL queries or getting contextual knowledge about the DBs"""
    return ANALYSIS_PROMPT.format(query=query)


@mcp.tool()
def get_product_and_data_contextual_knowledge() -> str:
    """Provides key product and data contextual information allowing to perform accurate SQL queries on DBs.
    Run this tool before executing SQL queries with query_db, and after fetching behavioral instructions to answer data questions."""
    artnfact_md_content = None
    artnfact_md_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "artnfact.md"
    )
    if os.path.exists(artnfact_md_path):
        with open(artnfact_md_path, "r") as file:
            artnfact_md_content = file.read()
            return artnfact_md_content
    return "No contextual knowledge found."


@mcp.tool()
async def query_db(db_name: str, sql_query: str, ctx: Context) -> list[dict[str, str]]:
    """Run the provided SQL query on the provided PostgreSQL DB.
    Returns the data as a list of dictionaries.
    Make sure you have fetched the behavioral instructions to answer data questions and the contextual knowledge about the DBs before executing this tool."""
    db = ctx.request_context.lifespan_context.dbs[db_name]
    return await db.query(sql_query)


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
