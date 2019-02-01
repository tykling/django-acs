from django.db import models
from django.urls import reverse
from acs.models import AcsHttpBaseModel


class AcsHttpResponse(AcsHttpBaseModel):
    """ Every HTTP response given by the ACS server is saved as an instance of this model. """
    http_request = models.ForeignKey('acs.AcsHttpRequest', related_name='acs_http_responses', on_delete=models.PROTECT) # a foreignkey to the http request which triggered this http response
    rpc_response_to = models.ForeignKey('acs.AcsHttpRequest', related_name='rpc_responses', null=True, blank=True, on_delete=models.PROTECT) # a foreignkey to the http request containing the acs rpc request which triggered the current http response (where relevant)

    class Meta:
        ### make sure we only ever have one active http response pointing to a specific http request
        unique_together = ('http_request', 'active')
        ordering = ['-created_date']

    def __str__(self):
        return str(self.tag)

    def get_absolute_url(self):
        return reverse('acshttpresponse_detail', kwargs={'pk': self.pk})

    @property
    def is_request(self):
        return False

    @property
    def is_response(self):
        return True

    @property
    def queuejob(self):
        return self.queuejobs.all().first()

