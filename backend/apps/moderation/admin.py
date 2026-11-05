"""The manual review queue lives in the Django admin (Table 6: "manual review
queue handled by the team on a rota", target response 24 h).

/admin/cards/card/?status__exact=pending_review   is the queue.
"""
from datetime import timedelta

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.cards.models import Card

from . import pipeline
from .models import ModerationDecision, Report

class ReportInline(admin.TabularInline):
    model = Report
    extra = 0
    readonly_fields = ("reason", "created_at", "resolved")
    can_delete = False

class DecisionInline(admin.TabularInline):
    model = ModerationDecision
    extra = 0
    readonly_fields = ("source", "outcome", "reason", "scores", "moderator", "created_at")
    can_delete = False

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("short_text", "status", "open_reports", "waiting", "is_seed", "created_at")
    list_filter = ("status", "is_seed")
    search_fields = ("text",)
    readonly_fields = ("id", "x", "y", "created_at", "status_changed_at", "prompt", "preview")
    fields = ("id", "text", "preview", "status", "is_seed", "x", "y", "prompt", "created_at", "status_changed_at")
    inlines = [ReportInline, DecisionInline]
    actions = ["approve_cards", "remove_cards"]
    date_hierarchy = "created_at"

    @admin.display(description="Text")
    def short_text(self, obj):
        return obj.text[:80]

    @admin.display(description="Open reports")
    def open_reports(self, obj):
        return obj.reports.filter(resolved=False).count()

    @admin.display(description="Waiting")
    def waiting(self, obj):
        if obj.status != Card.Status.PENDING_REVIEW:
            return "-"
        age = timezone.now() - obj.status_changed_at
        hours = int(age.total_seconds() // 3600)
        late = age > timedelta(hours=24)
        return format_html('<b style="color:{}">{} h</b>', "#c0392b" if late else "inherit", hours)

    @admin.display(description="Image")
    def preview(self, obj):
        if not obj.image:
            return "-"
        return format_html('<img src="{}" style="max-width:240px;max-height:240px">', obj.image.url)

    @admin.action(description="Approve and publish selected cards")
    def approve_cards(self, request, queryset):
        for card in queryset:
            pipeline.approve(card, moderator=request.user)

    @admin.action(description="Remove selected cards")
    def remove_cards(self, request, queryset):
        for card in queryset:
            pipeline.remove(card, moderator=request.user)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("card", "reason", "resolved", "created_at")
    list_filter = ("reason", "resolved")

@admin.register(ModerationDecision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("card", "source", "outcome", "reason", "moderator", "created_at")
    list_filter = ("source", "outcome")
    readonly_fields = [f.name for f in ModerationDecision._meta.fields]

    def has_add_permission(self, request):
        return False
