"""Classifier interface for automatic screening (Table 6: "keyword and
classifier check runs before publication").

The pipeline only depends on `Classifier.score()`. The built-in
KeywordClassifier is a transparent heuristic so the MVP works offline and its
decisions can be explained line by line in the moderation log.

TODO(moderation): add a trained text classifier (for example a small
toxicity model served locally) behind the same interface and select it with
MODERATION_CLASSIFIER. User card text must not be sent to a third-party API
(see proposal Appendix C, data and privacy).
"""
from dataclasses import dataclass, field

from django.conf import settings

from . import wordlists

@dataclass
class Scores:
    crisis: float = 0.0
    harmful: float = 0.0
    personal_info: float = 0.0
    matched: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "crisis": self.crisis,
            "harmful": self.harmful,
            "personal_info": self.personal_info,
            "matched": self.matched,
        }

class Classifier:
    name = "base"

    def score(self, text: str) -> Scores:  #pragma: no cover - interface
        raise NotImplementedError

class KeywordClassifier(Classifier):
    name = "keyword"

    def score(self, text: str) -> Scores:
        s = Scores()
        hit = wordlists.contains_phrase(text, wordlists.crisis_phrases())
        if hit:
            s.crisis = 1.0
            s.matched.append(f"crisis:{hit}")
        hit = wordlists.contains_phrase(text, wordlists.blocked_phrases())
        if hit:
            s.harmful = 1.0
            s.matched.append(f"blocked:{hit}")
        for pattern in wordlists.PERSONAL_INFO_PATTERNS:
            if pattern.search(text):
                s.personal_info = 1.0
                s.matched.append(f"personal_info:{pattern.pattern[:24]}")
                break
        return s

REGISTRY = {KeywordClassifier.name: KeywordClassifier}

def get_classifier() -> Classifier:
    name = settings.LIGHTS_OUT["CLASSIFIER"]
    return REGISTRY.get(name, KeywordClassifier)()
