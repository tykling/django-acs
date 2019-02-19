from lxml import etree
from defusedxml.lxml import fromstring
import uuid

from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist

from acs.response import get_soap_envelope
from acs.models import AcsHttpBaseModel
from acs.utils import create_xml_document

class AcsHttpRequest(AcsHttpBaseModel):
    """ Every HTTP request received on the ACS server URL is saved as an instance
        of this model. """

    acs_session = models.ForeignKey('acs.AcsSession', related_name='acs_http_requests', on_delete=models.PROTECT)
    rpc_response_to = models.ForeignKey('acs.AcsHttpResponse', related_name='rpc_responses', null=True, blank=True, on_delete=models.PROTECT) # a foreignkey to the http response containing the acs rpc request which triggered the current http request (where relevant)
    request_headers = models.TextField(blank=True)
    request_xml_valid = models.BooleanField(default=False)
    request_soap_valid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return str(self.tag)

    def get_absolute_url(self):
        return reverse('acshttprequest_detail', kwargs={'pk': self.pk})

    @property
    def is_request(self):
        return True

    @property
    def is_response(self):
        return False

    def get_response(self, empty_response=False):
        '''
        get_response() is called when the CPE is waiting for the ACS
        to do something. This happens after the CPE does an empty POST, or after
        the CPE has responded to an RPC call initiated by the ACS. It simply pops
        a job from the queue and returns it in a http response.
        '''
        job = False
        if not empty_response:
            ### get the first job from the queue (if any)
            #jobs = AcsQueueJob.objects.filter(acs_device=self.acs_session.acs_device, processed=False).order_by('created_date')
            jobs = self.acs_session.acs_device.acs_queue_jobs.filter(processed=False).order_by('created_date')
            self.acs_session.acs_log("Found %s unprocessed acs queue jobs for the device %s" % (jobs.count(), self.acs_session.acs_device))
            if jobs:
                job = jobs.first()
                self.acs_session.acs_log("Picked job %s" % job)

        if not empty_response and job:
            ### get blank SOAP response envelope
            response_cwmp_id = uuid.uuid4().hex
            root, body = get_soap_envelope(response_cwmp_id, self.acs_session)

            ### add the cwmp soap object to the soap body
            cwmpobj = fromstring(job.cwmp_rpc_object_xml.encode('utf-8'))
            body.append(cwmpobj)

            ### get the rpc method
            response_cwmp_rpc_method = job.cwmp_rpc_method

            ### put HTTP response together
            output = etree.tostring(root, encoding='utf-8', xml_declaration=True)
            response = HttpResponse(output, content_type='text/xml; charset=utf-8')
        else:
            ### no jobs in queue for this acs device (or an empty response was requested), so return empty body to end this cwmp session
            response = HttpResponse(status=204)
            response_cwmp_rpc_method = '(empty response body)'
            response_cwmp_id = ''

        ### save the http response
        from acs.models import AcsHttpResponse
        acs_http_response = AcsHttpResponse.objects.create(
            http_request=self,
            fk_body=create_xml_document(xml=response.content),
            cwmp_id=response_cwmp_id,
            soap_element="{%s}%s" % (self.acs_session.soap_namespaces['cwmp'], response_cwmp_rpc_method),
        )
        self.acs_session.acs_log("Created ACS HTTP response %s" % acs_http_response)

        if job:
            self.acs_session.acs_log("Saving AcsQueueJob %s" % job)
            ### save job
            job.handled_in = acs_http_response
            job.processed = True
            job.save()

        ### all good, return response
        self.acs_session.acs_log("Responding to CPE %s with %s" % (self.acs_session.acs_device, response_cwmp_rpc_method))
        return response

