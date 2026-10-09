"""BRAIN: turns spoken text into a Command."""

import re
from dataclasses import dataclass

import config


@dataclass
class Command:
    action: str
    target: str | None = None


OPEN_WORDS = (
    "open",
    "launch",
    "start",
    "run",
    "show",
    "bring up",
)

EXIT_PHRASES = (
    "exit",
    "quit",
    "goodbye",
    "good bye",
    "stop listening",
)

FILLER_WORDS = (
    "my",
    "the",
    "please",
    "for me",
)


def _normalize(text):
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def extract_command_text(heard):

    text = _normalize(heard)

    # Remove casual greetings before the wake word.
    text = re.sub(
        r"^(hey|hi|hello|ok|okay)\s+",
        "",
        text
    )

    # FRIDAY wake word.
    if re.match(
        rf"^{re.escape(config.NAME)}\b",
        text
    ):

        return text[
            len(config.NAME):
        ].strip()

    # If wake word is required,
    # ignore everything else.
    if config.REQUIRE_NAME:
        return None

    return text


def _clean_target(target):

    target = _normalize(target)

    words = target.split()

    words = [
        word
        for word in words
        if word not in FILLER_WORDS
    ]

    return " ".join(words).strip()


def _find_application(target):

    target = _clean_target(target)

    best_match = None

    for key, entry in config.OPENABLE.items():

        for alias in entry["aliases"]:

            alias = _normalize(alias)

            if target == alias:

                if (
                    best_match is None
                    or len(alias) > best_match[0]
                ):
                    best_match = (
                        len(alias),
                        key
                    )

            elif alias in target:

                if (
                    best_match is None
                    or len(alias) > best_match[0]
                ):
                    best_match = (
                        len(alias),
                        key
                    )

    if best_match:
        return best_match[1]

    return target


def parse(command_text):

    if not command_text:
        return None

    command_text = _normalize(
        command_text
    )

    # EXIT
    if any(
        command_text == phrase
        or command_text.endswith(
            " " + phrase
        )
        for phrase in EXIT_PHRASES
    ):

        return Command("exit")

    # OPEN / LAUNCH / START
    matched_word = None

    for word in OPEN_WORDS:

        if command_text == word:

            matched_word = word
            break

        if command_text.startswith(
            word + " "
        ):

            matched_word = word
            break

    if not matched_word:
        return None

    target = command_text[
        len(matched_word):
    ].strip()

    if not target:
        return None

    target = _find_application(
        target
    )

    return Command(
        "open",
        target
    )