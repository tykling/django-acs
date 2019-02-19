import re

from defusedxml.lxml import fromstring

from django.db import models
from django.conf import settings
from django.utils.functional import cached_property

from acs.models import AcsBaseModel
from acs.conf import acs_settings


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

    soap_element = models.CharField(
        max_length=100,
        blank=True
    )

    class Meta:
        abstract = True

    @cached_property
    def soap_element_ns(self):
        """
        Return a namespaced version of the soap_element, so
        "{urn:dslforum-org:cwmp-1-0}Inform" becomes "cwmp:Inform"
        Takes the cwmp version into account.
        """
        if not self.acs_session.soap_namespaces:
            # unable to get soap namespaces for this acs session, return unchanged
            return self.soap_element

        # loop over namespaces and find the right one
        for namespace, uri in self.acs_session.soap_namespaces.items():
            if uri in self.soap_element:
                # found the matching namespace
                return self.soap_element.replace("{%s}" % uri, "%s:" % namespace)

        # this is either an unknown uri or a non-namespaced soap element
        return self.soap_element

    @cached_property
    def soap_element_tuple(self):
        """
        Parse a soap element like {urn:dslforum-org:cwmp-1-0}Inform into a tuple like ("urn:dslforum-org:cwmp-1-0", "Inform")
        """
        match = re.match("{(.+)}(.+)", self.soap_element)
        if match:
            return match.groups()
        else:
            # unable to parse namespace from soap element, this must be non-namespaced
            return (None, self.soap_element)

    @cached_property
    def cwmp_rpc_method(self):
        """
        If this is a cwmp object return the cwmp_rpc_method
        """
        namespace, method = self.soap_element_tuple
        if namespace in acs_settings.CWMP_NAMESPACES:
            return method
        else:
            return False

    @cached_property
    def soap_body(self):
        if not self.body:
            return False
        try:
            xmlroot = fromstring(bytes(self.body, 'utf-8'))
            # use settings.SOAP_NAMESPACES here since the namespace 'soap-env' does not depend on cwmp version
            return xmlroot.find('soap-env:Body', settings.SOAP_NAMESPACES)
        except Exception:
            return False

    @cached_property
    def rpc_response(self):
        return self.rpc_responses.all().first()

    @cached_property
    def body(self):
        return self.fk_body.document

