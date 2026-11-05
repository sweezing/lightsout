from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models

PROMPT_MAX = settings.LIGHTS_OUT["PROMPT_MAX_LENGTH"]

class Prompt(models.Model):
    """One question in the team-authored prompt bank (Table 4: 60 at launch).

    Prompts rotate in `position` order, one per night, so the bank lasts
    len(bank) nights without repeats before cycling.
    """

    text = models.CharField(max_length=PROMPT_MAX, validators=[MaxLengthValidator(PROMPT_MAX)])
    position = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=True, help_text="Inactive prompts are skipped in rotation.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"#{self.position}: {self.text}"
