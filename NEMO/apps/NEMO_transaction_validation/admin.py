from django.contrib import admin
from django.contrib.admin import register

from NEMO.apps.NEMO_transaction_validation.models import Contest

# Register your models here.
@register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction",
        "reason",
        "tool",
        "user",
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
