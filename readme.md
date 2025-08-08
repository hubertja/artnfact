# Artnfact MCP

This is WIP, please use accordingly :)

## Setup

* Clone this repo
* Install [uv](https://github.com/astral-sh/uv)
* Setup your DBs in `db_conf.json` (can reference .env - see example)
* Write your specific data instructions in a `artnfact.md` file, at the root of the repo.
* Then make the MCP available to your favorite client:
  In `.cursor/mcp.json` for Cursor or in `~/Library/Application Support/Claude/claude_desktop_config.json` for Claude Desktop:
  ```
  {
      "mcpServers": {
        "artnfact": {
          "command": "<ABSOLUTE_PATH_TO_YOUR_UV>
          "args": ["run", "--project", "<ABSOLUTE_PATH_TO_THIS_REPO>", "artnfact-mcp"],
        }
      }
  }
  ```
