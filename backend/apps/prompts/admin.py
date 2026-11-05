from django.contrib import admin

from .models import Prompt

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("position", "text", "is_active")
    list_editable = ("is_active",)
    search_fields = ("text",)
