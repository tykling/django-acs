from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View, ListView, DetailView
from django.views.generic.edit import FormView, CreateView
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.conf import settings
from django.utils import timezone
from ipware.ip import get_ip
from lxml import etree
from mrxcore.views import MrxGroupRequiredMixin
from django.utils.dateparse import parse_datetime
from defusedxml.lxml import fromstring
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views.generic.detail import SingleObjectMixin
from datetime import timedelta
import json, uuid
from xmlarchive.utils import create_xml_document
from .models import *
from .utils import get_value_from_parameterlist
from .response import nse, get_soap_envelope
from .forms import AcsDeviceActionForm


class AcsQueueJobList(MrxGroupRequiredMixin, ListView):
    model = AcsQueueJob
    template_name = 'acs_queue_job_list.html'
    paginate_by = 25

    def get_queryset(self):
        queryset = super(AcsQueueJobList, self).get_queryset()
        if 'hideautomatic' in self.kwargs and self.kwargs['hideautomatic']:
            queryset = queryset.exclude(automatic=True)
        return queryset


class AcsQueueJobDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsQueueJob
    template_name = 'acs_queue_job_detail.html'


class AcsQueueJobCreate(MrxGroupRequiredMixin, CreateView):
    model = AcsQueueJob
    template_name = 'acs_queue_job_create.html'
    fields = ['cwmp_rpc_object_xml', 'reason', 'urgent']

    def setup(self, *args, **kwargs):
        self.acs_device = get_object_or_404(
            AcsDevice,
            pk=self.kwargs['pk'],
        )

    def form_valid(self, form):
        job = form.save(commit=False)
        job.acs_device = self.acs_device
        job.save()
        return(super().form_valid(form))


class AcsSessionList(MrxGroupRequiredMixin, ListView):
    model = AcsSession
    template_name = 'acs_session_list.html'
    paginate_by = 25

    def get_queryset(self):
        queryset = super(AcsSessionList, self).get_queryset()
        #queryset = queryset.get_related()
        if 'only_failed' in self.kwargs and self.kwargs['only_failed']:
            queryset = queryset.filter(session_result=False)
        if 'only_verified' in self.kwargs and self.kwargs['only_verified']:
            queryset = queryset.filter(client_ip_verified=True)
        return queryset


class AcsSessionDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsSession
    template_name = 'acs_session_detail.html'


class AcsHttpRequestList(MrxGroupRequiredMixin, ListView):
    model = AcsHttpRequest
    template_name = 'acs_http_request_list.html'
    paginate_by = 25


class AcsHttpRequestDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsHttpRequest
    template_name = 'acs_http_request_detail.html'


class AcsHttpResponseList(MrxGroupRequiredMixin, ListView):
    model = AcsHttpResponse
    template_name = 'acs_http_response_list.html'
    paginate_by = 25


class AcsHttpResponseDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsHttpResponse
    template_name = 'acs_http_response_detail.html'


class AcsDeviceModelList(MrxGroupRequiredMixin, ListView):
    model = AcsDeviceModel
    template_name = 'acs_device_model_list.html'
    paginate_by = 25


class AcsDeviceModelDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsDeviceModel
    template_name = 'acs_device_model_detail.html'


class AcsDeviceCategoryList(MrxGroupRequiredMixin, ListView):
    model = AcsDeviceCategory
    template_name = 'acs_device_category_list.html'
    paginate_by = 25


class AcsDeviceCategoryDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsDeviceCategory
    template_name = 'acs_device_category_detail.html'


class AcsDeviceVendorList(MrxGroupRequiredMixin, ListView):
    model = AcsDeviceVendor
    template_name = 'acs_device_vendor_list.html'
    paginate_by = 25


class AcsDeviceVendorDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsDeviceVendor
    template_name = 'acs_device_vendor_detail.html'


class AcsDeviceList(MrxGroupRequiredMixin, ListView):
    model = AcsDevice
    template_name = 'acs_device_list.html'
    paginate_by = 25


class AcsDeviceDetail(MrxGroupRequiredMixin, DetailView):
    model = AcsDevice
    template_name = 'acs_device_detail.html'


class AllAcsSessions(MrxGroupRequiredMixin, ListView):
    model = AcsSession
    template_name = 'acs_session_list.html'
    paginate_by = 100

    def get_queryset(self):
        return AcsSession.objects.filter(acs_device_id=self.kwargs['pk'])

