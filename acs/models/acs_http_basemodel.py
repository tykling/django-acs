from defusedxml.lxml import fromstring

from django.db import models
from django.conf import settings
from django.utils.functional import cached_property

from acs.models import AcsBaseModel


class AcsHttpBaseModel(AcsBaseModel):
    """ 
        This abstract model is used for the AcsHttpRequest and
        AcsHttpResponse models. It contains the common fields and
        methods shared by the two models.
    """
    fk_body = models.ForeignKey(
        settings.DJANGO_ACS['XML_STORAGE_MODEL'],
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    cwmp_id = models.CharField(
        max_length=100,
        blank=True
    )

    cwmp_rpc_method = models.CharField(
        max_length=100,
        blank=True
    )

    class Meta:
        abstract = True

    @property
    def soap_body(self):
        if not self.body:
            return False
        try:
            xmlroot = fromstring(bytes(self.body, 'utf-8'))
            # use settings.SOAP_NAMESPACES here since the namespace 'soap-env' does not depend on cwmp version
            return xmlroot.find('soap-env:Body', settings.SOAP_NAMESPACES)
        except Exception:
            return False

    @property
    def rpc_response(self):
        return self.rpc_responses.all().first()

    @cached_property
    def body(self):
        if self.fk_body:
            return self.fk_body.document
        else:
            return self.db_body

