from django.urls import path

import acs.views

urlpatterns = [
    path('http/requests/', acsadmin.views.AcsHttpRequestList.as_view(), name='acs_http_request_list'),
    path('http/requests/<int:pk>/', acsadmin.views.AcsHttpRequestDetail.as_view(), name='acs_http_request_detail'),

    path('http/responses/', acsadmin.views.AcsHttpResponseList.as_view(), name='acs_http_response_list'),
    path('http/responses/<int:pk>/', acsadmin.views.AcsHttpResponseDetail.as_view(), name='acs_http_response_detail'),

    path('sessions/', acsadmin.views.AcsSessionList.as_view(), name='acs_session_list'),
    path('sessions/failed/', acsadmin.views.AcsSessionList.as_view(), name='acs_session_list_failed', kwargs={'only_failed': True}),
    path('sessions/verifiedfailed/', acsadmin.views.AcsSessionList.as_view(), name='acs_session_list_failed_verified', kwargs={'only_failed': True, 'only_verified': True}),
    path('sessions/<int:pk>/', acsadmin.views.AcsSessionDetail.as_view(), name='acs_session_detail'),

    path('jobqueue/', acsadmin.views.AcsQueueJobList.as_view(), name='acs_queue_job_list'),
    path('jobqueue/hideautomatic/', acsadmin.views.AcsQueueJobList.as_view(), name='acs_queue_job_list_hideautomatic', kwargs={'hideautomatic': True}),
    path('jobqueue/<int:pk>/', acsadmin.views.AcsQueueJobDetail.as_view(), name='acs_queue_job_detail'),

    path('devicemodels/', acsadmin.views.AcsDeviceModelList.as_view(), name='acs_device_model_list'),
    path('devicemodels/<int:pk>/', acsadmin.views.AcsDeviceModelDetail.as_view(), name='acs_device_model_detail'),

    path('devicecategories/', acsadmin.views.AcsDeviceCategoryList.as_view(), name='acs_device_category_list'),
    path('devicecategories/<int:pk>/', acsadmin.views.AcsDeviceCategoryDetail.as_view(), name='acs_device_category_detail'),

    path('devicevendors/', acsadmin.views.AcsDeviceVendorList.as_view(), name='acs_device_vendor_list'),
    path('devicevendors/<int:pk>/', acsadmin.views.AcsDeviceVendorDetail.as_view(), name='acs_device_vendor_detail'),

    path('devices/', acsadmin.views.AcsDeviceList.as_view(), name='acs_device_list'),
    path('devices/<int:pk>/', acsadmin.views.AcsDeviceDetail.as_view(), name='acs_device_detail'),
    path('devices/<int:pk>/create_job/', acsadmin.views.AcsQueueJobCreate.as_view(), name='acs_queue_job_create'),
    path('devices/<int:pk>/allacssessions/', acsadmin.views.AllAcsSessions.as_view(), name='acsdevice_all_acs_sessions'),
]

