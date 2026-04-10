"""
Tool Registry & Executor
Each tool: description, input_schema, async handler
"""
 
import asyncio
import json
import math
import os
import subprocess
import tempfile
import httpx
 
# ─────────────────────────────────────────────
# Tool Handlers
# ─────────────────────────────────────────────
 
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key needed)."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
 
        results = []
 
        # Abstract (direct answer)
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")
 
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text']}")
 
        if not results:
            return f"No results found for: {query}"
 
        return "\n".join(results)
 
    except Exception as e:
        return f"Search failed: {str(e)}"
 
 
async def calculator(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    try:
        # Safe math eval — whitelist approach
        allowed = {
            k: getattr(math, k)
            for k in dir(math)
            if not k.startswith("_")
        }
        allowed["abs"] = abs
        allowed["round"] = round
        allowed["min"] = min
        allowed["max"] = max
        allowed["sum"] = sum
        allowed["pow"] = pow
 
        # Strip dangerous tokens
        safe_expr = re.sub(r"[^0-9+\-*/().,\s%a-zA-Z_]", "", expression)
        result = eval(safe_expr, {"__builtins__": {}}, allowed)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"
 
 
async def file_reader(path: str) -> str:
    """Read a file from disk (within allowed directories)."""
    try:
        # Restrict to safe directories
        safe_dirs = ["/tmp", os.path.expanduser("~/uploads")]
        abs_path = os.path.abspath(path)
 
        allowed = any(abs_path.startswith(d) for d in safe_dirs)
        if not allowed:
            return f"Access denied. Only files in {safe_dirs} are allowed."
 
        if not os.path.exists(abs_path):
            return f"File not found: {path}"
 
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(8000)  # Limit to 8k chars
 
        return f"File contents of {path}:\n\n{content}"
    except Exception as e:
        return f"File read error: {str(e)}"
 
 
async def python_executor(code: str) -> str:
    """Execute Python code in a sandboxed subprocess."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as f:
            f.write(code)
            tmp_path = f.name
 
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
 
        os.unlink(tmp_path)
 
        output = ""
        if result.stdout:
            output += f"stdout:\n{result.stdout}"
        if result.stderr:
            output += f"\nstderr:\n{result.stderr}"
        if not output:
            output = "Code ran with no output."
 
        return output[:3000]  # Limit
 
    except subprocess.TimeoutExpired:
        return "Execution timed out (15s limit)."
    except Exception as e:
        return f"Execution error: {str(e)}"
 
 
async def memory_search(query: str, chat_id: str = "default") -> str:
    """Search long-term semantic memory for relevant past context."""
    try:
        from memory import MemoryManager
        mm = MemoryManager()
        results = mm.search(chat_id, query, k=3)
        if not results:
            return "No relevant memories found."
        return "Relevant past context:\n" + "\n---\n".join(results)
    except Exception as e:
        return f"Memory search failed: {str(e)}"
 
 
async def datetime_tool(timezone: str = "UTC") -> str:
    """Get current date and time."""
    from datetime import datetime, timezone as tz
    import zoneinfo
    try:
        if timezone == "UTC":
            now = datetime.now(tz.utc)
        else:
            zi = zoneinfo.ZoneInfo(timezone)
            now = datetime.now(zi)
        return f"Current datetime ({timezone}): {now.strftime('%A, %B %d, %Y %H:%M:%S %Z')}"
    except Exception:
        now = datetime.utcnow()
        return f"Current datetime (UTC): {now.strftime('%A, %B %d, %Y %H:%M:%S')}"
 
 
# ─────────────────────────────────────────────
# Tool Registry
# ─────────────────────────────────────────────
 
import re  # needed by calculator
 
TOOLS = {
    "web_search": {
        "description": "Search the web for current information, facts, news, and general knowledge.",
        "input_schema": {"query": "string (search query)", "max_results": "int (optional, default 5)"},
        "handler": web_search,
    },
    "calculator": {
        "description": "Evaluate mathematical expressions. Supports +, -, *, /, **, sqrt, sin, cos, log, etc.",
        "input_schema": {"expression": "string (math expression e.g. '2 ** 10 + sqrt(144)')"},
        "handler": calculator,
    },
    "file_reader": {
        "description": "Read the contents of a file. Only files in /tmp or ~/uploads are accessible.",
        "input_schema": {"path": "string (absolute file path)"},
        "handler": file_reader,
    },
    "python_executor": {
        "description": "Execute Python code and return the output. Use for data processing, computations, and analysis.",
        "input_schema": {"code": "string (valid Python code)"},
        "handler": python_executor,
    },
    "memory_search": {
        "description": "Search long-term memory for relevant past conversations and context.",
        "input_schema": {"query": "string", "chat_id": "string (optional)"},
        "handler": memory_search,
    },
    "datetime": {
        "description": "Get the current date and time for a given timezone.",
        "input_schema": {"timezone": "string (e.g. 'UTC', 'Asia/Kolkata', 'America/New_York')"},
        "handler": datetime_tool,
    },
}
 
 
async def run_tool(tool_name: str, tool_input: dict) -> str:
    handler = TOOLS[tool_name]["handler"]
    return await handler(**tool_input)
 