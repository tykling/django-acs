from django.urls import path

import acs.views

urlpatterns = [
    path('', acs.views.AcsServerView.as_view(), name='acs_server'),
    path('http/requests/', acs.views.AcsHttpRequestList.as_view(), name='acs_http_request_list'),
    path('http/requests/<int:pk>/', acs.views.AcsHttpRequestDetail.as_view(), name='acs_http_request_detail'),
    path('http/responses/', acs.views.AcsHttpResponseList.as_view(), name='acs_http_response_list'),
    path('http/responses/<int:pk>/', acs.views.AcsHttpResponseDetail.as_view(), name='acs_http_response_detail'),
    path('sessions/', acs.views.AcsSessionList.as_view(), name='acs_session_list'),
    path('sessions/failed/', acs.views.AcsSessionList.as_view(), name='acs_session_list_failed', kwargs={'only_failed': True}),
    path('sessions/verifiedfailed/', acs.views.AcsSessionList.as_view(), name='acs_session_list_failed_verified', kwargs={'only_failed': True, 'only_verified': True}),
    path('sessions/<int:pk>/', acs.views.AcsSessionDetail.as_view(), name='acs_session_detail'),
    path('jobqueue/', acs.views.AcsQueueJobList.as_view(), name='acs_queue_job_list'),
    path('jobqueue/hideautomatic/', acs.views.AcsQueueJobList.as_view(), name='acs_queue_job_list_hideautomatic', kwargs={'hideautomatic': True}),
    path('jobqueue/<int:pk>/', acs.views.AcsQueueJobDetail.as_view(), name='acs_queue_job_detail'),
    path('devicemodels/', acs.views.AcsDeviceModelList.as_view(), name='acs_device_model_list'),
    path('devicemodels/<int:pk>/', acs.views.AcsDeviceModelDetail.as_view(), name='acs_device_model_detail'),
    path('devicecategories/', acs.views.AcsDeviceCategoryList.as_view(), name='acs_device_category_list'),
    path('devicecategories/<int:pk>/', acs.views.AcsDeviceCategoryDetail.as_view(), name='acs_device_category_detail'),
    path('devicevendors/', acs.views.AcsDeviceVendorList.as_view(), name='acs_device_vendor_list'),
    path('devicevendors/<int:pk>/', acs.views.AcsDeviceVendorDetail.as_view(), name='acs_device_vendor_detail'),
    path('devices/', acs.views.AcsDeviceList.as_view(), name='acs_device_list'),
    path('devices/<int:pk>/', acs.views.AcsDeviceDetail.as_view(), name='acs_device_detail'),
    path('devices/<int:pk>/create_job/', acs.views.AcsQueueJobCreate.as_view(), name='acs_queue_job_create'),
    path('devices/<int:pk>/allacssessions/', acs.views.AllAcsSessions.as_view(), name='acsdevice_all_acs_sessions'),
]

