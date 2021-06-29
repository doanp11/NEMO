from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, reverse
from django.views.decorators.http import require_GET, require_POST

from NEMO.models import UsageEvent, StaffCharge, User, Project, Tool
from NEMO.utilities import month_list, get_month_timeframe
from NEMO.apps.NEMO_transaction_validation.models import Contest

# Create your views here.
@staff_member_required
@require_GET
def transaction_validation(request):
	if request.GET.get("start_date") and request.GET.get("end_date"):
		start_date, end_date = parse_start_and_end_date(request.GET.get("start_date"), request.GET.get("end_date"))
	else:
		start_date, end_date = get_month_timeframe()

	operator = request.GET.get("operator")
	if operator:
		if operator == "all staff":
			operator = None
		else:
			operator = get_object_or_404(User, id=operator)
	else:
		operator = request.user

	project = request.GET.get("project")
	if project and project != "all projects":
		project = get_object_or_404(Project, id=project)
	else:
		project = None
	usage_events = UsageEvent.objects.filter(
		operator__is_staff=True, start__gte=start_date, start__lte=end_date
	).exclude(operator=F("user"))
	staff_charges = StaffCharge.objects.filter(start__gte=start_date, start__lte=end_date)
	if operator:
		usage_events = usage_events.exclude(~Q(operator_id=operator.id))
		staff_charges = staff_charges.exclude(~Q(staff_member_id=operator.id))
	if project:
		usage_events = usage_events.filter(project=project)
		staff_charges = staff_charges.filter(project=project)

	contests = Contest.objects.filter(admin_approved=False)
	contest_list = set()
	for contest in contests:
		contest_list.add(contest.transaction.id)

	dictionary = {
		"usage": usage_events,
		"staff_charges": staff_charges,
		"project_list": Project.objects.filter(active=True),
		"contest_list": contest_list,
		"start_date": start_date,
		"end_date": end_date,
		"month_list": month_list(),
		"selected_staff": operator.id if operator else "all staff",
		"selected_project": project.id if project else "all projects",
	}
	return render(request, "transaction_validation/validation.html", dictionary)

@staff_member_required(login_url=None)
def contest_usage_event(request, usage_event_id):
	usage_event = get_object_or_404(UsageEvent, id=usage_event_id)

	dictionary = {
		"usage_event": usage_event,
		"tool_list": Tool.objects.filter(visible=True),
		"start": usage_event.start,
		"end": usage_event.end,
		"user_list": User.objects.all(),
		"project_list": Project.objects.filter(active=True)
	}
	return render(request, "transaction_validation/contest.html", dictionary)

@staff_member_required(login_url=None)
@require_POST
def submit_contest(request, usage_event_id):
	new_contest = Contest()
	new_contest.transaction = get_object_or_404(UsageEvent, id=usage_event_id)
	new_contest.tool = get_object_or_404(Tool, id=request.POST['tool_id'])
	new_contest.admin_approved = False

	try:
		new_contest.operator = get_object_or_404(User, id=request.POST['operator_id'])
		new_contest.customer = get_object_or_404(User, id=request.POST['customer_id'])
		new_contest.project = get_object_or_404(Project, id=request.POST['project_id'])

		start = datetime.strptime(request.POST['start'], "%A, %B %d, %Y @ %I:%M %p")
		end = datetime.strptime(request.POST['end'], "%A, %B %d, %Y @ %I:%M %p")
		new_contest.start = start
		new_contest.end = end

		new_contest.reason = request.POST['contest_reason']
		new_contest.description = request.POST['contest_description']
	except Exception as e:
		return HttpResponseBadRequest(str(e))

	new_contest.save()
	return HttpResponseRedirect(reverse('transaction_validation'))