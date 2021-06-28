from django.db import models
from NEMO.models import Tool, Project, User, UsageEvent

# Create your models here.
class Contest(models.Model):
    CONTEST_REASONS = [
        (0, 'Incorrect operator selection'),
        (1, 'Incorrect customer selection'),
        (2, 'Incorrect project selection'),
        (3, 'Incorrect date selection'),
        (4, 'Incorrect tool selection'),
    ]
    transaction = models.ForeignKey(UsageEvent, help_text="Usage Event to be contested", on_delete=models.CASCADE)
    operator = models.ForeignKey(User, help_text="Staff that performed the transaction on behalf of the customer", related_name="contest_operator", on_delete=models.CASCADE)
    customer = models.ForeignKey(User, help_text="Customer that the staff performed the task on behalf of", related_name="contest_customer", on_delete=models.CASCADE)
    project = models.ForeignKey(Project, help_text="Transaction will be billed to this project", on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    tool = models.ForeignKey(Tool, help_text="The tool used during this transaction", on_delete=models.CASCADE)
    reason = models.TextField(choices=CONTEST_REASONS, help_text="Provide the reason for submitting this transaction contest")
    description = models.TextField(blank=True, null=True, help_text="Provide a detailed reason for submitting this transaction contest")
    admin_approved = models.BooleanField(default=False, help_text="<b>Check this to approve the contest</b>")

    class Meta:
        ordering = ['operator']

    def __str__(self):
        return self.id
