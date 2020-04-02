from acs.models import AcsBaseModel
from lxml import etree
import requests
from defusedxml.lxml import fromstring
from os import urandom
from collections import OrderedDict
import logging
from random import choice

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist

from acs.response import get_soap_xml_object
from acs.utils import run_ssh_command, get_value_from_parameterlist
from acs.conf import acs_settings

logger = logging.getLogger('django_acs.%s' % __name__)


class AcsDevice(AcsBaseModel):
    model = models.ForeignKey('acs.AcsDeviceModel', related_name="acsdevices", on_delete=models.PROTECT)
    serial = models.CharField(max_length=100)
    current_config_level = models.DateTimeField(null=True, blank=True)
    desired_config_level = models.DateTimeField(null=True, blank=True)
    current_software_version = models.CharField(max_length=50, blank=True)
    desired_software_version = models.CharField(max_length=50, blank=True)
    acs_xmpp_password = models.CharField(max_length=50, blank=True)
    acs_latest_inform = models.DateTimeField(null=True, blank=True)
    acs_latest_session_result = models.BooleanField(default=None, null=True, blank=True)
    acs_inform_count = models.PositiveIntegerField(default=0)
    acs_parameters = models.TextField(blank=True)
    acs_parameters_time = models.DateTimeField(null=True, blank=True)
    imported = models.BooleanField(default=False)
    acs_connectionrequest_password = models.CharField(max_length=50, blank=True)

    class Meta:
        # make sure we only ever have one device of a given model with a given serial number
        unique_together=('serial', 'model')

    def __str__(self):
        return str(self.tag)

    def get_absolute_url(self):
        return reverse('acs_device_detail', kwargs={'pk': self.pk})

    @property
    def latest_acs_session(self):
        try:
            return self.acs_sessions.latest('created_date')
        except ObjectDoesNotExist:
            return False

    def handle_user_config_changes(self):
        '''
        Check self.acs_parameters for changes to settings configurable by the user
        '''
        # check for device specific changes
        #changelist = self.get_related_device().get_user_config_changelist()
        changelist = None
        if changelist:
            # one or more device specific configuration elements has changed, update our end
            logger.warning("Wanted to reconfigure acs device %s due to user config changes, disabled waiting for TA approval. Changed items: %s" % (self, changelist))
            #self.get_related_device().handle_user_config_change(changelist)
            pass

    def get_desired_config_level(self):
        '''
        Return the desired config level (from the device where relevant, otherwise from the device model)
        '''
        if self.desired_config_level:
            return self.desired_config_level
        else:
            return self.model.desired_config_level

    def get_desired_software_version(self):
        '''
        Return the desired software version (from the device where relevant, otherwise from the device model)
        '''
        if self.desired_software_version:
            return self.desired_software_version
        else:
            return self.model.desired_software_version

    def get_software_url(self, version):
        '''
        Return the full URL to the specified software version for the model of this acs device.
        Must be plaintext http because our 4920 devices https support is nonexistant.
        Must be on an alternative port because our 4920 devices do not speak http/1.1 properly.
        Hostname hardcoded... not sure why.
        '''
        return '%s/%s-%s' % (settings.ACS_DOWNLOAD_URL, self.model.tag.replace('#', '_'), version)

    @property
    def acs_xmpp_username(self):
        return self.tag.replace("#", "")

    @property
    def acs_connectionrequest_username(self):
        return self.tag.replace("#", "")

    def create_xmpp_user(self):
        if self.acs_xmpp_password:
            ### we already have an xmpp password, bail out
            return False

        ### generate new xmpp password
        password = ''.join(choice(settings.PASSWORD_ALPHABET) for i in range(settings.ACS_XMPP_PASSWORD_LENGTH))

        ### create xmpp account for this acs device
        result = run_ssh_command(
            server=settings.ACS_XMPP_SSH_SERVER,
            username=settings.ACS_XMPP_SSH_USER,
            private_key=settings.ACS_XMPP_SSH_PRIVKEY,
            command='register %(user)s %(domain)s %(password)s' % {
                'user': self.tag,
                'domain': settings.ACS_XMPP_DOMAIN,
                'password': password,
            }
        )

        if result['result'] and result['exit_status'] == 0:
            self.acs_xmpp_password = password
            self.save()
            return True
        else:
            ### got exception or non-0 exit code
            if 'exception' in result:
                logger.error("got exception while creating xmpp user for %s: %s" % (self.tag, result['exception']))
            else:
                logger.error("got non-0 exit code while creating xmpp user for %s: %s and the output: %s" % (self.tag, result['exit_status'], result['errorlines']))
            return False

    def create_connreq_password(self):
        # generate a random 50 chars connreq password for this acs device
        self.acs_connectionrequest_password = ''.join(choice(settings.PASSWORD_ALPHABET) for i in range(50))
        self.save()

    def update_acs_parameters(self, attributes_rpc_response):
        """
        This method takes an AcsHttpRequest object with a GetParameterAtrributesResponse inside. It checks if the GetParameterAtrributesResponse is a response to
        a GetParameterAtrributes for the root object (like Device.)  and if so, checks the acs session for a GetParameterNames RPC request for the whole tree (aka parampath="" and nextlevel=0),
        and a GetParameterAttributes RPC request for the whole tree (aka "Device."). It then uses the info in the three RPC responses to build an XML tree and save it in self.acs_parameters
        """
        # get the acs_session for convenience
        acs_session = attributes_rpc_response.acs_session
        starttime = timezone.now()

        logger.debug(attributes_rpc_response)

        # 1) check if this GetParameterAtrributesResponse is a response to a GetParameterAtrributes RPC call for the whole tree...
        if attributes_rpc_response.rpc_response_to.soap_body.find('cwmp:GetParameterAttributes', acs_session.soap_namespaces).xpath('.//string[text()="%s."]' % acs_session.root_data_model.root_object) is None:
            acs_session.acs_log("GetParameterAttributesResponse seen, but it is not a response to a GetParameterAttributes for '%s.' - not updating acs_device.acs_parameter" % acs_session.root_data_model.root_object)
            return False

        ### check if we have the other two required responses in this acs session, so we can build the tree for this device.
        ### 2) Did we also complete a GetParameterValues call for the full tree in this acs session?
        values_rpc_response = acs_session.get_all_values_rpc_response()
        if not values_rpc_response:
            acs_session.acs_log("No GetParameterValues for the full tree found in this session, not updating acs_device.acs_parameters")
            return False

        ### 3) Did we also complete a GetParameterNames RPC with parampath='' and nextlevel=0 in this acs session?
        names_rpc_response = acs_session.get_all_names_rpc_response()

        if not names_rpc_response:
            acs_session.acs_log("No GetParameterNames for the full tree found in this session, not updating acs_device.acs_parameters")
            return False

        ### OK, ready to update the parameters...

        # get ParameterList from namesrequest and build a dict
        names_param_list = names_rpc_response.soap_body.find('cwmp:GetParameterNamesResponse', acs_session.soap_namespaces).find('ParameterList')
        writabledict = {}
        for child in names_param_list.iterchildren():
            writabledict[child.xpath("./Name")[0].text] = child.xpath("./Writable")[0].text

        # get ParameterList from GetParameterAttributesResponse and build a dict of lists of attributes
        attributes_param_list = attributes_rpc_response.soap_body.find('cwmp:GetParameterAttributesResponse', acs_session.soap_namespaces).find('ParameterList')
        attributedict = {}
        for child in attributes_param_list.iterchildren():
            attribs = []
            name = child.xpath("Name")[0]
            for attrib in name.itersiblings():
                attribs.append(attrib)
            attributedict[child.xpath("Name")[0].text] = attribs

        root = etree.Element("DjangoAcsParameterCache")
        ### loop through all params in valuesrequest
        paramcount = 0
        param_omitted_count = 0
        for param in values_rpc_response.soap_body.find('cwmp:GetParameterValuesResponse', acs_session.soap_namespaces).find('ParameterList').getchildren():
            paramname = param.xpath("Name")[0].text
            paramcount += 1

            # not all params have a lifetime that lasts until values are retrieved
            # in which case they are omitted
            if paramname in attributedict:
                writable = etree.Element("Writable")
                # add writable value if we can find it
                if paramname in writabledict:
                    writable.text = writabledict[paramname]
                param.append(writable)

                # append acl and notification (and any future attributes that may appear) to our tree
                for attrib in attributedict[paramname]:
                    param.append(attrib)

                # append this to the tree
                root.append(param)
            else:
                param_omitted_count += 1

        ### alright, save the tree
        self.acs_parameters = etree.tostring(root, xml_declaration=True).decode('utf-8')
        self.acs_parameters_time = timezone.now()
        self.save()
        acs_session.acs_log("Finished processing %s acs parameters (%s parameters omitted) for device %s" % (paramcount, param_omitted_count, self))
        return True

    @property
    def acs_parameter_dict(self):
        if not self.acs_parameters:
            return False
        xmlroot = fromstring(bytes(self.acs_parameters, 'utf-8'))
        paramdict = {}
        for child in xmlroot.iterchildren():
            value = child.find('Value')
            paramdict[child.find('Name').text] = {
                'type': value.attrib['{%s}type' % acs_settings.SOAP_NAMESPACES['xsi']],
                'value': value.text,
                'writable': child.find('Writable').text,
                'notification': child.find('Notification').text if child.find('Notification') is not None else "N/A",
                'accesslist': ",".join([acl.text for acl in child.find('AccessList').getchildren()]) if child.find('AccessList') is not None else "N/A",
            }
        return OrderedDict(sorted(paramdict.items()))

    @property
    def acs_connection_request_url(self):
        if not self.latest_acs_session:
            # we have not had any acs sessions for this device
            return False
        root_object = self.latest_acs_session.root_data_model.root_object
        return self.acs_get_parameter_value('%s.ManagementServer.ConnectionRequestURL' % root_object)

    def acs_get_parameter_value(self, parameterpath):
        if not self.acs_parameters or not parameterpath:
            return False
        xmlroot = fromstring(bytes(self.acs_parameters, 'utf-8'))
        pvslist = xmlroot.xpath('./ParameterValueStruct/Name[text()="%s"]/..' % parameterpath)
        if pvslist:
            valuelist =  pvslist[0].xpath('./Value')
            if not valuelist:
                return False
            return valuelist[0].text
        else:
            logger.error("unable to find %s in acs_parameters :(" % parameterpath)
            return False

    def acs_http_connection_request(self):
        ### get what we need
        url = self.acs_connection_request_url
        if not url or not self.acs_connectionrequest_password:
            logger.error("unable to make a connectionrequest without url or credentials")
            return False

        ### do the request
        try:
            return requests.get(url, auth=requests.auth.HTTPBasicAuth(self.acs_connectionrequest_username, self.acs_connectionrequest_password))
        except requests.exceptions.ConnectionError as E:
            ### catching this exception is neccesary because requests does not catch the exception which httplib returns,
            ### because our HTTP servers are closing connection "too fast" without ever sending an HTTP response
            logger.exception("got exception %s while running HTTP request" % E)
            return False

    @property
    def nonautomatic_acs_queue_jobs(self):
        return self.acs_queue_jobs.filter(automatic=False)

    @property
    def unprocessed_acs_queue_jobs(self):
        return self.acs_queue_jobs.filter(processed=False)

    def get_related_device(self):
        """
        Loops over models in settings.ACS_DEVICE_DJANGO_MODELS and checks each to find
        the related device (if any).
        Returns the related device or None
        """
        for acsmodel in settings.ACS_DEVICE_DJANGO_MODELS:
            devicemodel = apps.get_model(acsmodel['app'], acsmodel['model'])
            kwargs = {
                acsmodel['acsdevice_relation_field']: self
            }
            try:
                return devicemodel.objects.get(**kwargs)
            except devicemodel.DoesNotExist:
                # no match in this model, try the next
                pass

    @property
    def latest_client_ip(self):
        """Return the client ip address of the latest acs session for this acs device (if any)"""
        if self.acs_sessions.exists():
            return self.acs_sessions.latest('id').client_ip
        else:
            return False

    def associate_with_related_device(self):
        """
        Find the real device which belongs to this acs device (if any),
        and create the foreignkey to this model as needed.
        """
        if self.get_related_device():
            # this acs_device is already associated with a device
            return

        # loop over configured acs models, checking each for a match for this acs device
        for acsmodel in settings.ACS_DEVICE_DJANGO_MODELS:
            devicemodel = apps.get_model(acsmodel['app'], acsmodel['model'])
            args = {
                acsmodel['serial_field']: self.serial,
                acsmodel['model_name_field']: self.model.name,
                acsmodel['vendor_name_field']: self.model.vendor.name,
                '%s__isnull' % acsmodel['acsdevice_relation_field']: True
            }
            try:
                device = devicemodel.objects.get(**args)
                setattr(device, acsmodel['acsdevice_relation_field'], self)
                device.save()
                # we are done here
                break
            except devicemodel.DoesNotExist:
                # no match found, this is fine
                pass


