from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Q
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from NEMO.models import UsageEvent, StaffCharge, User, Project, Tool
from NEMO.utilities import month_list, get_month_timeframe, parse_start_and_end_date
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
	dictionary = {
		"usage": usage_events,
		"staff_charges": staff_charges,
		"project_list": Project.objects.filter(active=True),
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
		"start_date": usage_event.start,
		"end_date": usage_event.end,
		"user_list": User.objects.all(),
		"project_list": Project.objects.filter(active=True)
	}
	return render(request, "transaction_validation/contest.html", dictionary)

@staff_member_required(login_url=None)
@require_POST
def submit_contest(request, usage_event_id):
	new_contest = Contest()
	new_contest.transaction = get_object_or_404(UsageEvent, id=usage_event_id)
	new_contest.tool = get_object_or_404(Tool, id=request.POST.get('tool_id'))
	new_contest.admin_approved = False

	try:
		new_contest.operator = request.POST.get('operator')
		new_contest.customer = request.POST.get('customer')
		new_contest.project = request.POST.get('project')
		new_contest.start = request.POST.get('start_date')
		new_contest.end = request.POST.get('end_date')
		new_contest.reason = request.POST.get('contest_reason')
		new_contest.description = request.POST.get('contest_description')
	except Exception as e:
		return HttpResponseBadRequest(str(e))

	new_contest.save()
	return HttpResponse()