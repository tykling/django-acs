from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView, CreateView
from django.shortcuts import get_object_or_404

from xmlarchive.utils import create_xml_document
from acs.models import *
from .forms import AcsDeviceActionForm


class AcsQueueJobList(ListView):
    model = AcsQueueJob
    template_name = 'acs_queue_job_list.html'
    paginate_by = 25

    def get_queryset(self):
        queryset = super(AcsQueueJobList, self).get_queryset()
        if 'hideautomatic' in self.kwargs and self.kwargs['hideautomatic']:
            queryset = queryset.exclude(automatic=True)
        return queryset


class AcsQueueJobDetail(DetailView):
    model = AcsQueueJob
    template_name = 'acs_queue_job_detail.html'


class AcsQueueJobCreate(CreateView):
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


class AcsSessionList(ListView):
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


class AcsSessionDetail(DetailView):
    model = AcsSession
    template_name = 'acs_session_detail.html'


class AcsHttpRequestList(ListView):
    model = AcsHttpRequest
    template_name = 'acs_http_request_list.html'
    paginate_by = 25


class AcsHttpRequestDetail(DetailView):
    model = AcsHttpRequest
    template_name = 'acs_http_request_detail.html'


class AcsHttpResponseList(ListView):
    model = AcsHttpResponse
    template_name = 'acs_http_response_list.html'
    paginate_by = 25


class AcsHttpResponseDetail(DetailView):
    model = AcsHttpResponse
    template_name = 'acs_http_response_detail.html'


class AcsDeviceModelList(ListView):
    model = AcsDeviceModel
    template_name = 'acs_device_model_list.html'
    paginate_by = 25


class AcsDeviceModelDetail(DetailView):
    model = AcsDeviceModel
    template_name = 'acs_device_model_detail.html'


class AcsDeviceCategoryList(ListView):
    model = AcsDeviceCategory
    template_name = 'acs_device_category_list.html'
    paginate_by = 25


class AcsDeviceCategoryDetail(DetailView):
    model = AcsDeviceCategory
    template_name = 'acs_device_category_detail.html'


class AcsDeviceVendorList(ListView):
    model = AcsDeviceVendor
    template_name = 'acs_device_vendor_list.html'
    paginate_by = 25


class AcsDeviceVendorDetail(DetailView):
    model = AcsDeviceVendor
    template_name = 'acs_device_vendor_detail.html'


class AcsDeviceList(ListView):
    model = AcsDevice
    template_name = 'acs_device_list.html'
    paginate_by = 25


class AcsDeviceDetail(DetailView):
    model = AcsDevice
    template_name = 'acs_device_detail.html'


class AllAcsSessions(ListView):
    model = AcsSession
    template_name = 'acs_session_list.html'
    paginate_by = 100

    def get_queryset(self):
        return AcsSession.objects.filter(acs_device_id=self.kwargs['pk'])

