"""Patterns for automatic screening.

Kept deliberately small and readable. The team maintains extra terms in
wordlists/blocked.txt and wordlists/crisis.txt (one phrase per line), which
are loaded on top of these defaults.

TODO(moderation): review both lists with the faculty advisor before launch.
"""
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent / "wordlists"

#personal information. anonymity is the product, so a card may not carry
#anyone's contact details or a link out (doxxing and spam in one rule).
PERSONAL_INFO_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+", re.I), #email
    re.compile(r"(?:\+?\d[\s\-()]*){9,}"), #phone number
    re.compile(r"\b(?:https?://|www\.)\S+", re.I), #link
    re.compile(r"(?:^|\s)@[a-z0-9_.]{3,}", re.I), #social handle
]

#threats and harassment directed at someone else.
DEFAULT_BLOCKED = [
    "kill yourself",
    "kys",
    "i will kill you",
    "i'm going to kill you",
    "you should die",
    "go die",
]

#crisis indicators about the writer themself. a match withholds the card and
#shows the poster support resources; it is never published.
DEFAULT_CRISIS = [
    "kill myself",
    "killing myself",
    "end my life",
    "ending my life",
    "take my own life",
    "want to die",
    "wanna die",
    "don't want to be alive",
    "dont want to be alive",
    "don't want to wake up",
    "dont want to wake up",
    "no reason to live",
    "better off dead",
    "better off without me",
    "suicide",
    "suicidal",
    "hurt myself",
    "self harm",
    "self-harm",
    "cut myself",
    "overdose",
]

def _load(name, defaults):
    extra = []
    f = HERE / name
    if f.exists():
        extra = [ln.strip().lower() for ln in f.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.startswith("#")]
    return tuple(dict.fromkeys([*defaults, *extra]))

@lru_cache
def blocked_phrases():
    return _load("blocked.txt", DEFAULT_BLOCKED)

@lru_cache
def crisis_phrases():
    return _load("crisis.txt", DEFAULT_CRISIS)

def normalize(text: str) -> str:
    t = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", t)

NON_WORD = re.compile(r"[^a-z0-9' -]")

def contains_phrase(text: str, phrases) -> str | None:
    cleaned = NON_WORD.sub(" ", normalize(text))
    t = " " + re.sub(r"\s+", " ", cleaned).strip() + " "
    for p in phrases:
        if f" {p} " in t:
            return p
    return None
