"""
Modern Whisper Transcription App with Clean Architecture

A comprehensive audio transcription application using OpenAI Whisper,
built with proper state management and clean class-based design.
"""

import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Callable

import keyboard
import numpy as np
import pyperclip
import scipy.io.wavfile as wav
import sounddevice as sd
import whisper
from pydantic import BaseModel, Field, PrivateAttr
from whisper import _MODELS
from whisper.tokenizer import LANGUAGES as WHISPER_LANGS


class AudioDeviceInfo(BaseModel):
    """Audio device information with validation."""

    index: int = Field(..., description="Device index in sounddevice")
    name: str = Field(..., description="Human-readable device name")
    channels: int = Field(..., description="Number of input channels")
    default_samplerate: int = Field(..., description="Default sample rate in Hz")


class TranscriberConfig(BaseModel):
    """Configuration for the transcriber application."""

    hotkey: str = Field(default="ctrl+shift+space", description="Global hotkey for recording")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    window_size: str = Field(default="700x600", description="GUI window dimensions")
    max_parallel_audio: int = Field(default=1, description="Max concurrent audio operations")
    default_model: str = Field(default="base", description="Default Whisper model")
    default_language: str = Field(default="Autodetect", description="Default transcription language")
    test_duration: int = Field(default=5, description="Audio test duration in seconds")
    min_recording_duration: float = Field(default=0.5, description="Minimum recording length in seconds")
    silence_threshold: float = Field(default=0.001, description="Audio silence detection threshold")


class TranscriberState(BaseModel):
    """Current state of the transcriber application."""

    is_listening: bool = Field(default=False, description="Currently recording audio")
    is_testing_audio: bool = Field(default=False, description="Currently testing audio input")
    current_device_index: int | None = Field(default=None, description="Selected audio device index")
    selected_model: str = Field(default="base", description="Currently selected Whisper model")
    selected_language: str = Field(default="Autodetect", description="Currently selected language")

    # Runtime state (not serialized)
    _recording_data: list[np.ndarray] = PrivateAttr(default_factory=list)
    _audio_lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)
    _recording_stream: object | None = PrivateAttr(default=None)
    _test_stream: object | None = PrivateAttr(default=None)

    @property
    def is_audio_busy(self) -> bool:
        """Check if any audio operation is currently active."""
        return self.is_listening or self.is_testing_audio


