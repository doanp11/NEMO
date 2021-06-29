from django.contrib import admin
from django.contrib.admin import register

from NEMO.apps.NEMO_transaction_validation.models import Contest

# Register your models here.
def approve_contest(modeladmin, request, queryset):
    queryset.update(admin_approved=True)
approve_contest.short_description = "Approve selected contests"

@register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction",
        "reason",
        "tool",
        "customer",
        "operator",
        "project",
        "start",
        "end",
    )
    list_filter = (
        "admin_approved",
        "reason",
        "operator",
        "project",
        "tool",
    )
    date_hierarchy = "start"
    actions = [approve_contest]