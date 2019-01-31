from django.urls import re_path as url
from django.urls import path

import acs.views

urlpatterns = [
    path('', acs.views.AcsServerView.as_view(), name='acs_server'),
    url(r'^http/requests/$', acs.views.AcsHttpRequestList.as_view(), name='acs_http_request_list'),
    url(r'^http/requests/(?P<pk>[0-9]+)/$', acs.views.AcsHttpRequestDetail.as_view(), name='acs_http_request_detail'),
    url(r'^http/responses/$', acs.views.AcsHttpResponseList.as_view(), name='acs_http_response_list'),
    url(r'^http/responses/(?P<pk>[0-9]+)/$', acs.views.AcsHttpResponseDetail.as_view(), name='acs_http_response_detail'),
    url(r'^sessions/$', acs.views.AcsSessionList.as_view(), name='acs_session_list'),
    url(r'^sessions/failed/$', acs.views.AcsSessionList.as_view(), name='acs_session_list_failed', kwargs={'only_failed': True}),
    url(r'^sessions/verifiedfailed/$', acs.views.AcsSessionList.as_view(), name='acs_session_list_failed_verified', kwargs={'only_failed': True, 'only_verified': True}),
    url(r'^sessions/(?P<pk>[0-9]+)/$', acs.views.AcsSessionDetail.as_view(), name='acs_session_detail'),
    url(r'^jobqueue/$', acs.views.AcsQueueJobList.as_view(), name='acs_queue_job_list'),
    url(r'^jobqueue/hideautomatic/$', acs.views.AcsQueueJobList.as_view(), name='acs_queue_job_list_hideautomatic', kwargs={'hideautomatic': True}),
    url(r'^jobqueue/(?P<pk>[0-9]+)/$', acs.views.AcsQueueJobDetail.as_view(), name='acs_queue_job_detail'),
    url(r'^devicemodels/$', acs.views.AcsDeviceModelList.as_view(), name='acs_device_model_list'),
    url(r'^devicemodels/(?P<pk>[0-9]+)/$', acs.views.AcsDeviceModelDetail.as_view(), name='acs_device_model_detail'),
    url(r'^devicecategories/$', acs.views.AcsDeviceCategoryList.as_view(), name='acs_device_category_list'),
    url(r'^devicecategories/(?P<pk>[0-9]+)/$', acs.views.AcsDeviceCategoryDetail.as_view(), name='acs_device_category_detail'),
    url(r'^devicevendors/$', acs.views.AcsDeviceVendorList.as_view(), name='acs_device_vendor_list'),
    url(r'^devicevendors/(?P<pk>[0-9]+)/$', acs.views.AcsDeviceVendorDetail.as_view(), name='acs_device_vendor_detail'),
    url(r'^devices/$', acs.views.AcsDeviceList.as_view(), name='acs_device_list'),
    url(r'^devices/(?P<pk>[0-9]+)/$', acs.views.AcsDeviceDetail.as_view(), name='acs_device_detail'),
    url(r'^devices/(?P<pk>[0-9]+)/create_job/$', acs.views.AcsQueueJobCreate.as_view(), name='acs_queue_job_create'),
    url(r'^devices/(?P<pk>[0-9]+)/allacssessions/$', acs.views.AllAcsSessions.as_view(), name='acsdevice_all_acs_sessions'),
]

