# Whisper Transcriber (GUI)

A minimal Python app for recording and transcribing speech using OpenAI's Whisper.

🎙️ **Hotkey:** `Ctrl+Shift+Space`  
📋 **Output:** Transcribed text is automatically copied to your clipboard  
🧠 **Model & Language:** Selectable via dropdown in the GUI  
💻 **Platform:** Windows

---

## Features

- One hotkey to start/stop recording
- Simple status display: Idle / Listening / Transcribing / Done
- Choose from all official Whisper models (`tiny`, `base`, `small`, etc.)
- Supports language selection or automatic detection

---

## Installation

1. **Install Python packages:**

```bash
pip install openai-whisper sounddevice keyboard pyperclip scipy numpy
```

2. **Install FFmpeg:**

Download from [ffmpeg.org](https://ffmpeg.org/download.html) and make sure it's in your system PATH.

---

## Usage

Run the script:

```bash
python whisper_gui.py
```

- Use the GUI to select language and model
- Press `Ctrl+Shift+Space` to start recording
- Press again to stop and transcribe
- Transcription will be copied to your clipboard automatically

---

## Notes

- Whisper models will be downloaded on first use
- GPU acceleration will be used if available (via PyTorch)
- Designed for minimal distraction and fast transcription