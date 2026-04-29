"""
core/agent.py
Gemini-powered agentic brain.
Full pipeline: RAG context injection → Gemini API → tool execution →
multi-turn reasoning → final spoken response.

Supports: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash
"""
from __future__ import annotations
import os
import json
from typing import Optional, Callable

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
from rich.console import Console
from rich.panel import Panel

from tools.computer_tools import TOOL_FUNCTIONS
from rag.knowledge_base import KnowledgeBase

console = Console()


SYSTEM_PROMPT = """You are {name}, an intelligent voice-controlled desktop AI assistant.
You can control the user's computer, search the web, manage files, and answer questions.
You have access to a personal knowledge base that you will use when relevant.

Guidelines:
- Be concise. Responses will be spoken aloud — keep them short and clear.
- Always use tools proactively when the task requires computer interaction.
- When using knowledge base context, synthesise it naturally — don't quote it verbatim.
- If a task could harm the system (e.g. deleting important files), ask for confirmation first.
- Be friendly, efficient, and natural. You are a voice assistant, not a chatbot.
- After completing a tool task, give a brief spoken confirmation.
"""


# ── Build Gemini tool declarations from our tool registry ─────────────────────

def _build_gemini_tools() -> list[Tool]:
    """Convert computer_tools registry into Gemini FunctionDeclaration format."""
    schemas = {
        "get_current_time": {
            "description": "Get the current date and time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        "open_application": {
            "description": "Open a desktop application by name (e.g. chrome, notepad, vscode).",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string", "description": "Application name to open"}},
                "required": ["app_name"],
            },
        },
        "run_shell_command": {
            "description": "Run a shell/terminal command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command to execute"}},
                "required": ["command"],
            },
        },
        "read_file": {
            "description": "Read and return the contents of a text file.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Path to the file"}},
                "required": ["file_path"],
            },
        },
        "write_file": {
            "description": "Write or create a file with given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to write"},
                    "content":   {"type": "string", "description": "Content to write"},
                },
                "required": ["file_path", "content"],
            },
        },
        "list_directory": {
            "description": "List files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {"folder_path": {"type": "string", "description": "Directory path (default: current)"}},
                "required": [],
            },
        },
        "web_search": {
            "description": "Search the web using DuckDuckGo and return top results.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
        "open_url": {
            "description": "Open a URL in the default web browser.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL to open"}},
                "required": ["url"],
            },
        },
        "take_screenshot": {
            "description": "Take a screenshot of the current screen and save it.",
            "parameters": {
                "type": "object",
                "properties": {"save_path": {"type": "string", "description": "PNG save path (default: screenshot.png)"}},
                "required": [],
            },
        },
        "type_text": {
            "description": "Type text using the keyboard at the current cursor position.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Text to type"}},
                "required": ["text"],
            },
        },
        "get_clipboard": {
            "description": "Get the current clipboard content.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        "set_clipboard": {
            "description": "Copy text to the clipboard.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Text to copy"}},
                "required": ["text"],
            },
        },
        "get_system_info": {
            "description": "Get CPU, RAM, and disk usage information.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }

    declarations = []
    for name, schema in schemas.items():
        params = schema["parameters"]
        if not params.get("properties"):
            params["properties"] = {}
        declarations.append(
            FunctionDeclaration(
                name=name,
                description=schema["description"],
                parameters=params,
            )
        )
    return [Tool(function_declarations=declarations)]


# ── Main agent class ───────────────────────────────────────────────────────────

class VoiceAgent:
    """Gemini-powered voice agent with RAG and computer-use tools."""

    def __init__(
        self,
        name: str = "Jarvis",
        model: str = "gemini-2.0-flash-lite",
        knowledge_base: Optional[KnowledgeBase] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_response: Optional[Callable[[str], None]] = None,
        rag_top_k: int = 4,
    ):
        self.name        = name
        self.model_name  = model
        self.kb          = knowledge_base
        self.on_tool_call = on_tool_call
        self.on_response  = on_response
        self.rag_top_k   = rag_top_k
        self.chat_session = None

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set.\n"
                "Get your free key at: https://aistudio.google.com/app/apikey\n"
                "Then add GEMINI_API_KEY=your_key to your .env file."
            )

        genai.configure(api_key=api_key)
        self._tools = _build_gemini_tools()
        self._init_chat()

        console.print(f"[green]✓ Gemini agent '{name}' ready[/green] (model: {model})")

    def _init_chat(self):
        """Create or reset the Gemini stateful chat session."""
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_PROMPT.format(name=self.name),
            tools=self._tools,
            generation_config=genai.GenerationConfig(
                max_output_tokens=300,    # short spoken answers — faster
                temperature=0.7,
            ),
        )
        self.chat_session = model.start_chat(history=[])

    # ─── Main entry point ─────────────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        """
        Process a user utterance through RAG + Gemini agentic loop.
        Returns final text response (passed to TTS).
        """
        if not user_input.strip():
            return ""

        # 1. Retrieve RAG context
        rag_context = ""
        if self.kb:
            rag_context = self.kb.format_context(user_input, self.rag_top_k)

        # 2. Inject context into message
        full_msg = f"{rag_context}\n\nUser request: {user_input}" if rag_context else user_input

        # 3. Run agentic loop
        final_text = self._run_agent_loop(full_msg)

        if self.on_response:
            self.on_response(final_text)

        return final_text

    def reset(self):
        """Clear conversation history by starting a fresh Gemini chat session."""
        self._init_chat()
        console.print("[dim]Conversation history cleared (Gemini session reset).[/dim]")

    # ─── Gemini agentic loop ──────────────────────────────────────────────────

    def _run_agent_loop(self, user_message: str) -> str:
        """
        Sends message to Gemini and handles multi-turn tool calls automatically.
        Gemini returns function_call parts → we execute tools → send results back.
        Loop repeats until Gemini returns a plain text response.
        """
        MAX_ITERATIONS = 8

        # First message to Gemini
        response = self.chat_session.send_message(user_message)

        for _iteration in range(MAX_ITERATIONS):
            candidate = response.candidates[0]
            parts = candidate.content.parts

            text_parts     = [p.text for p in parts if hasattr(p, "text") and p.text]
            function_calls = [p.function_call for p in parts
                              if hasattr(p, "function_call") and p.function_call.name]

            if function_calls:
                # ── Execute every tool Gemini requested ───────────────────────
                function_responses = []
                for fc in function_calls:
                    tool_name  = fc.name
                    tool_input = dict(fc.args)   # proto MapComposite → plain dict

                    console.print(Panel(
                        f"[bold]{tool_name}[/bold]\n{json.dumps(tool_input, indent=2)}",
                        title="🔧 Gemini Tool Call",
                        border_style="yellow",
                    ))

                    if self.on_tool_call:
                        self.on_tool_call(tool_name, tool_input)

                    fn = TOOL_FUNCTIONS.get(tool_name)
                    if fn:
                        try:
                            result = fn(**tool_input)
                        except Exception as e:
                            result = f"Tool error: {e}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    console.print(f"[dim]Result:[/dim] {str(result)[:200]}")

                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": str(result)},
                            )
                        )
                    )

                # Send all tool results back to Gemini in one turn
                response = self.chat_session.send_message(function_responses)

            else:
                # No tool calls — Gemini's final answer
                final_text = " ".join(text_parts).strip()
                return final_text or "Done."

        return "I have completed the task."
