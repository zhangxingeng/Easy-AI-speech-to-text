import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk

import keyboard
import numpy as np
import pyperclip
import scipy.io.wavfile as wav
import sounddevice as sd
import whisper
from whisper import _MODELS
from whisper.tokenizer import LANGUAGES as WHISPER_LANGS

recording = []
is_listening = False
sample_rate = 16000
stream = None

LANGUAGES = {"Autodetect": None, **{v.capitalize(): k for k, v in WHISPER_LANGS.items()}}
MODELS = list(_MODELS.keys())

# Initial hotkey setup
HOTKEY = "ctrl+shift+space"

# GUI setup
root = tk.Tk()
root.title("Whisper Transcriber")
root.geometry("200x150")

status_label = ttk.Label(root, text="Idle", font=("Arial", 14))
status_label.pack(pady=5)

# Language dropdown
lang_var = tk.StringVar(value="Autodetect")
ttk.Label(root, text="Language").pack()
lang_menu = ttk.Combobox(root, textvariable=lang_var, values=list(LANGUAGES.keys()), state="readonly")
lang_menu.pack()

# Model dropdown
model_var = tk.StringVar(value="base")
ttk.Label(root, text="Model").pack()
model_menu = ttk.Combobox(root, textvariable=model_var, values=MODELS, state="readonly")
model_menu.pack()


def update_status(text):
    status_label.config(text=text)


def reset_status():
    update_status("Idle")


def record_callback(indata, frames, time_, status):
    recording.append(indata.copy())


def start_recording():
    global recording, stream, is_listening
    recording = []
    is_listening = True
    update_status("Listening")
    stream = sd.InputStream(samplerate=sample_rate, channels=1, callback=record_callback)
    stream.start()


def stop_recording():
    global is_listening
    is_listening = False
    if stream:
        stream.stop()
    update_status("Transcribing")
    threading.Thread(target=transcribe_audio).start()


def transcribe_audio():
    audio = np.concatenate(recording, axis=0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, sample_rate, audio)
        lang_code = LANGUAGES.get(lang_var.get())
        model_name = model_var.get()
        model = whisper.load_model(model_name)
        result = model.transcribe(f.name, language=lang_code) if lang_code else model.transcribe(f.name)
        pyperclip.copy(result["text"])
        update_status("Pasted to Clipboard")
        time.sleep(5)
        reset_status()


def toggle_recording():
    if not is_listening:
        start_recording()
    else:
        stop_recording()


# Hotkey binding
keyboard.add_hotkey(HOTKEY, toggle_recording)

root.mainloop()
