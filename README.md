# 🧠 Whisper Transcriber GUI: A Sci-Fi Adventure

> 🚀 Welcome, **Cadet Coder**, to the **Whisper Transcriber Mission** — your mission is to set up a speech-to-text AI that can hear your voice and transcribe it in real time.  
> You’ll be using **OpenAI’s Whisper** — the same kind of tech used by interstellar linguists and rogue hacker-AIs.  
> Ready to hack the future with your voice? Let’s go. 🌌

---

## 🧰 What You’re Building

- 🎙️ Speak into your microphone
- 📋 Whisper transcribes what you say
- 🧠 It uses advanced AI (just like in sci-fi movies)
- 💾 It puts the result straight into your clipboard (you can paste it anywhere!)

---

## 🧑‍💻 Step 0: The Mission Terminal (aka Your Computer)

Make sure you're on **Windows 11** and you have:
- Internet access 🌐
- A working microphone 🎤
- Some curiosity 😎

Let’s install your tools!

---

## 🔧 Step 1: Install Python (aka Programming Power Core)

### 🟢 Option A (Easiest): Get Python from Microsoft Store

1. Open the **Microsoft Store**
2. Search for **“Python 3.11”**
3. Click **Install** on the official one from the Python Software Foundation
4. Open **Command Prompt** (Press `Win + R`, type `cmd`, hit Enter)
5. Type:

```bash
python --version
```

You should see something like:

```
Python 3.11.x
```

✅ If that shows up, congrats! Python is online.

---

## 🧬 Step 2: Install `uv` (Fast Package Installer)

Now we’ll install `uv` — think of it as a **cyber-injector** that zaps your system with all the tools Whisper needs.

In your **Command Prompt**, type:

```bash
pip install uv
```

Wait a moment... once complete, you now have a superfast installer 🚀

---

### 🧩 Step 3: Clone the Project from GitHub

In **Command Prompt** or **PowerShell**, run:

```bash
git clone https://github.com/zhangxingeng/whisper_voice_to_text_converter.git
cd whisper_voice_to_text_converter
```

✅ This will download the full project including `app.py` and `pyproject.toml`.

---

Let me know if you want a script to automatically install everything after the clone (like a one-liner setup script)!
---

## ⚙️ Step 4: Install All Dependencies

Now, let uv install everything:

```bash
cd C:\WhisperMission
uv pip install --system -r pyproject.toml
```

This installs:
- 🧠 Whisper (the AI brain)
- 🎤 Sound recording tools
- 🎹 Keyboard listener
- 📋 Clipboard support
- 🧪 Scientific math tools

---

## 🎞️ Step 5: Install FFmpeg (Audio Handler)

Whisper needs a tool to **cut, convert, and slice audio files**. That's where `ffmpeg` comes in — your **cyber audio ninja**.

### 🟢 How to Install FFmpeg on Windows

1. Go to: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. Under "**Release builds**", click the **first ZIP link** under `ffmpeg-release-essentials.zip`
3. Extract the zip somewhere (e.g., `C:\ffmpeg`)
4. Inside that folder, go into: `ffmpeg\bin\`
5. Copy the full path of that folder (e.g., `C:\ffmpeg\bin`)

### 🧪 Add FFmpeg to Your System Path

1. Press `Win + S`, search for “**Environment Variables**”
2. Click “**Edit the system environment variables**”
3. Click the “**Environment Variables**” button
4. In the bottom section ("System variables"), scroll and click `Path`, then click **Edit**
5. Click **New** and paste the path: `C:\ffmpeg\bin`
6. Click OK → OK → OK

Now test it! In Command Prompt:

```bash
ffmpeg -version
```

If you see a bunch of info — 🎉 FFmpeg is ready!

---

## 💻 Step 6: Launch the Transcriber

You’re now ready to launch the GUI! Run:

```bash
python app.py
```

🧠 You’ll see a small window:
- Choose a language (or keep **Autodetect**)
- Pick a model like `base`, `small`, or `tiny` (smaller = faster, bigger = more accurate)
- Press **Ctrl + Shift + Space** to start recording
- Press again to stop
- Text will be automatically copied to your clipboard!

---

## 📋 Step 7: Try It Out!

Open Notepad or Word.

Press `Ctrl + V`.

🔥 BAM! Whisper just turned your voice into text.

---

## ⚠️ Tips & Notes

- First time you use a model, it will **download** (this can take a minute)
- Whisper will use **GPU if available**, otherwise CPU is fine
- This app is **offline-friendly** after the first model download
- Speak clearly into your mic for best results!

---

## 🧠 You're Now a Whisper Hacker

You’ve just built a **voice AI system** on your own.  
You’re ready to join the ranks of cyberpunk engineers and audio wizards.

Stay curious. Keep hacking. Whisper your way into the future.

☁️✨👾
