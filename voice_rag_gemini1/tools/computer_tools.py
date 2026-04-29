"""
tools/computer_tools.py
All tools the Claude agent can call to control your computer.
Each tool is a plain Python function decorated with metadata the agent uses.
"""
from __future__ import annotations
import os
import subprocess
import platform
import datetime
import webbrowser
from pathlib import Path
from typing import Any

from rich.console import Console
console = Console()

# ─── Tool registry ───────────────────────────────────────────────────────────
# Maps tool name → (function, Claude tool definition dict)

TOOL_DEFINITIONS: list[dict] = []
TOOL_FUNCTIONS:   dict[str, callable] = {}


def register_tool(func):
    """Decorator: registers a function as an agent tool."""
    TOOL_FUNCTIONS[func.__name__] = func
    return func


# ─── System tools ─────────────────────────────────────────────────────────────

@register_tool
def get_current_time() -> str:
    """Return the current date and time."""
    now = datetime.datetime.now()
    return now.strftime("Today is %A, %B %d %Y. The time is %I:%M %p.")


@register_tool
def open_application(app_name: str) -> str:
    """Open a desktop application by name (e.g. 'chrome', 'notepad', 'calculator')."""
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(app_name)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
        return f"Opened {app_name} successfully."
    except Exception as e:
        return f"Could not open {app_name}: {e}"


@register_tool
def run_shell_command(command: str) -> str:
    """Run a shell command and return its output. Use with caution."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=15
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 15 seconds."
    except Exception as e:
        return f"Error: {e}"


@register_tool
def read_file(file_path: str) -> str:
    """Read and return the contents of a text file."""
    try:
        p = Path(file_path).expanduser()
        if not p.exists():
            return f"File not found: {file_path}"
        if p.stat().st_size > 50_000:
            return p.read_text(encoding="utf-8", errors="ignore")[:50_000] + "\n[truncated]"
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Error reading file: {e}"


@register_tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file (creates or overwrites)."""
    try:
        p = Path(file_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"File written: {file_path} ({len(content)} chars)"
    except Exception as e:
        return f"Error writing file: {e}"


@register_tool
def list_directory(folder_path: str = ".") -> str:
    """List files and folders in a directory."""
    try:
        p = Path(folder_path).expanduser()
        if not p.exists():
            return f"Directory not found: {folder_path}"
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        lines = []
        for item in items[:60]:
            prefix = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{item.name}")
        if len(list(p.iterdir())) > 60:
            lines.append("... (truncated)")
        return "\n".join(lines) or "(empty directory)"
    except Exception as e:
        return f"Error: {e}"


@register_tool
def web_search(query: str) -> str:
    """Search the web using DuckDuckGo and return top results."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=4):
                results.append(f"• {r['title']}\n  {r['href']}\n  {r['body'][:200]}")
        return "\n\n".join(results) if results else "No results found."
    except ImportError:
        return "duckduckgo-search not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"


@register_tool
def open_url(url: str) -> str:
    """Open a URL in the default web browser."""
    webbrowser.open(url)
    return f"Opened {url} in browser."


@register_tool
def take_screenshot(save_path: str = "screenshot.png") -> str:
    """Take a screenshot of the current screen and save it."""
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(save_path)
        return f"Screenshot saved to {save_path}"
    except ImportError:
        return "pyautogui not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"Screenshot error: {e}"


@register_tool
def type_text(text: str) -> str:
    """Type text using the keyboard at the current cursor position."""
    try:
        import pyautogui
        import time
        time.sleep(0.5)
        pyautogui.typewrite(text, interval=0.03)
        return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"
    except ImportError:
        return "pyautogui not installed."
    except Exception as e:
        return f"Error: {e}"


@register_tool
def get_clipboard() -> str:
    """Return current clipboard content."""
    try:
        import pyperclip
        return pyperclip.paste() or "(clipboard is empty)"
    except ImportError:
        return "pyperclip not installed. Run: pip install pyperclip"


@register_tool
def set_clipboard(text: str) -> str:
    """Set clipboard content."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Copied to clipboard."
    except ImportError:
        return "pyperclip not installed."


@register_tool
def get_system_info() -> str:
    """Return basic system information (OS, CPU, memory, disk)."""
    import psutil, platform
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"CPU cores: {psutil.cpu_count()} | Usage: {psutil.cpu_percent(interval=1)}%\n"
            f"RAM: {mem.used/1e9:.1f} GB used / {mem.total/1e9:.1f} GB total ({mem.percent}%)\n"
            f"Disk: {disk.used/1e9:.1f} GB used / {disk.total/1e9:.1f} GB total ({disk.percent}%)"
        )
    except ImportError:
        return "psutil not installed. Run: pip install psutil"


# ─── Claude tool schema builder ───────────────────────────────────────────────

def build_claude_tools() -> list[dict]:
    """Generate the tools list in Anthropic API format."""
    schemas = {
        "get_current_time": {
            "description": "Get the current date and time.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "open_application": {
            "description": "Open a desktop application by name.",
            "input_schema": {
                "type": "object",
                "properties": {"app_name": {"type": "string", "description": "Application name, e.g. 'chrome', 'vscode', 'notepad'"}},
                "required": ["app_name"],
            },
        },
        "run_shell_command": {
            "description": "Run a shell/terminal command and return output.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command to execute"}},
                "required": ["command"],
            },
        },
        "read_file": {
            "description": "Read and return the contents of a file.",
            "input_schema": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Path to the file"}},
                "required": ["file_path"],
            },
        },
        "write_file": {
            "description": "Write or create a file with given content.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
        },
        "list_directory": {
            "description": "List files in a directory.",
            "input_schema": {
                "type": "object",
                "properties": {"folder_path": {"type": "string", "description": "Directory path (default: current dir)"}},
                "required": [],
            },
        },
        "web_search": {
            "description": "Search the web using DuckDuckGo.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
        "open_url": {
            "description": "Open a URL in the default web browser.",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
        "take_screenshot": {
            "description": "Take a screenshot of the screen.",
            "input_schema": {
                "type": "object",
                "properties": {"save_path": {"type": "string", "description": "Where to save the PNG (default: screenshot.png)"}},
                "required": [],
            },
        },
        "type_text": {
            "description": "Type text at the current cursor position.",
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        "get_clipboard": {
            "description": "Get current clipboard content.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        "set_clipboard": {
            "description": "Copy text to the clipboard.",
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        "get_system_info": {
            "description": "Get CPU, RAM, and disk usage information.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    }
    tools = []
    for name, schema in schemas.items():
        tools.append({"name": name, **schema})
    return tools
