"""FRIDAY microphone listener."""

import time
import speech_recognition as sr
import config


class Listener:

    def __init__(self):

        self.recognizer = sr.Recognizer()

        # Better speech detection
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.5
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5

        self.microphone = sr.Microphone()

        print("Calibrating microphone...")

        with self.microphone as source:

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

        print("Microphone ready.")

    def listen(self):

        print("Listening...")

        try:

            with self.microphone as source:

                audio = self.recognizer.listen(
                    source,
                    timeout=config.LISTEN_TIMEOUT,
                    phrase_time_limit=config.PHRASE_TIME_LIMIT
                )

        except sr.WaitTimeoutError:

            print("No speech detected.")

            return None

        except Exception as error:

            print(
                f"Microphone error: {error}"
            )

            return None

        print("Processing speech...")

        try:

            text = self.recognizer.recognize_google(
                audio,
                language=config.LANGUAGE
            )

            text = text.strip()

            if not text:
                return None

            print(
                f"You said: {text}"
            )

            # Small protection against immediately
            # capturing FRIDAY's own voice.
            time.sleep(0.25)

            return text

        except sr.UnknownValueError:

            print(
                "Could not understand the speech."
            )

            return None

        except sr.RequestError as error:

            print(
                f"Google speech service error: {error}"
            )

            return None

        except Exception as error:

            print(
                f"Speech recognition error: {error}"
            )

            return None