"""
core/voice.py
STT: SpeechRecognition library with Google Web Speech API (free, no key needed)
TTS: pyttsx3 (fully offline)
Zero torch, zero transformers, zero build errors.
"""
from __future__ import annotations
import threading
from typing import Optional, Callable
from rich.console import Console

console = Console()


# ─── Speech-to-Text ───────────────────────────────────────────────────────────

class SpeechToText:
    """Microphone → Google Web Speech API → text. No local model, no torch."""

    def __init__(self, model_size: str = "base"):
        # model_size param kept for API compatibility but not used here
        try:
            import speech_recognition as sr
            self.sr = sr
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.pause_threshold  = 1.0   # seconds of silence to stop
            self.recognizer.dynamic_energy_threshold = True
            console.print("[green]✓ SpeechRecognition ready (Google Web Speech)[/green]")
        except ImportError:
            raise ImportError(
                "SpeechRecognition not installed.\n"
                "Run: pip install SpeechRecognition pyaudio"
            )

    def record_and_transcribe(
        self,
        max_seconds: int = 15,
        silence_timeout: float = 2.0,
        on_recording_start: Optional[Callable] = None,
    ) -> str:
        """Record from microphone and transcribe via Google Web Speech (free)."""
        sr = self.sr

        if on_recording_start:
            on_recording_start()

        console.print("[yellow]🎙 Listening...[/yellow]")

        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=5,                    # wait max 5s for speech to start
                        phrase_time_limit=max_seconds,
                    )
                except sr.WaitTimeoutError:
                    console.print("[dim]No speech detected.[/dim]")
                    return ""

            # Transcribe using Google Web Speech (free, no API key)
            text = self.recognizer.recognize_google(audio)
            console.print(f"[cyan]You:[/cyan] {text}")
            return text

        except sr.UnknownValueError:
            console.print("[dim]Could not understand audio.[/dim]")
            return ""
        except sr.RequestError as e:
            console.print(f"[red]Google Speech API error:[/red] {e}")
            console.print("[yellow]Check your internet connection.[/yellow]")
            return ""
        except Exception as e:
            console.print(f"[red]Microphone error:[/red] {e}")
            return ""


# ─── Text-to-Speech ───────────────────────────────────────────────────────────

class TextToSpeech:
    """Offline TTS using pyttsx3 — no internet, no API key."""

    def __init__(self, rate: int = 175, volume: float = 0.9):
        self.rate    = rate
        self.volume  = volume
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   self.rate)
            engine.setProperty("volume", self.volume)
            # Pick cleaner Windows voice if available
            for v in engine.getProperty("voices"):
                if "zira" in v.name.lower() or "david" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            self._engine = engine
            console.print("[green]✓ TTS engine ready (pyttsx3)[/green]")
        except Exception as e:
            console.print(f"[yellow]TTS unavailable ({e}) — text only mode[/yellow]")

    def speak(self, text: str, blocking: bool = True) -> None:
        console.print(f"[green]Jarvis:[/green] {text}")
        if not self._engine or not text.strip():
            return
        try:
            if blocking:
                self._engine.say(text)
                self._engine.runAndWait()
            else:
                threading.Thread(target=self._bg, args=(text,), daemon=True).start()
        except Exception as e:
            console.print(f"[yellow]TTS error:[/yellow] {e}")

    def _bg(self, text: str):
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass

    def stop(self):
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
