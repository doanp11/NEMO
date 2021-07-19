from django.conf.urls import url
from NEMO.apps.NEMO_transaction_validation import views

urlpatterns = [
	# Add your urls here.
	url(r'^transaction_validation/$', views.transaction_validation, name='transaction_validation'),
	url(r'^contest/usage_event/(?P<transaction_id>\d+)/$', views.contest_transaction, {'transaction_type': 'usage_event'}, name='contest_usage_event'),
	url(r'^contest/staff_charge/(?P<transaction_id>\d+)/$', views.contest_transaction, {'transaction_type': 'staff_charge'}, name='contest_staff_charge'),
	url(r'^submit_contest/usage_event/(?P<transaction_id>\d+)/$', views.submit_contest, {'transaction_type': 'usage_event'}, name='submit_ue_contest'),
	url(r'^submit_contest/staff_charge/(?P<transaction_id>\d+)/$', views.submit_contest, {'transaction_type': 'staff_charge'}, name='submit_sc_contest'),
	url(r'^review_contests/$', views.review_contests, name='review_contests'),
	url(r'^approve_contest/(?P<contest_id>\d+)/$', views.approve_contest, name='approve_contest'),
	url(r'^$', views.landing, name='landing'),
]