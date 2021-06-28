from django.contrib import admin
from django.contrib.admin import register

from NEMO.apps.NEMO_transaction_validation.models import Contest

# Register your models here.
@register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = (
        "operator",
        "customer",
        "project",
        "start",
        "end",
        "tool",
        "reason",
    )
    list_filter = (
        "operator",
        "project",
        "tool",
        "reason",
    )
    date_hierarchy = "start"