from django.contrib import admin
from django.contrib.admin import register
from NEMO.models import AreaAccessRecord
from NEMO.apps.NEMO_transaction_validation.models import ContestUsageEvent, ContestStaffCharge, ContestAreaAccessRecord
from mptt.admin import TreeRelatedFieldListFilter

# Register your models here.
@register(ContestUsageEvent)
class ContestUsageEventAdmin(admin.ModelAdmin):
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
            orig_ue_created = ContestUsageEvent.objects.filter(transaction=usage_event.id, reason='original').exists()
            if not orig_ue_created:
                orig_usage_event = ContestUsageEvent()
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

@register(ContestStaffCharge)
class ContestStaffChargeAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "area_access_records",
    )
    list_display = (
        "id",
        "transaction",
        "reason",
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
    )
    date_hierarchy = "start"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        staff_charge = obj.transaction
        if obj.admin_approved:
            # Check and create a Contest model if original Usage Event has not been saved as a Contest model
            orig_sc_created = ContestStaffCharge.objects.filter(transaction=staff_charge.id, reason='original').exists()
            if not orig_sc_created:
                orig_staff_charge = ContestStaffCharge()
                orig_staff_charge.transaction = staff_charge
                orig_staff_charge.user = staff_charge.customer
                orig_staff_charge.operator = staff_charge.staff_member
                orig_staff_charge.project = staff_charge.project
                orig_staff_charge.start = staff_charge.start
                orig_staff_charge.end = staff_charge.end
                orig_staff_charge.reason = 'original'
                orig_staff_charge.description = 'Original Transaction'
                orig_staff_charge.admin_approved = True
                orig_staff_charge.save()

        # Update Staff Charge model
        contest_reason = obj.reason
        if contest_reason == "customer":
            staff_charge.user = obj.user
            staff_charge_aars = AreaAccessRecord.objects.filter(staff_charge=staff_charge)
            for aar in staff_charge_aars:
                aar.customer = obj.user
                aar.save()
        if contest_reason == "project":
            staff_charge.project = obj.project
            staff_charge_aars = AreaAccessRecord.objects.filter(staff_charge=staff_charge)
            for aar in staff_charge_aars:
                aar.project = obj.project
                aar.save()
        if contest_reason == "datetime":
            staff_charge.start = obj.start
            staff_charge.end = obj.end
        staff_charge.save()

    def delete_model(self, request, obj):
        for aar in obj.area_access_records.all():
            aar.delete()

        super().delete_model(request, obj)

@register(ContestAreaAccessRecord)
class ContestAreaAccessRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "transaction",
        "original",
        "area",
        "start",
        "end",
    )
    list_filter = (
        "admin_approved",
        ("area", TreeRelatedFieldListFilter),
    )
    date_hierarchy = "start"
    readonly_fields = ('original',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        aar = obj.transaction
        if obj.admin_approved:
            # Check and create a Contest model if original Area Access Record has not been saved as a Contest model
            orig_aar_created = ContestAreaAccessRecord.objects.filter(transaction=aar.id, original=True).exists()
            if not orig_aar_created:
                orig_aar_created = ContestAreaAccessRecord()
                orig_aar_created.transaction = aar
                orig_aar_created.area = aar.area
                orig_aar_created.start = aar.start
                orig_aar_created.end = aar.end
                orig_aar_created.admin_approved = True
                orig_aar_created.save()

        # Update Area Access Record model
        aar.area = obj.area
        aar.start = obj.start
        aar.end = obj.end
        aar.save()