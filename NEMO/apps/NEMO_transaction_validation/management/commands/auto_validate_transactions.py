from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from NEMO.apps.NEMO_transaction_validation.models import ContestUsageEvent, ContestStaffCharge
from NEMO.models import UsageEvent, StaffCharge

class Command(BaseCommand):
    help = 'Auto validates Usage Events with end dates that have finished 5 days from now'

    def handle(self, *args, **options):
        outdated_ue_transactions = UsageEvent.objects.filter(validated=False, end__lte=timezone.now() - timedelta(days=5))
        for ue in outdated_ue_transactions:
            if not ContestUsageEvent.objects.filter(admin_approved=False, transaction=ue.id).exists():
                ue.validated = True
                ue.save()

        outdated_sc_transactions = StaffCharge.objects.filter(validated=False, end__lte=timezone.now() - timedelta(days=5))
        for sc in outdated_sc_transactions:
            if not ContestStaffCharge.objects.filter(admin_approved=False, transaction=sc.id).exists():
                sc.validated = True
                sc.save()
