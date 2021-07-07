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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        usage_event = obj.transaction
        if obj.admin_approved:
            # Check and create a Contest model if original Usage Event has not been saved as a Contest model
            orig_ue_created = Contest.objects.filter(transaction=usage_event.id, reason='original').exists()
            if not orig_ue_created:
                orig_usage_event = Contest()
                orig_usage_event.transaction = usage_event
                orig_usage_event.user = usage_event.user
                orig_usage_event.operator = usage_event.operator
                orig_usage_event.project = usage_event.project
                orig_usage_event.tool = usage_event.tool
                orig_usage_event.start = usage_event.start
                orig_usage_event.end = usage_event.end
                orig_usage_event.reason = 'original'
                orig_usage_event.description = 'Original Transaction'
                orig_usage_event.admin_approved = True
                orig_usage_event.save()

        # Update Usage Event model
        contest_reason = obj.reason
        if contest_reason == "customer":
            usage_event.user = obj.user
        if contest_reason == "project":
            usage_event.project = obj.project
        if contest_reason == "datetime":
            usage_event.start = obj.start
            usage_event.end = obj.end
        if contest_reason == "tool":
            usage_event.tool = obj.tool
        usage_event.save()