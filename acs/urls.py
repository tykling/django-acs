from django.urls import path

import acs.views

urlpatterns = [
    path('', acs.views.AcsServerView.as_view(), name='acs_server'),
]

