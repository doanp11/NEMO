from datetime import datetime, timedelta
import pytz

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from NEMO.models import UsageEvent, StaffCharge, User, Project, Tool, LandingPageChoice, Reservation, Alert, Resource, Area, AreaAccessRecord
from NEMO.apps.NEMO_transaction_validation.models import ContestUsageEvent, ContestStaffCharge, ContestAreaAccessRecord
from NEMO.utilities import month_list, get_month_timeframe, parse_start_and_end_date, BasicDisplayTable
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
	staff_charges = StaffCharge.objects.filter(start__gte=start_date, start__lte=end_date)
	if operator:
		usage_events = usage_events.exclude(~Q(operator_id=operator.id))
		staff_charges = staff_charges.exclude(~Q(staff_member_id=operator.id))
	if project:
		usage_events = usage_events.filter(project=project)
		staff_charges = staff_charges.filter(project=project)

	csv_export = bool(request.GET.get("csv", False))
	if csv_export:
		table_result = BasicDisplayTable()
		TYPE, ID, ITEM, STAFF, CUSTOMER, PROJECT, START, END = (
			"item_type",
			"item_id",
			"item",
			"staff_member",
			"customer",
			"project",
			"start_date",
			"end_date",
		)
		table_result.headers = [
			(TYPE, "Item Type"),
			(ID, "Item Id"),
			(ITEM, "Item"),
			(STAFF, "Staff"),
			(CUSTOMER, "Customer"),
			(PROJECT, "Project"),
			(START, "Start"),
			(END, "End"),
		]
		for usage in usage_events:
			table_result.add_row(
				{
					ID: usage.tool.id,
					TYPE: "Tool Usage",
					ITEM: usage.tool,
					STAFF: usage.operator,
					CUSTOMER: usage.user,
					START: usage.start.astimezone(timezone.get_current_timezone()).strftime("%m/%d/%Y @ %I:%M %p"),
					END: usage.end.astimezone(timezone.get_current_timezone()).strftime("%m/%d/%Y @ %I:%M %p") if usage.end else "",
					PROJECT: usage.project,
				}
			)
		for staff_charge in staff_charges:
			for access in staff_charge.areaaccessrecord_set.all():
				table_result.add_row(
					{
						ID: access.area.id,
						TYPE: "Area Access",
						ITEM: access.area,
						STAFF: staff_charge.staff_member,
						CUSTOMER: access.customer,
						START: access.start.astimezone(timezone.get_current_timezone()).strftime("%m/%d/%Y @ %I:%M %p"),
						END: access.end.astimezone(timezone.get_current_timezone()).strftime("%m/%d/%Y @ %I:%M %p") if access.end else "",
						PROJECT: access.project,
					}
				)
			table_result.add_row(
				{
					ID: staff_charge.id,
					TYPE: "Staff Charge",
					ITEM: "Staff Charge",
					STAFF: staff_charge.staff_member,
					CUSTOMER: staff_charge.customer,
					START: staff_charge.start.astimezone(timezone.get_current_timezone()).strftime(
						"%m/%d/%Y @ %I:%M %p"
					),
					END: staff_charge.end.astimezone(timezone.get_current_timezone()).strftime("%m/%d/%Y @ %I:%M %p") if staff_charge.end else "",
					PROJECT: staff_charge.project,
				}
			)
		response = table_result.to_csv()
		filename = f"remote_work_{start_date.strftime('%m_%d_%Y')}_to_{end_date.strftime('%m_%d_%Y')}.csv"
		response["Content-Disposition"] = f'attachment; filename="{filename}"'
		return response

	# Determine Usage Events and Staff Charges with contest(s) submitted
	ue_contests = ContestUsageEvent.objects.filter(admin_approved=False)
	sc_contests = ContestStaffCharge.objects.filter(admin_approved=False)

	ue_contest_list = set()
	sc_contest_list = set()
	for contest in ue_contests:
		ue_contest_list.add(contest.transaction.id)
	for contest in sc_contests:
		sc_contest_list.add(contest.transaction.id)

	dictionary = {
		"usage": usage_events.order_by('validated', 'id'),
		"staff_charges": staff_charges.order_by('validated', 'id'),
		"project_list": Project.objects.filter(active=True),
		"ue_contest_list": ue_contest_list,
		"sc_contest_list": sc_contest_list,
		"start_date": start_date,
		"end_date": end_date,
		"month_list": month_list(),
		"selected_staff": operator.id if operator else "all staff",
		"selected_project": project.id if project else "all projects",
	}
	return render(request, "transaction_validation/validation.html", dictionary)

