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


class AcsServerView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        '''
        Like a general in a war, this dispatch method is only here to get decorated
        '''
        return super(AcsServerView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        ### get the client IP from the request
        ip = get_ip(request)
        informinterval = 7200 # informinterval should come from settings or something, hardcoded for now

        ### check if we have an acs session id in a cookie
        if 'acs_session_id' in request.COOKIES:
            hexid = request.COOKIES['acs_session_id']
            try:
                acs_session = AcsSession.objects.get(acs_session_id=hexid)
                acs_session.acs_log("got acs_session_id from acs_session_id cookie")
            except AcsSession.DoesNotExist:
                ### create a new AcsSession? only if we haven't already got enough sessions from this client ip
                sessions_since_informinterval = AcsSession.objects.filter(
                    client_ip=ip,
                    created_date__gt=timezone.now()-timedelta(seconds=informinterval),
                ).count()

                if sessions_since_informinterval > 3:
                    message = "acs session DENIED: the IP %s already has %s sessions the last %s seconds, no thanks" % (ip, sessions_since_informinterval, informinterval)
                    print(message)
                    return HttpResponse(status=420)

                acs_session = AcsSession.objects.create(
                    client_ip=ip,
                )
                hexid = acs_session.hexid
                acs_session.acs_log("got invalid acs_session_id %s from acs_session_id cookie, new acs session created" % request.COOKIES['acs_session_id'])
        else:
            ### no acs_session_id cookie seen, create a new AcsSession? only if we haven't already got enough sessions from this client ip
            sessions_since_informinterval = AcsSession.objects.filter(
                client_ip=ip,
                created_date__gt=timezone.now()-timedelta(seconds=informinterval),
            ).count()

            if sessions_since_informinterval > 1:
                message = "acs session DENIED: the IP %s already has %s sessions the last %s seconds, no thanks" % (ip, sessions_since_informinterval, informinterval)
                print(message)
                return HttpResponse(status=420)

            acs_session = AcsSession.objects.create(
                client_ip=ip,
            )
            ### and save the acs session ID (uuid.hex()) in the django session for later use
            hexid = acs_session.acs_session_id.hex
            acs_session.acs_log("created new acs session (had %s sessions in the latest informinterval)" % sessions_since_informinterval)

        ### do we have a body in this http request? attempt parsing it as XML if so
        validxml=False
        if request.body:
            try:
                xmlroot = fromstring(request.body)
                validxml=True
            except Exception as E:
                acs_session.acs_log('got exception parsing ACS XML: %s' % E)

        ### get all HTTP headers for this request
        headerdict = {}
        for key, value in request.META.items():
            ### in django all HTTP headers are prefixed with HTTP_ in request.META
            if key[:5] == 'HTTP_':
                headerdict[key] = value

        ### save this HTTP request to DB
        acs_http_request = AcsHttpRequest.objects.create(
            acs_session=acs_session,
            request_headers=json.dumps(headerdict),
            request_xml_valid=validxml,
            fk_body=create_xml_document(request.body)
        )
        acs_session.acs_log("saved acs http request %s to db" % acs_http_request)

        if request.body:
            ### bail out if we have a bad xml body
            if not validxml:
                message = 'Invalid XML body posted by client %s' % ip
                acs_session.acs_log(message)
                return HttpResponseBadRequest(message)

            ### figure out which cwmp version we are speaking (if any)
            if not 'cwmp' in xmlroot.nsmap:
                message = 'No cwmp namespace found in soap envelope, this is not a valid CWMP request posted by client %s' % ip
                acs_session.acs_log(message)
                return HttpResponseBadRequest(message)
            else:
                acs_session.cwmp_namespace = xmlroot.nsmap['cwmp']
                acs_session.save()

            ### parse soap header and body
            soap_header = xmlroot.find('soap-env:Header', acs_session.soap_namespaces)
            soap_body = xmlroot.find('soap-env:Body', acs_session.soap_namespaces)
            if soap_body is None:
                # a soap body is required..
                message = 'Unable to find SOAP body in xml posted by client %s' % ip
                acs_session.acs_log(message)
                return HttpResponseBadRequest(message)

            if soap_header is not None:
                ### parse the cwmp id from the soap header
                acs_http_request.cwmp_id = soap_header.find('cwmp:ID', acs_session.soap_namespaces).text

            ### parse the cwmp method from the soap Body (but first remove the cwmp namespace)
            acs_http_request.cwmp_rpc_method = list(soap_body)[0].tag.replace('{%s}' % acs_session.soap_namespaces['cwmp'], '')

            ### do we have exactly one soap object in this soap body?
            if len(list(soap_body)) != 1:
                acs_http_request.save()
                message = 'Only one cwmp object per soap envelope please (client: %s)' % ip
                acs_session.acs_log(message)
                return HttpResponseBadRequest(message)
            else:
                ### this appears (for now) to be a valid soap envelope
                acs_http_request.request_soap_valid = True
        else:
            ### empty request body, this means that the CPE is done for now
            acs_http_request.cwmp_id = ''
            acs_http_request.cwmp_rpc_method = '(empty request body)'

        ### save the http request
        acs_http_request.save()

        ################# http request saved to acs session, now we have to put a response together ##################
        ################# at this point we still have not associated the acs session with an acs device, #############
        ################# and we can only do so if we have a valid inform with vendor, serial etc. for the device ####
        if not acs_session.acs_device:
            # we only permit Inform requests when we have no device
            if acs_http_request.cwmp_rpc_method != "Inform":
                message = 'An ACS session must begin with an Inform, not %s' % acs_http_request.cwmp_rpc_method 
                acs_session.acs_log(message)
                return HttpResponseBadRequest(message)
 
        ### initialize a variable
        empty_response=False
        ### first things first, do we have a body in the http request?
        if request.body:
            if acs_http_request.cwmp_rpc_method in settings.CWMP_ACS_VALID_RPC_METHODS:
                ####################################################################################################
                acs_session.acs_log('the ACS client %s is calling a valid RPC method on the ACS server: %s' % (ip, acs_http_request.cwmp_rpc_method))

                ### get SOAP response envelope
                root, body = get_soap_envelope(acs_http_request.cwmp_id, acs_session)

                ### set a few variables used when saving the HTTP response to db
                response_cwmp_rpc_method = '%sResponse' % acs_http_request.cwmp_rpc_method
                response_cwmp_id = acs_http_request.cwmp_id

                ### parse the soap request (which ACS RPC method is the CPE calling?)
                if acs_http_request.cwmp_rpc_method == 'Inform':
                    ### get Inform xml element
                    inform = soap_body.find('cwmp:Inform', acs_session.soap_namespaces)

                    ### determine which data model version this device is using
                    datamodel, created = CwmpDataModel.objects.get_or_create(
                        name=acs_session.determine_data_model(inform)
                    )
                    acs_session.acs_log("ACS client is using data model %s" % datamodel)
                    acs_session.root_data_model = datamodel

                    #########################################################################
                    ### get deviceid element from Inform request
                    deviceid = inform.find('DeviceId')
                    if deviceid is None:
                        message = 'Invalid Inform, DeviceID missing from request %s' % request
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    serial = deviceid.find('SerialNumber').text
                    if not serial:
                        message = 'Invalid Inform, SerialNumber missing from request %s' % request
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    vendor = deviceid.find('Manufacturer').text
                    if not vendor:
                        message = 'Invalid Inform, Manufacturer missing from request %s' % request
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    model = deviceid.find('ProductClass').text
                    if not model:
                        message = 'Invalid Inform, ProductClass missing from request %s' % request
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    oui = deviceid.find('OUI').text
                    if not oui:
                        message = 'Invalid Inform, OUI missing from request %s' % request
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    ### find or create acs devicevendor (using Manufacturer and OUI)
                    acs_devicevendor, created = AcsDeviceVendor.objects.get_or_create(
                        name = vendor,
                        oui = oui,
                    )

                    ### find or create acs devicetype (using ProductClass)
                    acs_devicemodel, created = AcsDeviceModel.objects.get_or_create(
                        vendor = acs_devicevendor,
                        name = model,
                    )

                    ### find or create acs device (using serial number and acs devicetype)
                    acs_device, created = AcsDevice.objects.get_or_create(
                        model = acs_devicemodel,
                        serial = serial
                    )

                    # save acs_device to acs_session
                    acs_session.acs_device = acs_device
                    acs_session.save()

                    # set imported=False to differentiate the acsdevices created in a migration from the ones created by an acs client (TODO: remove this bit of code in time)
                    if acs_device.imported:
                        acs_device.imported=False
                        acs_device.save()

                    # attempt acs device association
                    if not acs_device.get_related_device():
                        acs_device.associate_with_related_device()

                    if not acs_device.acs_xmpp_password:
                        acs_device.create_xmpp_user()

                    if not acs_device.acs_connectionrequest_password:
                        acs_device.create_connreq_password()

                    if not acs_session.get_inform_eventcodes(inform, acs_http_request):
                        # the event section is missing from this Inform
                        return HttpResponseBadRequest()

                    #########################################################
                    # refresh from db to make any changes above visible
                    acs_device.refresh_from_db()

                    # if this acs device is associated with a real device we can call that devices verify_acs_client_ip() method
                    # and possibly mark this acs session as client_ip_verified=True (which is required before we give out any secrets like ssid in the session)
                    if acs_device.get_related_device():
                        ### run acs pre-ip-verified session hook
                        acs_device.get_related_device().acs_session_pre_verify_hook()

                        # set acs_session.client_ip_verified based on the outcome of verify_acs_client_ip(acs_session.client_ip) 
                        acs_session.client_ip_verified = acs_device.get_related_device().verify_acs_client_ip(acs_session.client_ip)
                        message = "client_ip_verified set to %s after running acs_device.get_related_device().verify_acs_client_ip(%s)" % (acs_session.client_ip_verified, acs_session.client_ip)
                        acs_session.acs_log(message)
                        acs_session.save()

                        ### run acs post-ip-verified session hook
                        acs_device.get_related_device().acs_session_post_verify_hook()

                        # refresh from db to make any changes above visible
                        acs_device.refresh_from_db()

                    ##########################################################
                    ### this is a good place to check for different Inform EventCodes or use
                    ### other data from the Inform

                    # first we clean up any old unprocessed automatic jobs.
                    # these might be lingering from earlier sessions that may have failed (for any number of reasons)
                    deleted, info = acs_session.acs_device.acs_queue_jobs.filter(automatic=True, processed=False).delete()
                    if deleted:
                        acs_session.acs_log("Cleanup: Deleted %s old unprocessed automatic AcsQueueJobs for this device" % deleted)

                    ### get parameterlist from the Inform payload
                    parameterlist = inform.find('ParameterList')

                    ### update current_config_level from Device.ManagementServer.ParameterKey
                    parameterkey = get_value_from_parameterlist(parameterlist, acs_session.get_acs_parameter_name('django_acs.acs.parameterkey'))
                    if not parameterkey:
                        acs_device.current_config_level = None
                    else:
                        acs_device.current_config_level = parse_datetime(parameterkey)

                    ### update latest_inform time
                    acs_device.acs_latest_inform = timezone.now()

                    ### update current_software_version
                    acs_device.current_software_version = get_value_from_parameterlist(parameterlist, acs_session.get_acs_parameter_name('django_acs.deviceinfo.softwareversion'))

                    ### save acs device
                    acs_device.save()

                    ###############################################
                    ### This is where we do things we want do _after_ an Inform session.
                    ### Queue jobs here before sending InformResponse and they will be run in the same session.

                    # queue GetParameterNames, GetParameterValues, GetParameterAttributes
                    if not acs_session.collect_device_info("Collecting information triggered by Inform"):
                        # unable to queue neccesary job
                        return HttpResponseServerError()

                    ## Queue a firmware upgrade job?
                    if not acs_session.device_firmware_upgrade():
                        # we wanted to queue a firmware upgrade job, but failed
                        return HttpResponseServerError()

                    ###############################################
                    ### we are done processing the Inform RPC request, and ready to return the InformResponse, 
                    ### so add the outer response element
                    cwmp = etree.SubElement(body, nse('cwmp', 'InformResponse'))
                    ### add the inner response elements, without namespace (according to cwmp spec!)
                    maxenv = etree.SubElement(cwmp, 'MaxEnvelopes')
                    maxenv.text = '1'

                elif acs_http_request.cwmp_rpc_method == 'TransferComplete':
                    ### handle TransferComplete RPC call
                    cwmp = etree.SubElement(body, nse('cwmp', 'TransferCompleteResponse'))

                else:
                    message = 'Unimplemented cwmp method %s called by the client %s' % (acs_http_request.cwmp_rpc_method, acs_device)
                    acs_session.acs_log(message)
                    return HttpResponseBadRequest(message)

                #####################################################################################################
                ### we are done processing the http request, put HTTP response together
                output = etree.tostring(root, encoding='utf-8', xml_declaration=True)
                response = HttpResponse(output, content_type='text/xml; charset=utf-8')

                ### save the HTTP response
                acs_http_response = AcsHttpResponse.objects.create(
                    http_request=acs_http_request,
                    fk_body=create_xml_document(response.content),
                    cwmp_id=response_cwmp_id,
                    cwmp_rpc_method=response_cwmp_rpc_method,
                    rpc_response_to=acs_http_request,
                )
                acs_session.acs_log("responding to CPE %s with %s" % (acs_session.acs_device, response_cwmp_rpc_method))

            elif acs_http_request.cwmp_rpc_method[:-8] in settings.CWMP_CPE_VALID_RPC_METHODS:
                #####################################################################################################
                acs_session.acs_log('the CPE %s is responding to an RPC call from the ACS: %s' % (acs_session.acs_device, acs_http_request.cwmp_rpc_method))
                ### first link this http request to the related rpc request (which is in a http response),
                ### find it by looking for the same rpc method and cwmp id in http responses in this acs session
                match = False
                for httpresponse in acs_session.acs_http_responses:
                    if httpresponse.cwmp_rpc_method == acs_http_request.cwmp_rpc_method[:-8] and httpresponse.cwmp_id == acs_http_request.cwmp_id:
                        acs_http_request.rpc_response_to = httpresponse
                        acs_http_request.save()
                        match = True
                if not match:
                    message = 'Unable to find the HTTP response containing the RPC request being responded to :('
                    acs_session.acs_log(message)
                    return HttpResponseServerError(message)

                ### parse the cwmp object from the soap body
                rpcresponsexml = soap_body.find('cwmp:%s' % acs_http_request.cwmp_rpc_method, acs_session.soap_namespaces)

                if acs_http_request.cwmp_rpc_method == 'GetParameterNamesResponse':
                    ### do nothing for now, the response will be used when the GetParameterValuesResponse comes in later
                    pass

                elif acs_http_request.cwmp_rpc_method == 'GetParameterValuesResponse':
                    # nothing here for now
                    pass

                elif acs_http_request.cwmp_rpc_method == 'GetParameterAttributesResponse':
                    # this is a GetParameterAttributesResponse, attempt to update the device acs parameters
                    if acs_session.acs_device.update_acs_parameters(acs_http_request):
                        #################################################################################################
                        ### this is where we do things to and with the recently fetched acs parameters from the device,
                        ### like configuring the device or handling user config changes
                        ### Queue jobs here before sending GetParameterAttributesResponse and they will be run in the same session.

                        # extract device uptime from acs_device.acs_parameters and save it to acs_session.device_uptime
                        acs_session.update_device_uptime()

                        # check if we need to call the handle_user_config_changes() method on the acs_device,
                        # we only check for user changes if a device has been configured by us already, and doesn't need any more config at the moment
                        if acs_session.acs_device.current_config_level and acs_session.acs_device.current_config_level > acs_session.acs_device.get_desired_config_level():
                            # device is already configured, and doesn't need additional config from us right now, so check if the user changed anything on the device, and act accordingly
                            acs_session.acs_device.handle_user_config_changes()

                        # refresh to get any changes from above
                        acs_session.refresh_from_db()

                        # if this device has been reconfigured in this session we collect data again,
                        # if not, we reconfigure it if needed
                        if acs_session.configuration_done:
                            # device has been configured, so collect data again so we have the latest (unless we have already done so)
                            if not acs_session.post_configuration_collection_done:
                                if not acs_session.collect_device_info(reason="Device has been reconfigured"):
                                    acs_session.acs_log("Unable to queue one or more jobs to collect info after configuration")
                                    return HttpResponseServerError()
                        else:
                            # this device has not been configured in this ACS session. This is where we check if we need to configure it now.
                            # acs_session.configure_device returns False if there was a problem configuring the device, and true if
                            # the device was configured, or did not need to be configured
                            if not acs_session.configure_device():
                                # there was a problem creating configure jobs for the device
                                return HttpResponseServerError()

                elif acs_http_request.cwmp_rpc_method == 'GetRPCMethodsResponse':
                    pass

                elif acs_http_request.cwmp_rpc_method == 'SetParameterValuesResponse':
                    ### find status
                    status = rpcresponsexml.find('Status').text
                    if status != '0':
                        ### ACS client failed to apply all our settings, fuckery is afoot!
                        message = 'The ACS device %s failed to apply our SetParameterValues settings, something is wrong!' % acs_device
                        acs_session.acs_log(message)
                        return HttpResponseBadRequest(message)

                    ### find the parameterkey and update the acs_device so we know its current_config_level
                    ### since this is a SetParameterValuesResponse we will probably get settings.CWMP_CONFIG_INCOMPLETE_PARAMETERKEY_DATE here,
                    ### which is fine(tm)
                    parameterkey = acs_http_request.rpc_response_to.soap_body.find('cwmp:SetParameterValues', acs_session.soap_namespaces).find('ParameterKey').text
                    acs_session.acs_device.current_config_level = parse_datetime(parameterkey)

                elif acs_http_request.cwmp_rpc_method == 'SetParameterAttributesResponse':
                    ### find the parameterkey and update the acs_device so we know its current_config_level
                    parameterkey = acs_http_request.rpc_response_to.soap_body.find('cwmp:SetParameterAttributes', acs_session.soap_namespaces).find('ParameterKey').text
                    acs_session.acs_device.current_config_level = parse_datetime(parameterkey)
                    # in case we have a local desired_config_level on the acs device, unset it now as the configuration has been done
                    if acs_session.acs_device.desired_config_level:
                        acs_session.acs_device.desired_config_level = None
                    acs_session.acs_device.save()

                elif acs_http_request.cwmp_rpc_method == 'FactoryResetResponse':
                    empty_response=True

                ### we are done processing the clients response, do we have anything else?
                response = acs_http_request.get_response(empty_response=empty_response)
            else:
                #####################################################################################################
                ### TODO: insert some code to handle soapfault here so we dont hit the "Unknown cwmp object/method" bit below when a soapfault happens

                #####################################################################################################
                acs_session.acs_log('unknown cwmp object/method received from %s: %s' % (acs_session.acs_device, acs_http_request.cwmp_rpc_method))
                return HttpResponseBadRequest('unknown cwmp object/method received')

        else:
            # this http request has an empty body
            acs_session.acs_log('the CPE %s is done and posted an empty body to the ACS' % acs_session.acs_device)
            ### get a response for the client - if we have nothing queued it will be an empty response
            response = acs_http_request.get_response()

        ### all done, update the acs session with result before returning response
        acs_session.update_session_result()

        ### set the acs session cookie
        # we have to set this cookie manually because some stupid ACS client cannot parse expires in a http cookie
        # and Django always sets exipires in cookies, no even it the expires argument is set to None,
        # to be compatible with old IE clients yay
        #response.set_cookie(key='acs_session_id', value=max_age=60, expires=None, path='/')
        response['Set-Cookie'] = "acs_session_id=%s; Max-Age=60; Path=/" % hexid
        return response

