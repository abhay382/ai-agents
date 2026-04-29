@echo off
echo ================================================
echo  JARVIS - One Click Clean Install
echo ================================================

echo.
echo [1/3] Removing conflicting packages (torch etc)...
pip uninstall torch torchvision torchaudio transformers faster-whisper ctranslate2 sentence-transformers openai-whisper numpy -y 2>nul
pip cache purge

echo.
echo [2/3] Installing all packages with exact versions...
pip install ^
  SpeechRecognition==3.16.1 ^
  pyttsx3==2.99 ^
  google-generativeai==0.8.6 ^
  chromadb==1.0.9 ^
  pyautogui==0.9.54 ^
  pyperclip==1.9.0 ^
  psutil==7.2.0 ^
  duckduckgo-search==7.5.5 ^
  Pillow==11.2.1 ^
  python-dotenv==1.2.2 ^
  rich==13.9.4 ^
  requests==2.32.3 ^
  numpy==1.26.4

echo.
echo [3/3] Installing pyaudio (microphone)...
pip install pyaudio==0.2.14
if errorlevel 1 (
    echo Direct install failed. Trying pipwin...
    pip install pipwin
    pipwin install pyaudio
)

echo.
echo ================================================
echo  Done! Run:  python main.py
echo ================================================
pause