@staff_member_required(login_url=None)
def contest_transaction(request, transaction_id, transaction_type='usage_event'):
	if transaction_type is 'staff_charge':
		transaction = get_object_or_404(StaffCharge, id=transaction_id)
		template = "transaction_validation/contest_staff_charge.html"
	else:
		transaction = get_object_or_404(UsageEvent, id=transaction_id)
		template = "transaction_validation/contest_usage_event.html"

	dictionary = {
		"transaction": transaction,
		"start": transaction.start,
		"end": transaction.end,
		"user_list": User.objects.all(),
		"project_list": Project.objects.filter(active=True),
	}
	if transaction_type is 'staff_charge':
		dictionary['area_list'] = Area.objects.all()
	else:
		dictionary['tool_list'] = Tool.objects.filter(visible=True)
	return render(request, template, dictionary)

@staff_member_required(login_url=None)
@require_POST
def submit_contest(request, transaction_id, transaction_type='usage_event'):
	# Staff Charge contest submitted
	if transaction_type == 'staff_charge':
		try:
			new_contest = ContestStaffCharge()
			new_contest.transaction = get_object_or_404(StaffCharge, id=transaction_id)
		except Exception as e:
			return HttpResponseBadRequest(str(e))

	# Usage Event contest submitted
	else:
		new_contest = ContestUsageEvent()
		try:
			new_contest.transaction = get_object_or_404(UsageEvent, id=transaction_id)
			new_contest.tool = get_object_or_404(Tool, id=request.POST['tool_id'])
		except Exception as e:
			return HttpResponseBadRequest(str(e))
		if request.POST['contest_reason'] == 'area' and new_contest.transaction.tool.id == new_contest.tool.id:
			return HttpResponseBadRequest("No Usage Event Tool change submitted")

	new_contest.operator = request.user
	new_contest.admin_approved = False

	new_contest.reason = request.POST['contest_reason']
	new_contest.description = request.POST['contest_description']

	try:
		new_contest.user = get_object_or_404(User, id=request.POST['customer_id'])
		new_contest.project = get_object_or_404(Project, id=request.POST['project_id'])
	except Exception as e:
		return HttpResponseBadRequest(str(e))
	new_contest.start = datetime.strptime(request.POST['start'], "%A, %B %d, %Y @ %I:%M %p")
	new_contest.end = datetime.strptime(request.POST['end'], "%A, %B %d, %Y @ %I:%M %p")

	# Determine if submitted contest reason and change matches
	if transaction_type == 'staff_charge':
		if new_contest.reason == 'customer' and new_contest.transaction.customer.id == new_contest.user.id:
			return HttpResponseBadRequest("No Staff Charge Customer change submitted")
		if new_contest.reason == 'project' and new_contest.transaction.project.id == new_contest.project.id:
			return HttpResponseBadRequest("No Staff Charge Project change submitted")
		if new_contest.reason == 'datetime' \
				and new_contest.transaction.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_contest.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") \
				and new_contest.transaction.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_contest.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p"):
			return HttpResponseBadRequest("No Staff Charge Start or End change submitted")
	else:
		if new_contest.reason == 'customer' and new_contest.transaction.user.id == new_contest.user.id:
			return HttpResponseBadRequest("No Usage Event Customer change submitted")
		if new_contest.reason == 'project' and new_contest.transaction.project.id == new_contest.project.id:
			return HttpResponseBadRequest("No Usage Event Project change submitted")
		if new_contest.reason == 'datetime' \
				and new_contest.transaction.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_contest.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") \
				and new_contest.transaction.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_contest.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p"):
			return HttpResponseBadRequest("No Usage Event Start or End change submitted")

	# Save contest
	new_contest.save()

	# If submitting a Staff Charge contest, check to see if Area Access Record contests are being submitted
	if transaction_type == 'staff_charge' and new_contest.reason == 'area':
		for k in request.POST:
			if k.startswith('area_id_'):
				aar_id = k.split('area_id_')[1]
				new_aar_contest = ContestAreaAccessRecord()
				try:
					new_aar_contest.transaction = get_object_or_404(AreaAccessRecord, id=aar_id)
					new_aar_contest.area = get_object_or_404(Area, id=request.POST["area_id_" + aar_id])
				except Exception as e:
					new_contest.delete()
					return HttpResponseBadRequest(str(e))

				new_aar_contest.start = datetime.strptime(request.POST['start_' + aar_id], "%A, %B %d, %Y @ %I:%M %p")
				new_aar_contest.end = datetime.strptime(request.POST['end_' + aar_id], "%A, %B %d, %Y @ %I:%M %p")

				new_aar_contest.admin_approved = False

				# Filter out any unnecessary changes
				if new_aar_contest.transaction.area == new_aar_contest.area:
					new_aar_contest.area = None
				if new_aar_contest.transaction.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_aar_contest.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p"):
					new_aar_contest.start = None
				if new_aar_contest.transaction.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") == new_aar_contest.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p"):
					new_aar_contest.end = None

				if new_aar_contest.transaction.area != new_aar_contest.area \
						or new_aar_contest.transaction.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") != new_aar_contest.start.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") \
						or new_aar_contest.transaction.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p") != new_aar_contest.end.astimezone(pytz.UTC).strftime("%A, %B %d, %Y @ %I:%M %p"):
					new_aar_contest.save()
					new_contest.area_access_records.add(new_aar_contest)

		# In case Staff Charge contest is for contesting Area Access Records, determine if there are any changes submitted
		if not new_contest.area_access_records.exists():
			new_contest.delete()
			return HttpResponseBadRequest("No Area Access Record changes submitted.")

	# Contests created and saved with no errors
	return HttpResponse()

