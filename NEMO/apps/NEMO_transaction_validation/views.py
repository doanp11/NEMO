from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from NEMO.models import UsageEvent, User, Project, Tool, LandingPageChoice, Reservation, Alert, Resource
from NEMO.apps.NEMO_transaction_validation.models import Contest
from NEMO.utilities import month_list, get_month_timeframe
from NEMO.views.alerts import delete_expired_alerts
from NEMO.views.area_access import able_to_self_log_in_to_area, able_to_self_log_out_of_area
from NEMO.views.landing import valid_url_for_landing
from NEMO.views.notifications import delete_expired_notifications

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
	if operator:
		usage_events = usage_events.exclude(~Q(operator_id=operator.id))
	if project:
		usage_events = usage_events.filter(project=project)

	contests = Contest.objects.filter(admin_approved=False)
	contest_list = set()
	for contest in contests:
		contest_list.add(contest.transaction.id)

	dictionary = {
		"usage": usage_events,
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

@login_required
@require_GET
def landing(request):
	user: User = request.user
	delete_expired_alerts()
	delete_expired_notifications()
	usage_events = UsageEvent.objects.filter(operator=user.id, end=None).prefetch_related("tool", "project")
	tools_in_use = [u.tool.tool_or_parent_id() for u in usage_events]
	fifteen_minutes_from_now = timezone.now() + timedelta(minutes=15)
	landing_page_choices = LandingPageChoice.objects.all()
	if request.device == "desktop":
		landing_page_choices = landing_page_choices.exclude(hide_from_desktop_computers=True)
	if request.device == "mobile":
		landing_page_choices = landing_page_choices.exclude(hide_from_mobile_devices=True)
	if not user.is_staff and not user.is_superuser and not user.is_technician:
		landing_page_choices = landing_page_choices.exclude(hide_from_users=True)

	if not settings.ALLOW_CONDITIONAL_URLS:
		# validate all urls
		landing_page_choices = [
			landing_page_choice
			for landing_page_choice in landing_page_choices
			if valid_url_for_landing(landing_page_choice.url)
		]

	upcoming_reservations = Reservation.objects.filter(
		user=user.id, end__gt=timezone.now(), cancelled=False, missed=False, shortened=False
	).exclude(tool_id__in=tools_in_use, start__lte=fifteen_minutes_from_now).exclude(ancestor__shortened=True)
	if user.in_area():
		upcoming_reservations = upcoming_reservations.exclude(
			area=user.area_access_record().area, start__lte=fifteen_minutes_from_now
		)
	upcoming_reservations = upcoming_reservations.order_by("start")[:3]
	dictionary = {
		"validation_required": UsageEvent.objects.filter(operator=user.id, validated=False).exclude(user=user.id).exists(),
		"now": timezone.now(),
		"alerts": Alert.objects.filter(
			Q(user=None) | Q(user=user), debut_time__lte=timezone.now(), expired=False, deleted=False
		),
		"usage_events": usage_events,
		"upcoming_reservations": upcoming_reservations,
		"disabled_resources": Resource.objects.filter(available=False),
		"landing_page_choices": landing_page_choices,
		"self_log_in": able_to_self_log_in_to_area(request.user),
		"self_log_out": able_to_self_log_out_of_area(request.user),
	}
	return render(request, "transaction_validation/landing_custom.html", dictionary)