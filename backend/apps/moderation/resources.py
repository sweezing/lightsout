"""Support resources shown when a card is withheld for a crisis indicator.

TODO(moderation): the team verifies every number and link here before each
public deployment; services change. Regional selection is by the reader's
browser language/region hint only. No location is requested or stored.
"""

RESOURCES = [
    {
        "region": "Worldwide",
        "name": "Find A Helpline",
        "detail": "Free, confidential helplines in your country",
        "url": "https://findahelpline.com",
    },
    {
        "region": "United States",
        "name": "988 Suicide & Crisis Lifeline",
        "detail": "Call or text 988",
        "url": "https://988lifeline.org",
    },
    {
        "region": "Kazakhstan",
        "name": "National helpline for children and young people",
        "detail": "Call 150, free and anonymous",
        "url": None,
    },
    {
        "region": "Emergency",
        "name": "If you are in immediate danger",
        "detail": "Call your local emergency number (112 in Kazakhstan, 911 in the US)",
        "url": None,
    },
]

def support_resources():
    return RESOURCES
