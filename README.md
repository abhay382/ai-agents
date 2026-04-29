

<img width="1321" height="960" alt="Screenshot 2026-04-29 131356" src="https://github.com/user-attachments/assets/01c4762c-eccc-4be8-bc7c-e4757865f2c1" />

<img width="863" height="444" alt="image" src="https://github.com/user-attachments/assets/ec168aa5-71f1-450b-907a-016700ee8a58" />


# 🤖 JARVIS — Voice RAG Agent
### Talk to your computer. It talks back. It takes action.

---

## ✅ Prerequisites
- Python **3.10.11** (already installed via PyCharm)
- PyCharm (any edition)
- Microphone + speakers
- Internet connection (for Claude API calls)

---

## 🚀 STEP-BY-STEP SETUP IN PYCHARM

### Step 1 — Open Project in PyCharm
```
File → Open → select the voice_rag_agent folder
```

### Step 2 — Set Python Interpreter
```
File → Settings → Project → Python Interpreter
→ Click gear icon → Add
→ Virtualenv Environment → New environment
→ Base interpreter: Python 3.10.11
→ OK
```

### Step 3 — Install dependencies
Open PyCharm **Terminal** (bottom panel) and run:
```bash
pip install -r requirements.txt
```

> ⏳ This takes 3–5 minutes first time (downloads Whisper model ~74MB)

### Step 4 — Add your API Key
```bash
# In PyCharm terminal:
copy .env.example .env        # Windows
# OR
cp .env.example .env          # Mac/Linux
```
Then open `.env` and replace:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```
→ Get your key free at: https://console.anthropic.com

### Step 5 — Run the app
```
Right-click main.py → Run 'main'
```
OR press the green ▶ Play button in PyCharm.

---

## 🎙 HOW TO USE

| Action | How |
|--------|-----|
| Talk to JARVIS | Click the big green **🎙 SPEAK** button, speak, wait |
| Type instead | Type in the bottom text box, press Enter |
| Add your documents | Click **+ Add Text File** or **+ Add PDF** |
| Auto-load docs | Drop files in `data/knowledge_base/` folder |
| Start fresh chat | Click **⟳ NEW CHAT** |

---

## 💬 EXAMPLE VOICE COMMANDS

```
"What time is it?"
"Open Chrome"
"Search the web for Python tutorials"
"What's in my Downloads folder?"
"Create a file called notes.txt with content Hello World"
"Read the file C:/Users/me/Desktop/report.txt"
"Take a screenshot"
"What is my CPU and RAM usage?"
"Run the command ipconfig"
"Open YouTube"
"Type hello world"
```

---

## ⚙️ CONFIGURATION (.env file)

| Key | Default | Description |
|-----|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Claude API key |
| `AGENT_NAME` | Jarvis | Agent's name |
| `CLAUDE_MODEL` | claude-3-5-haiku-20241022 | Fastest Claude model |
| `WHISPER_MODEL` | base | STT model: tiny/base/small/medium |
| `AGENT_VOICE_RATE` | 175 | TTS speed (words per minute) |
| `RAG_TOP_K` | 4 | Knowledge base chunks to retrieve |

### Making it Faster
Change in `.env`:
```
WHISPER_MODEL=tiny    # 2x faster STT, slightly less accurate
```

### Making it Smarter
Change in `.env`:
```
CLAUDE_MODEL=claude-3-5-sonnet-20241022   # more capable, slightly slower
```

---

## 📁 PROJECT STRUCTURE

```
voice_rag_agent/
├── main.py                    ← RUN THIS IN PYCHARM
├── requirements.txt
├── .env.example               ← copy to .env and add API key
│
├── core/
│   ├── agent.py              ←  agentic brain + tool loop
│   └── voice.py              ← Whisper STT + pyttsx3 TTS
│
├── rag/
│   └── knowledge_base.py     ← ChromaDB vector store + embeddings
│
├── tools/
│   └── computer_tools.py     ← All computer control tools
│
├── ui/
│   └── desktop_app.py        ← tkinter desktop GUI
│
└── data/
    ├── chroma_db/            ← auto-created: vector database
    └── knowledge_base/       ← drop your .txt/.md/.pdf files here
        └── sample_knowledge.md
```

---

## 🔧 TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| `No module named 'whisper'` | `pip install openai-whisper` |
| `No module named 'sounddevice'` | `pip install sounddevice` |
| Microphone not working | Check Windows Privacy → Microphone access |
| `ANTHROPIC_API_KEY not set` | Check your `.env` file exists with the key |
| App opens but no voice | Check speaker volume; pyttsx3 uses system TTS |
| Slow first response | Normal — Whisper loads model on first use |
| `chromadb` install error | `pip install chromadb --upgrade` |

---

## 🧠 ADDING YOUR OWN KNOWLEDGE

Drop any of these into `data/knowledge_base/` before running:
- `.txt` — plain text notes
- `.md` — markdown files
- `.pdf` — documents, manuals, reports

JARVIS will automatically read them and use them when answering!

---

## 💡 TIPS

- Speak clearly and wait 1 second after clicking SPEAK
- The agent remembers the full conversation until you click New Chat
- Tool activity (what JARVIS is doing on your PC) shows in the right panel
- You can use text input while voice is processing


















---
🎙 Voice Input (Whisper STT)
        ↓
  RAG lookup in ChromaDB
  (your personal documents)
        ↓
  Gemini 2.0 Flash API
  (system prompt + context + history)
        ↓
  Tool execution if needed
  (open Chrome, read file, run command…)
        ↓
🔊 Spoken Response (pyttsx3 TTS)









*Built with:  · OpenAI Whisper · ChromaDB · pyttsx3 · tkinter*