@staff_member_required(login_url=None)
@require_GET
def review_contests(request, transaction_id=0, transaction_type='usage_event'):
	if transaction_id == 0:
		# Determine Usage Events and Staff Charges with contest(s) submitted
		ue_contests = ContestUsageEvent.objects.filter(admin_approved=False)
		sc_contests = ContestStaffCharge.objects.filter(admin_approved=False)

		ue_contest_list = set()
		sc_contest_list = set()
		for contest in ue_contests:
			ue_contest_list.add(contest.transaction.id)
		for contest in sc_contests:
			sc_contest_list.add(contest.transaction.id)

		dictionary = {
			"ue_contest_list": ue_contest_list,
			"sc_contest_list": sc_contest_list,
			"ue_contests": ContestUsageEvent.objects.exclude(transaction__validated=True).order_by('transaction__id'),
			"sc_contests": ContestStaffCharge.objects.exclude(transaction__validated=True).order_by('transaction__id')
		}
		return render(request, "transaction_validation/review_contests.html", dictionary)
	elif transaction_type == 'area_access_record':
		sc_contest = get_object_or_404(ContestStaffCharge, id=transaction_id)
		dictionary = {
			"contest_reason": sc_contest.description,
			"aar_contests": sc_contest.area_access_records.order_by('transaction__id')
		}
		return render(request, "transaction_validation/review_aar_contests.html", dictionary)
	elif transaction_type == 'staff_charge':
		dictionary = {
			"staff_charge": get_object_or_404(StaffCharge, id=transaction_id),
			"contests": ContestStaffCharge.objects.filter(transaction=transaction_id)
		}
		return render(request, "transaction_validation/review_sc_contests.html", dictionary)
	else:
		dictionary = {
			"usage_event": get_object_or_404(UsageEvent, id=transaction_id),
			"contests": ContestUsageEvent.objects.filter(transaction=transaction_id)
		}
		return render(request, "transaction_validation/review_ue_contests.html", dictionary)

@staff_member_required(login_url=None)
@require_POST
def approve_ue_contest(request, contest_id):
	user: User = request.user

	# Check if user has admin authorizations
	if not user.is_superuser:
		return HttpResponseBadRequest("You are not authorized to approve contests.")

	# Get models
	contest = get_object_or_404(ContestUsageEvent, id=contest_id)
	usage_event = get_object_or_404(UsageEvent, id=contest.transaction.id)

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

	# Update Contest model
	contest.admin_approved = True
	contest.save()

	# Update Usage Event model
	contest_reason = contest.reason
	if contest_reason == "customer":
		usage_event.user = contest.user
	if contest_reason == "project":
		usage_event.project = contest.project
	if contest_reason == "datetime":
		usage_event.start = contest.start
		usage_event.end = contest.end
	if contest_reason == "tool":
		usage_event.tool = contest.tool
	usage_event.save()

	return HttpResponse()

