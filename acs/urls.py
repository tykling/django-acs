from django.urls import path

import acs.views

app_name = 'acs'

urlpatterns = [
    path('', acs.views.AcsServerView.as_view(), name='acs_server'),
]

