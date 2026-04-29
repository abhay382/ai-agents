"""
main.py  ─  Run this file in PyCharm to launch JARVIS (Gemini edition)
────────────────────────────────────────────────────────────────────────
    1. pip install -r requirements.txt
    2. Copy .env.example → .env  and add your GEMINI_API_KEY
    3. Right-click main.py → Run 'main'
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel

console = Console()


def check_api_key():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or key.startswith("your_"):
        console.print(Panel(
            "[red]GEMINI_API_KEY is missing or not set![/red]\n\n"
            "1. Go to [link=https://aistudio.google.com/app/apikey]aistudio.google.com/app/apikey[/link]\n"
            "2. Click [bold]Create API key[/bold] (free, no credit card needed)\n"
            "3. Copy [bold].env.example[/bold] → [bold].env[/bold]\n"
            "4. Paste your key as GEMINI_API_KEY=your_key\n"
            "5. Re-run main.py",
            title="⚠  Setup Required",
            border_style="red",
        ))
        sys.exit(1)


def main():
    console.rule("[bold cyan]JARVIS  ·  Voice RAG Agent  (Gemini)[/bold cyan]")

    check_api_key()

    agent_name  = os.getenv("AGENT_NAME",    "Jarvis")
    model       = os.getenv("GEMINI_MODEL",  "gemini-2.0-flash-lite")
    voice_rate  = int(os.getenv("AGENT_VOICE_RATE", "175"))
    rag_top_k   = int(os.getenv("RAG_TOP_K", "4"))
    whisper_sz  = os.getenv("WHISPER_MODEL", "base")

    console.print("[dim]1/4  Starting knowledge base...[/dim]")
    from rag.knowledge_base import KnowledgeBase
    kb = KnowledgeBase(persist_dir="data/chroma_db")

    kb_folder = "data/knowledge_base"
    os.makedirs(kb_folder, exist_ok=True)
    files_in_kb = list(os.scandir(kb_folder))
    if files_in_kb:
        console.print(f"[dim]  Auto-ingesting {len(files_in_kb)} file(s) from data/knowledge_base/[/dim]")
        kb.add_folder(kb_folder)

    console.print("[dim]2/4  Loading Whisper speech-to-text...[/dim]")
    from core.voice import SpeechToText, TextToSpeech
    stt = SpeechToText(model_size=whisper_sz)

    console.print("[dim]3/4  Starting text-to-speech engine...[/dim]")
    tts = TextToSpeech(rate=voice_rate)

    console.print("[dim]4/4  Connecting to Gemini...[/dim]")
    from core.agent import VoiceAgent
    from ui.desktop_app import DesktopApp

    app = DesktopApp.__new__(DesktopApp)

    agent = VoiceAgent(
        name=agent_name,
        model=model,
        knowledge_base=kb,
        on_tool_call=lambda name, inp: app.on_tool_call(name, inp),
        on_response=lambda txt: app.on_response(txt),
        rag_top_k=rag_top_k,
    )

    app.__init__(agent, stt, tts)

    console.print(Panel(
        f"[green]✓ All systems online[/green]\n\n"
        f"  Agent  : [bold]{agent_name}[/bold]\n"
        f"  Model  : {model}\n"
        f"  STT    : Whisper ({whisper_sz})\n"
        f"  KB     : {kb.collection.count()} chunks\n\n"
        "[dim]The desktop window should now be visible.[/dim]",
        title="🚀  JARVIS Ready  (Gemini)",
        border_style="green",
    ))

    app.run()


if __name__ == "__main__":
    main()