def approve_aar_contest(request, sc_contest, contest_id):
	# Get models
	contest = get_object_or_404(ContestAreaAccessRecord, id=contest_id)
	area_access_record = get_object_or_404(AreaAccessRecord, id=contest.transaction.id)

	# Check and create a Contest model if original Area Access Record has not been saved as a Contest model
	orig_aar_created = ContestAreaAccessRecord.objects.filter(transaction=area_access_record.id, original=True).exists()
	if not orig_aar_created:
		orig_aar_created = ContestAreaAccessRecord()
		orig_aar_created.transaction = area_access_record
		orig_aar_created.area = area_access_record.area
		orig_aar_created.start = area_access_record.start
		orig_aar_created.end = area_access_record.end
		orig_aar_created.original = True
		orig_aar_created.admin_approved = True
		orig_aar_created.save()
		sc_contest.area_access_records.add(orig_aar_created)

	# Update Contest model
	contest.admin_approved = True
	contest.save()

	# Update Area Access Record model
	if contest.area is not None:
		area_access_record.area = contest.area
	if contest.start is not None:
		area_access_record.start = contest.start
	if contest.end is not None:
		area_access_record.end = contest.end
	area_access_record.save()

def approve_sc_aar_contests(request, sc_contest):
	# Get models
	area_access_records = sc_contest.area_access_records.all()

	for aar_contest in area_access_records:
		approve_aar_contest(request, sc_contest, aar_contest.id)

@staff_member_required(login_url=None)
@require_POST
def approve_sc_contest(request, contest_id):
	user: User = request.user

	# Check if user has admin authorizations
	if not user.is_superuser:
		return HttpResponseBadRequest("You are not authorized to approve contests.")

	# Get models
	contest = get_object_or_404(ContestStaffCharge, id=contest_id)
	staff_charge = get_object_or_404(StaffCharge, id=contest.transaction.id)

	# Check and create a Contest model if original Staff Charge has not been saved as a Contest model
	orig_sc_created = ContestStaffCharge.objects.filter(transaction=staff_charge.id, reason='original').exists()
	if not orig_sc_created:
		orig_sc_created = ContestStaffCharge()
		orig_sc_created.transaction = staff_charge
		orig_sc_created.user = staff_charge.customer
		orig_sc_created.operator = staff_charge.staff_member
		orig_sc_created.project = staff_charge.project
		orig_sc_created.start = staff_charge.start
		orig_sc_created.end = staff_charge.end
		orig_sc_created.reason = 'original'
		orig_sc_created.description = 'Original Transaction'
		orig_sc_created.admin_approved = True
		orig_sc_created.save()

	# Update Contest model
	contest.admin_approved = True
	contest.save()

	# Update Staff Charge model
	contest_reason = contest.reason
	if contest_reason == "customer":
		staff_charge.customer = contest.user
		staff_charge_aars = AreaAccessRecord.objects.filter(staff_charge=staff_charge)
		for aar in staff_charge_aars:
			aar.customer = contest.user
			aar.save()
	if contest_reason == "project":
		staff_charge.project = contest.project
		staff_charge_aars = AreaAccessRecord.objects.filter(staff_charge=staff_charge)
		for aar in staff_charge_aars:
			aar.project = contest.project
			aar.save()
	if contest_reason == "datetime":
		staff_charge.start = contest.start
		staff_charge.end = contest.end
	if contest_reason == "area":
		approve_sc_aar_contests(request, contest)
	staff_charge.save()

	return HttpResponse()

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
		"validation_required": UsageEvent.objects.filter(operator=user.id, validated=False).exclude(user=user.id).exists() or StaffCharge.objects.filter(staff_member=user.id, validated=False).exclude(customer=user.id).exists(),
		"approval_required": ContestUsageEvent.objects.filter(admin_approved=False).exists() or ContestStaffCharge.objects.filter(admin_approved=False).exists(),
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