from acs.models import AcsBaseModel
from django.urls import reverse
from django.db import models
from lxml import etree
from defusedxml.lxml import fromstring


class AcsQueueJob(AcsBaseModel):
    cwmp_rpc_object_xml = models.TextField()
    acs_device = models.ForeignKey('acs.AcsDevice', null=True, blank=True, related_name='acs_queue_jobs', on_delete=models.PROTECT)
    reason = models.CharField(max_length=200)
    automatic = models.BooleanField(default=False)
    urgent = models.BooleanField(default=False)
    notification_sent = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    handled_in = models.ForeignKey('acs.AcsHttpResponse', null=True, blank=True, related_name='queuejobs', on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return str(self.tag)

    def get_absolute_url(self):
        return reverse('acs_queue_job_detail', kwargs={'pk': self.pk})

    @property
    def cwmp_rpc_method(self):
        ### parse XML to etree object
        cwmpobj = fromstring(bytes(self.cwmp_rpc_object_xml, 'utf-8'))

        ### returns 'FooMethod' from string '{urn:dslforum-org:cwmp-1-0}FooMethod'
        try:
            method = cwmpobj.tag.replace('{%s}' % cwmpobj.nsmap[cwmpobj.prefix], '')
        except KeyError:
            method = None
        return method

    def add_job_tag_as_command_key(self):
        element = fromstring(bytes(self.cwmp_rpc_object_xml, 'utf-8'))
        cmdkey = etree.SubElement(element, 'CommandKey')
        cmdkey.text = self.tag
        self.cwmp_rpc_object_xml=etree.tostring(element, xml_declaration=True).decode('utf-8')
        self.save()

