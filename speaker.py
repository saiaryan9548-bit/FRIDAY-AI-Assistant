"""
FRIDAY SPEAKER

Reliable Windows text-to-speech using pyttsx3 + SAPI5.
Each response gets a fresh engine inside the same COM worker thread.
"""

import queue
import threading

import pyttsx3
import pythoncom

import config


class Speaker:

    def __init__(self):

        self.speaking = False
        self.stop_requested = False

        self.speech_queue = queue.Queue(
            maxsize=1
        )

        self.engine = None

        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )

        self.thread.start()

        print("Voice engine starting...")

    # =========================================================
    # SPEAK
    # =========================================================

    def speak(self, text):

        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        print(
            f"FRIDAY: {text}"
        )

        self.stop()

        self.stop_requested = False

        try:

            self.speech_queue.put_nowait(
                text
            )

        except queue.Full:

            pass

    # =========================================================
    # WORKER
    # =========================================================

    def _worker(self):

        pythoncom.CoInitialize()

        try:

            print(
                "Windows voice worker ready."
            )

            while True:

                text = self.speech_queue.get()

                if not text:
                    continue

                if self.stop_requested:
                    continue

                self.speaking = True

                engine = None

                try:

                    print(
                        "VOICE: Initializing speech..."
                    )

                    # Fresh engine for every response.
                    # This is slower to initialize, but much
                    # more reliable with Windows SAPI.
                    engine = pyttsx3.init(
                        "sapi5"
                    )

                    self.engine = engine

                    engine.setProperty(
                        "rate",
                        config.SPEECH_RATE
                    )

                    # -------------------------------------------------
                    # Select configured voice.
                    # -------------------------------------------------

                    voice_hint = (
                        config.VOICE_HINT
                        .lower()
                        .strip()
                    )

                    voices = engine.getProperty(
                        "voices"
                    )

                    selected_voice = None

                    for voice in voices:

                        voice_name = (
                            getattr(
                                voice,
                                "name",
                                ""
                            )
                            .lower()
                        )

                        if (
                            voice_hint
                            and voice_hint
                            in voice_name
                        ):

                            selected_voice = voice

                            break

                    if selected_voice:

                        engine.setProperty(
                            "voice",
                            selected_voice.id
                        )

                    elif voices:

                        engine.setProperty(
                            "voice",
                            voices[0].id
                        )

                    print(
                        "VOICE: Speaking..."
                    )

                    engine.say(
                        text
                    )

                    engine.runAndWait()

                    print(
                        "VOICE: Finished."
                    )

                except Exception as error:

                    print(
                        f"Speech error: {error}"
                    )

                finally:

                    try:

                        if engine:

                            engine.stop()

                    except Exception:
                        pass

                    self.engine = None
                    self.speaking = False

        except Exception as error:

            print(
                f"Voice worker error: {error}"
            )

        finally:

            self.speaking = False
            self.engine = None

            try:

                pythoncom.CoUninitialize()

            except Exception:
                pass

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        self.stop_requested = True

        # Clear waiting speech.
        try:

            while True:

                self.speech_queue.get_nowait()

        except queue.Empty:

            pass

        # Interrupt current engine.
        if self.engine:

            try:

                self.engine.stop()

            except Exception:
                pass

        self.speaking = False

    # =========================================================
    # STATUS
    # =========================================================

    def is_speaking(self):

        return self.speaking