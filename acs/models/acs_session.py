from datetime import timedelta
import uuid, logging

from acs.models import AcsBaseModel
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import DateTimeRangeField
from django.utils import timezone
from django.conf import settings

from acs.models import AcsHttpResponse, AcsQueueJob
from acs.utils import *
from acs.response import get_soap_xml_object

logger = logging.getLogger('django_acs.%s' % __name__)

class AcsSession(AcsBaseModel):
    """ An ACSSession model instance represents a single ACS session with
        an ACS device. Every HTTP request and HTTP response in that session
        is linked to the ACS session. The reference field can be used to record
        freehand info about the session."""

    acs_device = models.ForeignKey('acs.AcsDevice', null=True, blank=True, related_name='acs_sessions', on_delete=models.PROTECT)
    acs_session_id = models.UUIDField(default=uuid.uuid4)
    client_ip = models.GenericIPAddressField()
    client_ip_verified = models.BooleanField(default=False)
    reference = models.CharField(max_length=100, default='', blank=True)
    session_result = models.BooleanField(default=False)
    latest_rpc_method = models.CharField(max_length=100, default='', blank=True)
    session_end = models.DateTimeField(null=True, blank=True)
    _device_uptime = DateTimeRangeField(null=True, blank=True) # use the property device_uptime instead
    inform_eventcodes = ArrayField(models.TextField(), default=list, blank=True)
    cwmp_namespace = models.CharField(max_length=100, default='', blank=True)
    root_data_model = models.ForeignKey('acs.CwmpDataModel', null=True, blank=True, related_name='acs_sessions', on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_date']
        unique_together = (('acs_session_id', 'client_ip', 'active'),)

    def __str__(self):
        return str('%s (%s)' % (self.tag, self.hexid))

    def get_absolute_url(self):
        return reverse('acssession_detail', kwargs={'pk': self.pk})

    def add_acs_queue_job(self, cwmp_rpc_object_xml, reason, automatic=False, urgent=False):
        '''
        add_acs_queue_job() adds an AcsQueueJob or returns an existing if an 
        identical job already exists (not taking 'reason' into account)
        '''

        ### do we have any XML?
        if not cwmp_rpc_object_xml:
            self.acs_log('unable to add acs queue job for acs_device %s, reason "%s": no XML found!' % (self.acs_device.tag, reason))
            return False
        ### get or create job and return it
        try:
            job, created = AcsQueueJob.objects.get_or_create(
                acs_device=self.acs_device,
                cwmp_rpc_object_xml=cwmp_rpc_object_xml.decode('utf-8'),
                processed=False,
                urgent=urgent,
                defaults={
                    'reason': reason,
                    'automatic': automatic,
                }
            )
        except AcsQueueJob.MultipleObjectsReturned:
            job = AcsQueueJob.objects.filter(
                acs_device=self.acs_device,
                cwmp_rpc_object_xml=cwmp_rpc_object_xml,
                processed=False,
                urgent=urgent,
            ).first()
            created = False

        self.acs_log('%(action)s acs queue job %(job)s for acs_device %(acs_device)s method %(method)s reason: "%(reason)s" urgent: %(urgent)s' % {
            'action': 'created' if created else 'returning',
            'job': job.tag,
            'acs_device': self.acs_device,
            'method': job.cwmp_rpc_method,
            'reason': job.reason,
            'urgent': job.urgent,
        })
        return job

    @property
    def configuration_done(self):
        """
        Check if we have done both SetParameterValues and SetParameterAttributes in this session
        """
        if self.acs_http_responses.filter(cwmp_rpc_method="SetParameterValues").exists() and self.acs_http_responses.filter(cwmp_rpc_method="SetParameterAttributes").exists():
            return True
        return False

    @property
    def post_configuration_collection_done(self):
        """
        After configuring a device we queue a GetParameterNames, GetParameterValues and GetParameterAttributes call.
        Check if this has been done or not.
        """
        # first get the id of the SetParameterValues call
        if not self.acs_http_responses.filter(cwmp_rpc_method="SetParameterValues").exists():
            # no SetParameterValues call found
            return False
        configcall = self.acs_http_responses.filter(cwmp_rpc_method="SetParameterValues").first()
        if self.acs_http_responses.filter(cwmp_rpc_method="GetParameterNames", id__gt=configcall.id).exists() and self.acs_http_responses.filter(cwmp_rpc_method="GetParameterValues", id__gt=configcall.id).exists() and self.acs_http_responses.filter(cwmp_rpc_method="GetParameterAttributes", id__gt=configcall.id).exists():
            return True
        return False

    def get_device_parameterdict(self, configdict):
        """
        Loop over keys in configdict and find the ACS parameter we need to set,
        add each to the parameterdict and return.
        """
        parameterdict = {}
        for key in list(configdict.keys()):
            parameterdict[self.get_acs_parameter_name(key)] = configdict[key]
        return parameterdict

    def configure_device_parameter_attributes(self, reason, parameterlist, update_parameterkey=False):
        """Takes a list of parameter names and configures them for active notification"""
        parameterdict = {}
        for param in parameterlist:
            parameterdict[param] = 1 # 2=active notification
        return self.acs_rpc_set_parameter_attributes(
            parameterdict=parameterdict,
            reason='configuring wifi device notifications (reason: %s)' % reason,
            automatic=True,
            update_parameterkey=update_parameterkey
        )

    def configure_device_parameter_values(self, reason, update_parameterkey=False):
        """ Configures ACS device """
        # initialize empty configdict
        configdict = {}

        # set InformInterval to 2 hours
        configdict['mrx.acs.informinterval'] = 7200

        # enable ACS managed firmware upgrades (disables manufacturer/provider upgrades)
        configdict['mrx.acs.acs_managed_upgrades'] = True

        # add acs client xmpp settings (only if we have an xmpp account for this device)
        if self.acs_device.acs_xmpp_password:
            configdict['mrx.acs.xmpp_server'] = settings.ACS_XMPP_SERVERTUPLE[0]
            configdict['mrx.acs.xmpp_server_port'] = settings.ACS_XMPP_SERVERTUPLE[1]
            configdict['mrx.acs.xmpp_connection_enable'] = True
            configdict['mrx.acs.xmpp_connection_username'] = self.acs_device.acs_xmpp_username
            configdict['mrx.acs.xmpp_connection_password'] = self.acs_device.acs_xmpp_password
            configdict['mrx.acs.xmpp_connection_domain'] = settings.ACS_XMPP_DOMAIN # all ACS clients connect to the same XMPP server domain for now
            configdict['mrx.acs.xmpp_connection_usetls'] = True
            configdict['mrx.acs.xmpp_connreq_connection'] = '%s.XMPP.Connection.1.' % self.root_data_model.root_object

        # set connectionrequest credentials?
        if self.acs_device.acs_connectionrequest_username:
            configdict['mrx.acs.connection_request_user'] = self.acs_device.acs_connectionrequest_username
            configdict['mrx.acs.connection_request_password'] = self.acs_device.acs_connectionrequest_password

        # get device specific config from the related device and add it to the configdict
        if self.acs_device.get_related_device():
            configdict.update(self.acs_device.get_related_device().get_acs_config())

        # get a parameterdict suitable for this device by feeding our configdict to this devices get_parameterdict_from_configdict() method
        parameterdict = self.get_device_parameterdict(configdict)

        # queue and return the job
        return self.acs_rpc_set_parameter_values(
            parameterdict=parameterdict,
            reason='configuring wifi device (reason: %s)' % reason,
            automatic=True,
            update_parameterkey=update_parameterkey
        )

    def configure_device(self):
        """
        Method to determine if the acs device should be configured.
        Returns True if device does not need config, or cannot be configured because we don't have enough information.
        Return False if an attempt to queue jobs to configure the device fails.
        """
        if not self.acs_device.get_related_device():
            self.acs_log("Not configuring %s: We refuse to put configuration on an acs device if it has no related device" % self.acs_device)
            return True

        if not self.acs_device.get_related_device().is_configurable():
            self.acs_log("Not configuring %s: The real device which this acs_device is related to is not configurable" % self.acs_device)
            return True

        if not self.client_ip_verified:
            self.acs_log("Not configuring %s: This acs_session is not ip_verified" % self.acs_device)
            return True

        if self.acs_device.current_config_level and self.acs_device.current_config_level >= self.acs_device.get_desired_config_level():
            self.acs_log("Not configuring %s: This acs_device is already at least at the config_level we want it to be at" % self.acs_device)
            return True

        # we need to configure this device! but what is the reason?
        if self.acs_device.current_config_level:
            reason="Device config level is wrong (it is %s but it should be %s)" % (self.acs_device.current_config_level, self.acs_device.get_desired_config_level())
        else:
            reason="Device is unconfigured/has been factory defaulted"

        # we need to update parameterkey in both calls even though we have more work to do,
        # because it appears the parameterkey is not updated after a SetParameterAttributes call for some reason
        if not self.configure_device_parameter_values(reason=reason, update_parameterkey=True):
            self.acs_log('error, unable to create acs job to configure device parameter values for %s' % self.acs_device)
            return False

        # get the list of parameters we want to set notification on
        parameterlist = self.acs_device.model.get_active_notification_parameterlist(self.root_data_model.root_object)

        # queue the job to set active notifications
        if not self.configure_device_parameter_attributes(reason=reason, parameterlist=parameterlist, update_parameterkey=True):
            self.acs_log('error, unable to create acs job to configure parameter attributes for %s' % self.acs_device)
            return False

        # all done
        return True

    def device_firmware_upgrade(self):
        if not self.acs_device.get_related_device():
            # we refuse to upgrade acs devices with no related device
            return True

        if not self.acs_device.get_related_device().is_configurable():
            # the related device is not configurable
            return True

        if not self.client_ip_verified:
            # this acs session is not ip verified
            return True

        if not self.acs_device.get_desired_software_version():
            # we cannot upgrade a device if we dont know its current software version
            return True

        if self.acs_device.get_desired_software_version() == self.acs_device.current_software_version:
            # this device has the software version we want it to
            return True

        # check if we have already done a Download RPC call in this session
        if self.acs_http_responses.filter(cwmp_rpc_method='Download').exists():
            # we already have a Download job in this session, one must be enough
            return True

        # OK, queue the firmware upgrade
        self.acs_log("%s has wrong software version (current: %s - desired: %s), queueing download job" % (self.acs_device, self.acs_device.current_software_version, self.acs_device.get_desired_software_version()))
        job = self.acs_rpc_download(
            parameterdict={
               'url': self.acs_device.get_software_url(version=self.acs_device.get_desired_software_version())
            },
            reason='Current software version %s differs from desired software version %s' % (self.acs_device.current_software_version, self.acs_device.get_desired_software_version()),
            automatic=True,
        )
        if not job:
            message = 'error, unable to create acs queue job for %s' % self.acs_device
            self.acs_log(message)
            return False

        # all good
        return True

    def collect_device_info(self, reason):
        """
        Called in the beginning of the Inform, and after configuring device, to gather all information we can from the acs device
        """
        if not self.get_all_parameter_names(reason):
            self.acs_log('error, unable to create GetParameterNames acs queue job for %s' % self.acs_device)
            return False

        if not self.get_all_parameter_values(reason):
            self.acs_log('error, unable to create GetParameterValues acs queue job for %s' % self.acs_device)
            return False

        if not self.get_all_parameter_attributes(reason):
            self.acs_log('error, unable to create GetParameterAttributes acs queue job for %s' % self.acs_device)
            return False

        # all good
        return True

    def get_all_parameter_names(self, reason):
        # get all parameter names in the tree
        return self.acs_rpc_get_parameter_names(
            reason=reason,
            parampath='',
            nextlevel='0',
            automatic=True,
        )

    def get_all_parameter_values(self, reason):
        # get all parameter values under the root element
        return self.acs_rpc_get_parameter_values(
            reason=reason,
            parameterlist=['%s.' % self.root_data_model.root_object],
            automatic=True,
        )

    def get_all_parameter_attributes(self, reason):
        # get all parameter attributes under Device.
        return self.acs_rpc_get_parameter_attributes(
            reason=reason,
            parameterlist=['%s.' % self.root_data_model.root_object],
            automatic=True,
        )

    def get_acs_parameter_name(self, parametername):
        """
        Converts something like mrx.acs.parameterkey to Device.ManagementServer.ParameterKey based on the root_data_model in use in this session.
        """
        # TODO: Does not currently support device overrides!
        if not self.root_data_model:
            return False
        root_object = self.root_data_model.root_object
        element = settings.DEFAULT_ACS_DEVICE_PARAMETER_MAP[parametername]
        return "%s.%s" % (root_object, element)

    def get_inform_eventcodes(self, inform, acshttprequest):
        # get Event element from Inform request
        event = inform.find('Event')
        if event is None:
            message = 'Invalid Inform, Event missing from request %s' % acshttprequest
            self.acs_log(message)
            return False

        # get the EventCode(s) for this inform
        eventcodes = []
        for es in event.findall('EventStruct'):
            message = 'Found EventStruct with EventCode %s inside Inform' % es.find('EventCode').text
            self.acs_log(message)
            eventcodes.append(es.find('EventCode').text)

        if not eventcodes:
            message = 'EventStruct sections mising from Event in request %s' % acshttprequest
            self.acs_log(message)
        else:
            self.inform_eventcodes = eventcodes

        # return true even if we didn't find any eventcodes
        return True

    def get_all_values_rpc_response(self):
        """
        Loop over the GetParameterValuesResponse http requests in this acs session and find
        one asking for the whole device tree
        """
        for httpreq in self.acs_http_requests.filter(cwmp_rpc_method='GetParameterValuesResponse'):
            if httpreq.soap_body.find('cwmp:GetParameterValuesResponse', self.soap_namespaces).xpath('.//string[text()="%s."]' % self.root_data_model.root_object) is not None:
                # one of the requested values is Device. - great! return this request
                return httpreq
        # nothing found
        return False

    def get_all_names_rpc_response(self):
        """
        Loop over the GetParameterNamesResponse http requests in this acs session and find
        one asking for the whole device tree
        """
        for httpreq in self.acs_http_requests.filter(cwmp_rpc_method='GetParameterNamesResponse'):
            if httpreq.soap_body.find('cwmp:GetParameterNamesResponse', self.soap_namespaces).xpath('.//string[text()="%s."]' % self.root_data_model.root_object) is not None:
                # one of the requested values is Device. - great! return this request
                return httpreq
        # nothing found
        return False


    def determine_data_model(self, inform):
        """
        Find the tr-069 data model in use based on the information in the Inform
        This would be a bit of a faff if the devices all followed the cwmp specs.
        Since the devices don't follow the specs this is actually a massive faff.
        """
        # get parameterlist
        parameterlist = inform.find('ParameterList')

        # try getting Device.DeviceSummary
        summary = get_value_from_parameterlist(parameterlist, 'Device.DeviceSummary')
        if summary:
            #  this is some version of an Device:1 device, we can get the exact datamodel version from Device.DeviceSummary
            datamodel = get_datamodel_from_devicesummary(summary)
            if datamodel:
                return datamodel

        # try getting InternetGatewayDevice.DeviceSummary
        summary = get_value_from_parameterlist(parameterlist, 'InternetGatewayDevice.DeviceSummary')
        if summary:
            #  this is some version of an InternetGatewayDevice:1 device, we can get the exact datamodel version from InternetGatewayDevice.DeviceSummary
            datamodel = get_datamodel_from_devicesummary(summary)
            if datamodel:
                return datamodel

        # this might be InternetGatewayDevice:1.0 which did not have InternetGatewayDevice.DeviceSummary.
        # if we have some value under InternetGatewayDevice and we got this far, this must be data model "InternetGatewayDevice:1.0"
        if get_value_from_parameterlist(parameterlist, 'InternetGatewayDevice.DeviceInfo.SoftwareVersion'):
            return "InternetGatewayDevice:1.0"

        # this must be a Device:2.x data model, check if we have Device.RootDataModelVersion
        if get_value_from_parameterlist(parameterlist, 'Device.RootDataModelVersion'):
            return "Device:%s" % get_value_from_parameterlist(parameterlist, 'Device.RootDataModelVersion')

        # this device datamodel is between Device:2.0 and Device:2.3,
        # no idea how to figure out which one until we see a device of this type,
        # to be conservative and assume the lowest version
        return "Device:2.0"

    @property
    def cwmp_version(self):
        if self.cwmp_namespace == "urn:dslforum-org:cwmp-1-0":
            return "1.0"
        elif self.cwmp_namespace == "urn:dslforum-org:cwmp-1-1":
            return "1.1"
        elif self.cwmp_namespace == "urn:dslforum-org:cwmp-1-2":
            return "1.2"
        elif self.cwmp_namespace == "urn:dslforum-org:cwmp-1-3":
            return "1.3"
        elif self.cwmp_namespace == "urn:dslforum-org:cwmp-1-4":
            return "1.4"
        else:
            return False

    def acs_log(self, message):
        logger.info('acs session %s: %s' % (self.tag, message))

    @property
    def device_uptime(self):
        """
        Lazily populated fake field, added february 2018. Returns the value straight from the model if one is present,
        otherwise extracts the value from the device acs_parameters XML and saves it in the session model, and then returns it
        """
        if self._device_uptime:
            return self._device_uptime
        else:
            return self.update_device_uptime()

    def update_device_uptime(self):
        """
        Update _device_uptime by finding the relevant value in the acs parameters of the device
        """
        if not self.acs_device:
            return False
        uptime_seconds = self.acs_device.acs_get_parameter_value(self.get_acs_parameter_name('mrx.deviceinfo.uptime'))
        if uptime_seconds:
            self._device_uptime = (timezone.now()-timedelta(seconds=int(uptime_seconds)), timezone.now())
            self.save()
        return self._device_uptime

    @property
    def hexid(self):
        return self.acs_session_id.hex

    @property
    def soap_namespaces(self):
        if not self.cwmp_namespace:
            # cannot determine namespaces without knowing which cwmp version we are using
            return False

        # add the cwmp namespace to the settings.SOAP_NAMESPACES dict and return
        namespaces = settings.SOAP_NAMESPACES
        namespaces.update({
            'cwmp': self.cwmp_namespace,
        })
        return namespaces

    @property
    def start(self):
        return self.created_date

    @property
    def end(self):
        if not self.session_end:
            self.session_end = self.acs_http_responses.latest('created_date').created_date
            self.save()
        return self.session_end

    @property
    def duration(self):
        return self.end - self.start

    @property
    def bytes_in(self):
        bytes_in = 0
        for http in self.acs_http_requests.all():
            bytes_in += len(http.body)
        return bytes_in

    @property
    def bytes_out(self):
        ### this could probably be done really elegantly with .aggregate and Sum somehow
        bytes_out = 0
        for resp in self.acs_http_responses.all():
            bytes_out += len(resp.body)
        return bytes_out

    @property
    def acs_http_responses(self):
        return AcsHttpResponse.objects.filter(http_request__acs_session=self).order_by('-created_date')

    @property
    def acs_http_conversationlist(self):
        conversationlist = []
        for req in self.acs_http_requests.all():
            if req.acs_http_response:
                conversationlist.append(req.acs_http_response)
            conversationlist.append(req)
        return conversationlist

    def get_latest_http_tx(self):
        # this might need to be wrapped in a try/except for weird cases
        try:
            return self.acs_http_conversationlist[0]
        except IndexError:
            return False

    def update_session_result(self):
        latest_tx = self.get_latest_http_tx()
        self.latest_rpc_method = latest_tx.cwmp_rpc_method
        self.session_end = latest_tx.created_date
        if self.latest_rpc_method != '(empty response body)' or latest_tx.is_request:
            # the last http tx in this acs session is not an http response with the cwmp_rpc_method '(empty response body)' so something is fucky
            self.session_result=False
        else:
            self.session_result=True
        self.save()

    def get_latest_rpc_method(self):
        if not self.latest_rpc_method:
            # this might need to be wrapped in a try/except for weird cases
            latesttx = self.get_latest_http_tx()
            if latesttx:
                # update self.latest_rpc_method
                self.latest_rpc_method = self.get_latest_http_tx().cwmp_rpc_method
                self.save()
        return self.latest_rpc_method


###########################################################################################################
### ACS RPC METHODS BELOW HERE

    ### GetRPCMethods
    def acs_rpc_get_rpc_methods(self, reason, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'GetRPCMethods'
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### SetParameterValues
    def acs_rpc_set_parameter_values(self, reason, parameterdict, automatic=False, urgent=False, update_parameterkey=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'SetParameterValues',
                datadict=parameterdict,
                update_parameterkey=update_parameterkey
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### GetParameterValues
    def acs_rpc_get_parameter_values(self, reason, parameterlist, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'GetParameterValues', datadict={
                    'parameterlist': parameterlist
                }
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job


    ### GetParameterNames
    def acs_rpc_get_parameter_names(self, reason, parampath='', nextlevel='0', automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'GetParameterNames', datadict={
                    'parampath': parampath,
                    'nextlevel': nextlevel,
                }
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### GetParameterAttributes
    def acs_rpc_get_parameter_attributes(self, reason, parameterlist, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'GetParameterAttributes', datadict={
                    'parameterlist': parameterlist
                }
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### SetParameterAttributes
    def acs_rpc_set_parameter_attributes(self, reason, parameterdict, automatic=False, urgent=False, update_parameterkey=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'SetParameterAttributes',
                datadict=parameterdict,
                update_parameterkey=update_parameterkey
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### AddObject
    def acs_rpc_add_object(self, reason, objectname, automatic=False, urgent=False, update_parameterkey=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'AddObject',
                datadict={
                    'objectname': objectname
                },
                update_parameterkey=update_parameterkey
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### DeleteObject
    def acs_rpc_delete_object(self, reason, objectname, automatic=False, urgent=False, update_parameterkey=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object(
                'DeleteObject',
                datadict={
                    'objectname': objectname
                },
                update_parameterkey=update_parameterkey
            ),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### Reboot
    def acs_rpc_reboot(self, reason, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object('Reboot'),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        job.add_job_tag_as_command_key()
        return job

    ### Download
    def acs_rpc_download(self, reason, parameterdict, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object('Download', datadict=parameterdict),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        job.add_job_tag_as_command_key()
        return job

    ### Upload
    def acs_rpc_upload(self, reason, parameterdict, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object('Upload', datadict=parameterdict),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### FactoryReset
    def acs_rpc_factory_reset(self, reason, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object('FactoryReset'),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

    ### ScheduleInform
    def acs_rpc_schedule_inform(self, reason, parameterdictdict, automatic=False, urgent=False):
        job = self.add_acs_queue_job(
            cwmp_rpc_object_xml=get_soap_xml_object('ScheduleInform', datadict=parameterdict),
            reason=reason,
            urgent=urgent,
            automatic=automatic,
        )
        return job

