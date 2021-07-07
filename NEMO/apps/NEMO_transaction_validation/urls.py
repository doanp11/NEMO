from django.conf.urls import url
from NEMO.apps.NEMO_transaction_validation import views

urlpatterns = [
	# Add your urls here.
	url(r'^transaction_validation/$', views.transaction_validation, name='transaction_validation'),
	url(r'^contest_usage_event/(?P<usage_event_id>\d+)/$', views.contest_usage_event, name='contest_usage_event'),
	url(r'^submit_contest/(?P<usage_event_id>\d+)/$', views.submit_contest, name='submit_contest'),
	url(r'^review_contests/$', views.review_contests, name='review_contests'),
	url(r'^approve_contest/(?P<contest_id>\d+)/$', views.approve_contest, name='approve_contest'),
	url(r'^$', views.landing, name='landing'),
]