class WhisperTranscriber:
    """Main transcriber application with clean state management."""

    def __init__(self, config: TranscriberConfig | None = None):
        self.config = config or TranscriberConfig()
        self.state = TranscriberState(selected_model=self.config.default_model, selected_language=self.config.default_language)

        # Language mappings
        self._languages = {"Autodetect": None, **{v.capitalize(): k for k, v in WHISPER_LANGS.items()}}
        self._models = list(_MODELS.keys())

        # GUI components (initialized in setup_gui)
        self.root: tk.Tk | None = None
        self._gui_components: dict[str, tk.Widget] = {}

        # Audio devices cache
        self._audio_devices: list[AudioDeviceInfo] = []

    def get_audio_devices(self) -> list[AudioDeviceInfo]:
        """Get list of available audio input devices."""
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:
                    input_devices.append(AudioDeviceInfo(index=i, name=device["name"], channels=device["max_input_channels"], default_samplerate=int(device["default_samplerate"])))
            return input_devices
        except Exception as e:
            self._log_error(f"Error getting audio devices: {e}")
            return []

    def get_default_input_device(self) -> AudioDeviceInfo | None:
        """Get the system default input device."""
        try:
            default_device = sd.query_devices(kind="input")
            return AudioDeviceInfo(
                index=sd.default.device[0] if sd.default.device[0] is not None else default_device["index"],
                name=default_device["name"],
                channels=default_device["max_input_channels"],
                default_samplerate=int(default_device["default_samplerate"]),
            )
        except Exception as e:
            self._log_error(f"Error getting default device: {e}")
            return None

    def setup_gui(self) -> None:
        """Initialize the GUI components."""
        self.root = tk.Tk()
        self.root.title("Whisper Transcriber")
        self.root.geometry(self.config.window_size)

        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(5, weight=1)  # Text area row
        main_frame.grid_columnconfigure(0, weight=1)

        self._create_status_section(main_frame)
        self._create_audio_device_section(main_frame)
        self._create_model_selection_section(main_frame)
        self._create_control_buttons_section(main_frame)
        self._create_text_display_section(main_frame)

        # Initialize state
        self._refresh_audio_devices()
        self._update_ui_state()

        # Show welcome message
        self._show_welcome_message()

    def _create_status_section(self, parent: ttk.Frame) -> None:
        """Create status display section."""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(0, weight=1)

        self._gui_components["status_label"] = ttk.Label(controls_frame, text="Idle", font=("Arial", 14), foreground="blue")
        self._gui_components["status_label"].grid(row=0, column=0, pady=5)

        self._gui_components["hotkey_label"] = ttk.Label(controls_frame, text=f"Hotkey: {self.config.hotkey}", font=("Arial", 10), foreground="gray")
        self._gui_components["hotkey_label"].grid(row=1, column=0, pady=2)

    def _create_audio_device_section(self, parent: ttk.Frame) -> None:
        """Create audio device selection and testing section."""
        audio_frame = ttk.LabelFrame(parent, text="Audio Device", padding="5")
        audio_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        audio_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(audio_frame, text="Input Device:").grid(row=0, column=0, padx=(0, 5), sticky="w")

        self._gui_components["device_var"] = tk.StringVar()
        self._gui_components["device_menu"] = ttk.Combobox(audio_frame, textvariable=self._gui_components["device_var"], state="readonly", width=40)
        self._gui_components["device_menu"].grid(row=0, column=1, padx=(0, 5), sticky="ew")
        self._gui_components["device_menu"].bind("<<ComboboxSelected>>", self._on_device_change)

        self._gui_components["test_audio_button"] = ttk.Button(audio_frame, text="Test Audio", command=self._toggle_audio_test)
        self._gui_components["test_audio_button"].grid(row=0, column=2, padx=(5, 0))

        self._gui_components["audio_level_label"] = ttk.Label(audio_frame, text="Audio Level: --", font=("Arial", 9))
        self._gui_components["audio_level_label"].grid(row=1, column=0, columnspan=3, pady=(5, 0), sticky="w")

        self._gui_components["device_info_label"] = ttk.Label(audio_frame, text="", font=("Arial", 8), foreground="gray")
        self._gui_components["device_info_label"].grid(row=2, column=0, columnspan=3, pady=(2, 0), sticky="w")

    def _create_model_selection_section(self, parent: ttk.Frame) -> None:
        """Create model and language selection section."""
        dropdowns_frame = ttk.Frame(parent)
        dropdowns_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # Language selection
        ttk.Label(dropdowns_frame, text="Language").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self._gui_components["lang_var"] = tk.StringVar(value=self.config.default_language)
        self._gui_components["lang_menu"] = ttk.Combobox(dropdowns_frame, textvariable=self._gui_components["lang_var"], values=list(self._languages.keys()), state="readonly", width=15)
        self._gui_components["lang_menu"].grid(row=0, column=1, padx=(0, 20), sticky="w")

        # Model selection
        ttk.Label(dropdowns_frame, text="Model").grid(row=0, column=2, padx=(0, 5), sticky="w")
        self._gui_components["model_var"] = tk.StringVar(value=self.config.default_model)
        self._gui_components["model_menu"] = ttk.Combobox(dropdowns_frame, textvariable=self._gui_components["model_var"], values=self._models, state="readonly", width=15)
        self._gui_components["model_menu"].grid(row=0, column=3, sticky="w")

    def _create_control_buttons_section(self, parent: ttk.Frame) -> None:
        """Create control buttons section."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        self._gui_components["record_button"] = ttk.Button(buttons_frame, text="Start Recording", command=self._toggle_recording)
        self._gui_components["record_button"].grid(row=0, column=0, padx=(0, 10))

        self._gui_components["clear_button"] = ttk.Button(buttons_frame, text="Clear Text", command=self._clear_text)
        self._gui_components["clear_button"].grid(row=0, column=1, padx=(0, 10))

        self._gui_components["copy_button"] = ttk.Button(buttons_frame, text="Copy to Clipboard", command=self._copy_current_text)
        self._gui_components["copy_button"].grid(row=0, column=2, padx=(0, 10))

        self._gui_components["refresh_button"] = ttk.Button(buttons_frame, text="Refresh Devices", command=self._refresh_audio_devices)
        self._gui_components["refresh_button"].grid(row=0, column=3)

    def _create_text_display_section(self, parent: ttk.Frame) -> None:
        """Create text display section."""
        ttk.Label(parent, text="Transcribed Text:").grid(row=4, column=0, sticky="w", pady=(0, 5))

        self._gui_components["text_display"] = scrolledtext.ScrolledText(parent, wrap=tk.WORD, width=80, height=18, font=("Arial", 11))
        self._gui_components["text_display"].grid(row=5, column=0, sticky="nsew")

        # Configure text tags
        text_widget = self._gui_components["text_display"]
        text_widget.tag_configure("timestamp", foreground="gray", font=("Arial", 9))
        text_widget.tag_configure("transcription", foreground="black", font=("Arial", 11))
        text_widget.tag_configure("device_info", foreground="blue", font=("Arial", 10))
        text_widget.tag_configure("error", foreground="red", font=("Arial", 10))

    def _update_status(self, text: str, color: str = "blue") -> None:
        """Update status label with text and color."""
        if "status_label" in self._gui_components:
            self._gui_components["status_label"].config(text=text, foreground=color)

    def _reset_status(self) -> None:
        """Reset status to idle if not busy."""
        if not self.state.is_audio_busy:
            self._update_status("Idle")

    def _update_ui_state(self) -> None:
        """Update UI elements based on current state."""
        busy = self.state.is_audio_busy

        # Update button states
        if "test_audio_button" in self._gui_components:
            if self.state.is_testing_audio:
                self._gui_components["test_audio_button"].config(text="Stop Test")
            else:
                self._gui_components["test_audio_button"].config(text="Test Audio")
            self._gui_components["test_audio_button"].config(state="normal" if not self.state.is_listening else "disabled")

        if "record_button" in self._gui_components:
            if self.state.is_listening:
                self._gui_components["record_button"].config(text="Stop Recording", style="Accent.TButton")
            else:
                self._gui_components["record_button"].config(text="Start Recording", style="TButton")
            self._gui_components["record_button"].config(state="normal" if not self.state.is_testing_audio else "disabled")

        # Update other controls
        for control_name in ["device_menu", "refresh_button"]:
            if control_name in self._gui_components:
                state = "disabled" if busy else ("readonly" if control_name == "device_menu" else "normal")
                self._gui_components[control_name].config(state=state)

    def _append_to_display(self, text: str, tag: str | None = None) -> None:
        """Append text to the display area with optional formatting."""
        if "text_display" not in self._gui_components:
            return

        text_widget = self._gui_components["text_display"]
        text_widget.config(state=tk.NORMAL)
        if tag:
            text_widget.insert(tk.END, text, tag)
        else:
            text_widget.insert(tk.END, text)
        text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)

    def _clear_text(self) -> None:
        """Clear the text display area."""
        if "text_display" in self._gui_components:
            text_widget = self._gui_components["text_display"]
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.config(state=tk.DISABLED)

    def _copy_current_text(self) -> None:
        """Copy all text from display to clipboard."""
        if "text_display" not in self._gui_components:
            return

        text_widget = self._gui_components["text_display"]
        current_text = text_widget.get(1.0, tk.END).strip()

        if current_text:
            pyperclip.copy(current_text)
            self._update_status("Text copied to clipboard!", "green")
            if self.root:
                self.root.after(3000, self._reset_status)
        else:
            self._update_status("No text to copy", "orange")
            if self.root:
                self.root.after(2000, self._reset_status)

    def _refresh_audio_devices(self) -> None:
        """Refresh the list of available audio devices."""
        if self.state.is_audio_busy:
            self._update_status("Cannot refresh while audio is active", "orange")
            return

        self._audio_devices = self.get_audio_devices()
        device_names = [f"{device.name} ({device.index})" for device in self._audio_devices]

        if "device_menu" in self._gui_components:
            self._gui_components["device_menu"]["values"] = device_names

        # Set default device
        default_device = self.get_default_input_device()
        if default_device and "device_var" in self._gui_components:
            default_name = f"{default_device.name} ({default_device.index})"
            if default_name in device_names:
                self._gui_components["device_var"].set(default_name)
                self._update_device_info(default_device)

        self._append_to_display(f"\nRefreshed audio devices. Found {len(self._audio_devices)} input devices.\n", "device_info")

    def _update_device_info(self, device: AudioDeviceInfo) -> None:
        """Update device information display."""
        if "device_info_label" in self._gui_components:
            info_text = f"Channels: {device.channels}, Sample Rate: {device.default_samplerate} Hz"
            self._gui_components["device_info_label"].config(text=info_text)

        self.state.current_device_index = device.index

    def _on_device_change(self, event=None) -> None:
        """Handle device selection change."""
        if self.state.is_audio_busy:
            self._update_status("Cannot change device while audio is active", "orange")
            return

        if "device_var" not in self._gui_components:
            return

        selected = self._gui_components["device_var"].get()
        if not selected:
            return

        try:
            device_index = int(selected.split("(")[-1].split(")")[0])
            for device in self._audio_devices:
                if device.index == device_index:
                    self._update_device_info(device)
                    self._append_to_display(f"\nSwitched to audio device: {device.name}\n", "device_info")
                    break
        except (ValueError, IndexError):
            self._log_error("Failed to parse device selection")

    def _cleanup_audio_streams(self) -> None:
        """Safely cleanup all audio streams."""
        try:
            if self.state._recording_stream and hasattr(self.state._recording_stream, "active"):
                if self.state._recording_stream.active:
                    self.state._recording_stream.stop()
                    self.state._recording_stream.close()
                self.state._recording_stream = None
        except Exception as e:
            self._log_error(f"Error closing recording stream: {e}")

        try:
            if self.state._test_stream and hasattr(self.state._test_stream, "active"):
                if self.state._test_stream.active:
                    self.state._test_stream.stop()
                    self.state._test_stream.close()
                self.state._test_stream = None
        except Exception as e:
            self._log_error(f"Error closing test stream: {e}")

    def _toggle_audio_test(self) -> None:
        """Toggle audio testing on/off."""
        with self.state._audio_lock:
            if self.state.is_testing_audio:
                # Stop current test
                self.state.is_testing_audio = False
                self._cleanup_audio_streams()
                self._update_status("Audio test stopped", "orange")
                if "audio_level_label" in self._gui_components:
                    self._gui_components["audio_level_label"].config(text="Audio Level: --")
                self._update_ui_state()
                if self.root:
                    self.root.after(1000, self._reset_status)
                return

            if self.state.is_audio_busy:
                self._update_status("Stop recording first", "orange")
                return

            self.state.is_testing_audio = True

        self._update_status("Testing audio input...", "orange")
        self._update_ui_state()
        threading.Thread(target=self._run_audio_test, daemon=True).start()

    def _run_audio_test(self) -> None:
        """Run audio level testing in background thread."""
        try:
            device_index = self.state.current_device_index

            def callback(indata, frames, time, status):
                if not self.state.is_testing_audio:
                    raise sd.CallbackAbort
                if status:
                    print(f"Test audio status: {status}")

                volume_norm = np.linalg.norm(indata) * 10
                level_text = f"Audio Level: {'█' * min(int(volume_norm), 20)} ({volume_norm:.1f})"

                if self.root and "audio_level_label" in self._gui_components:
                    self.root.after(0, lambda: self._gui_components["audio_level_label"].config(text=level_text))

            with self.state._audio_lock:
                if not self.state.is_testing_audio:
                    return

                self.state._test_stream = sd.InputStream(callback=callback, device=device_index, channels=1, samplerate=self.config.sample_rate)
                self.state._test_stream.start()

            # Wait for test duration or until cancelled
            for _ in range(self.config.test_duration * 10):
                if not self.state.is_testing_audio:
                    break
                time.sleep(0.1)

            # Cleanup
            with self.state._audio_lock:
                self.state.is_testing_audio = False
                self._cleanup_audio_streams()

            if self.root:
                self.root.after(0, self._audio_test_complete)

        except Exception as e:
            error_msg = f"Audio test failed: {str(e)}"
            with self.state._audio_lock:
                self.state.is_testing_audio = False
                self._cleanup_audio_streams()

            if self.root:
                self.root.after(0, lambda: self._audio_test_error(error_msg))

    def _audio_test_complete(self) -> None:
        """Handle successful audio test completion."""
        self._update_status("Audio test complete", "green")
        if "audio_level_label" in self._gui_components:
            self._gui_components["audio_level_label"].config(text="Audio Level: --")
        self._update_ui_state()
        if self.root:
            self.root.after(3000, self._reset_status)

    def _audio_test_error(self, error_msg: str) -> None:
        """Handle audio test error."""
        self._update_status(error_msg, "red")
        if "audio_level_label" in self._gui_components:
            self._gui_components["audio_level_label"].config(text="Audio Level: --")
        self._append_to_display(f"\n{error_msg}\n", "error")
        self._update_ui_state()
        if self.root:
            self.root.after(3000, self._reset_status)

    def _toggle_recording(self) -> None:
        """Toggle recording on/off."""
        if self.state.is_testing_audio:
            self._update_status("Stop audio test first", "orange")
            return

        if self.state.is_listening:
            self._stop_recording()
        else:
            self._start_recording()

    def _record_callback(self, indata, frames, time_, status):
        """Callback for audio recording."""
        if not self.state.is_listening:
            raise sd.CallbackAbort
        if status:
            print(f"Recording status: {status}")
        self.state._recording_data.append(indata.copy())

    def _start_recording(self) -> None:
        """Start audio recording."""
        with self.state._audio_lock:
            if self.state.is_audio_busy:
                self._update_status("Audio system busy", "orange")
                return
            self.state.is_listening = True

        self.state._recording_data.clear()
        self._update_status("Listening...", "red")
        self._update_ui_state()

        try:
            device_index = self.state.current_device_index

            with self.state._audio_lock:
                if not self.state.is_listening:
                    return

                self.state._recording_stream = sd.InputStream(samplerate=self.config.sample_rate, channels=1, callback=self._record_callback, device=device_index)
                self.state._recording_stream.start()

            # Show which device is being used
            device_name = "Default"
            if device_index is not None and "device_var" in self._gui_components:
                device_name = self._gui_components["device_var"].get().split(" (")[0]

            timestamp = time.strftime("%H:%M:%S")
            self._append_to_display(f"\n[{timestamp}] Recording started with: {device_name}\n", "device_info")

        except Exception as e:
            with self.state._audio_lock:
                self.state.is_listening = False
                self._cleanup_audio_streams()

            error_msg = f"Failed to start recording: {str(e)}"
            self._update_status(error_msg, "red")
            self._append_to_display(f"\n{error_msg}\n", "error")
            self._update_ui_state()
            if self.root:
                self.root.after(3000, self._reset_status)

    def _stop_recording(self) -> None:
        """Stop audio recording and start transcription."""
        with self.state._audio_lock:
            self.state.is_listening = False
            self._cleanup_audio_streams()

        self._update_ui_state()
        self._update_status("Transcribing...", "orange")
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    def _transcribe_audio(self) -> None:
        """Transcribe recorded audio using Whisper."""
        try:
            if not self.state._recording_data:
                self._update_status("No audio recorded", "red")
                if self.root:
                    self.root.after(2000, self._reset_status)
                return

            audio = np.concatenate(self.state._recording_data, axis=0)

            # Audio analysis
            audio_duration = len(audio) / self.config.sample_rate
            audio_max = np.max(np.abs(audio))
            audio_rms = np.sqrt(np.mean(audio**2))

            stats_text = f"Audio stats - Duration: {audio_duration:.1f}s, Max: {audio_max:.3f}, RMS: {audio_rms:.3f}\n"
            self._append_to_display(stats_text, "timestamp")

            # Validation checks
            if audio_duration < self.config.min_recording_duration:
                self._update_status("Recording too short", "red")
                if self.root:
                    self.root.after(2000, self._reset_status)
                return

            if audio_max < self.config.silence_threshold:
                self._update_status("No audio detected - check microphone", "red")
                self._append_to_display("Try the 'Test Audio' button to check your microphone levels.\n", "timestamp")
                if self.root:
                    self.root.after(3000, self._reset_status)
                return

            # Transcribe with Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav.write(f.name, self.config.sample_rate, audio)

                # Get current selections
                lang_code = None
                model_name = self.config.default_model

                if "lang_var" in self._gui_components:
                    selected_lang = self._gui_components["lang_var"].get()
                    lang_code = self._languages.get(selected_lang)

                if "model_var" in self._gui_components:
                    model_name = self._gui_components["model_var"].get()

                # Load and run model
                self._update_status("Loading model...", "orange")
                model = whisper.load_model(model_name)

                self._update_status("Transcribing...", "orange")
                result = model.transcribe(f.name, language=lang_code) if lang_code else model.transcribe(f.name)

                transcribed_text = str(result.get("text", "")).strip()

                if transcribed_text:
                    # Display and copy result
                    timestamp = time.strftime("%H:%M:%S")
                    self._append_to_display(f"\n[{timestamp}] ", "timestamp")
                    self._append_to_display(f"{transcribed_text}\n", "transcription")

                    pyperclip.copy(transcribed_text)
                    self._update_status("Transcribed & copied to clipboard!", "green")
                else:
                    self._update_status("No speech detected", "orange")
                    timestamp = time.strftime("%H:%M:%S")
                    self._append_to_display(f"\n[{timestamp}] No speech detected\n", "timestamp")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self._update_status(error_msg, "red")
            timestamp = time.strftime("%H:%M:%S")
            self._append_to_display(f"\n[{timestamp}] {error_msg}\n", "error")

        finally:
            # Reset status and UI
            if self.root:
                self.root.after(5000, lambda: [self._reset_status(), self._update_ui_state()])

    def _show_welcome_message(self) -> None:
        """Display welcome message in the text area."""
        welcome_text = f"""Welcome to Whisper Transcriber!

Instructions:
1. Select your microphone from the dropdown above
2. Use 'Test Audio' to check if your microphone is working
3. Press {self.config.hotkey} to start/stop recording or use the button
4. Select your preferred language and model
5. Transcribed text will appear here and be copied to clipboard

Ready to transcribe!
"""
        self._append_to_display(welcome_text, "timestamp")

    def _log_error(self, message: str) -> None:
        """Log error messages (could be extended to use proper logging)."""
        print(f"ERROR: {message}")

    def run(self) -> None:
        """Start the application."""
        self.setup_gui()

        # Set up global hotkey
        keyboard.add_hotkey(self.config.hotkey, self._toggle_recording)

        # Start GUI main loop
        if self.root:
            self.root.mainloop()


def main() -> None:
    """Application entry point."""
    config = TranscriberConfig()
    app = WhisperTranscriber(config)
    app.run()


if __name__ == "__main__":
    main()
