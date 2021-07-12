from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from NEMO.apps.NEMO_transaction_validation.models import Contest
from NEMO.models import UsageEvent

class Command(BaseCommand):
    help = 'Auto validates Usage Events with end dates that have finished 5 days from now'

    def handle(self, *args, **options):
        outdated_transactions = UsageEvent.objects.filter(validated=False, end__lte=timezone.now() - timedelta(days=5))
        for ot in outdated_transactions:
            if not Contest.objects.filter(admin_approved=False, transaction=ot.id).exists():
                ot.validated = True
                ot.save()
