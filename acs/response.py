from lxml import etree
import logging

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned

logger = logging.getLogger('mrx.%s' % __name__)


def add_parameter_names(soapobject, parameterlist):
    ### add empty ParameterNames element
    paramnames = etree.SubElement(soapobject, 'ParameterNames')
    for parameter in parameterlist:
        param = etree.SubElement(paramnames, 'string')
        param.text = parameter

    ### finally add the total number of elements
    paramnames.set(nse('soap-enc', 'arrayType'), "xsd:string[%s]" % len(parameterlist))


def get_soap_xml_object(cwmp_rpc_method, datadict=None, update_parameterkey=False):
    ### first get the outer soap object
    soapobject = etree.Element(nse('cwmp', cwmp_rpc_method))

    ### determine what method we are working with
    cwmp_rpc_method = str(cwmp_rpc_method)
    if cwmp_rpc_method=='GetRPCMethods':
        ### nothing else to add for this call
        pass

    elif cwmp_rpc_method=='SetParameterValues':
        if not datadict:
            logger.error('datadict needed for SetParameterValues')
            return False
        paramlist = etree.SubElement(soapobject, 'ParameterList')
        for key, value in datadict.items():
            add_pvs(element=paramlist, key=key, value=value)
        paramlist.set(nse('soap-enc', 'arrayType'), "cwmp:ParameterValueStruct[%s]" % len(paramlist))
        paramkey = etree.SubElement(soapobject, 'ParameterKey')
        if update_parameterkey:
            paramkey.text = str(timezone.now())
        else:
            paramkey.text = str(settings.CWMP_CONFIG_INCOMPLETE_PARAMETERKEY_DATE)

    elif cwmp_rpc_method=='GetParameterValues':
        if not datadict:
            logger.error('datadict needed for GetParameterValues')
            return False

        ### add ParameterNames
        add_parameter_names(soapobject, datadict['parameterlist'])

    elif cwmp_rpc_method=='GetParameterNames':
        if not datadict:
            datadict = {
                'parampath': '',
                'nextlevel': '0'
            }
        ### add the inner response elements, but without XML namespace (according to cwmp spec!)
        parampath = etree.SubElement(soapobject, 'ParameterPath')
        parampath.text = datadict['parampath']
        nextlevel = etree.SubElement(soapobject, 'NextLevel')
        nextlevel.text = datadict['nextlevel']

    elif cwmp_rpc_method=='GetParameterAttributes':
        if not datadict:
            logger.error('datadict needed for GetParameterAttributes, returning False')
            return False

        ### add ParameterNames
        add_parameter_names(soapobject, datadict['parameterlist'])

    elif cwmp_rpc_method=='SetParameterAttributes':
        if not datadict:
            logger.error('datadict needed for SetParameterValues, returning False')
            return False
        paramlist = etree.SubElement(soapobject, 'ParameterList')
        for name, value in datadict.items():
            add_pas(element=paramlist, name=name, value=value)
        paramlist.set(nse('soap-enc', 'arrayType'), "cwmp:SetParameterAttributeStruct[%s]" % len(paramlist))
        paramkey = etree.SubElement(soapobject, 'ParameterKey')
        if update_parameterkey:
            paramkey.text = str(timezone.now())
        else:
            paramkey.text = str(settings.CWMP_CONFIG_INCOMPLETE_PARAMETERKEY_DATE)

    elif cwmp_rpc_method=='AddObject':
        if not datadict:
            logger.error('datadict needed for AddObject, returning False')
            return False
        objname = etree.SubElement(soapobject, 'ObjectName')
        objname.text = datadict['objectname']
        paramkey = etree.SubElement(soapobject, 'ParameterKey')
        if update_parameterkey:
            paramkey.text = str(timezone.now())
        else:
            paramkey.text = str(settings.CWMP_CONFIG_INCOMPLETE_PARAMETERKEY_DATE)

    elif cwmp_rpc_method=='DeleteObject':
        if not datadict:
            logger.error('datadict needed for DeleteObject, returning False')
            return False
        objname = etree.SubElement(soapobject, 'ObjectName')
        objname.text = datadict['objectname']
        paramkey = etree.SubElement(soapobject, 'ParameterKey')
        if update_parameterkey:
            paramkey.text = str(timezone.now())
        else:
            paramkey.text = str(settings.CWMP_CONFIG_INCOMPLETE_PARAMETERKEY_DATE)

    elif cwmp_rpc_method=='Reboot':
        ### nothing else to add for this call
        pass

    elif cwmp_rpc_method=='Download':
        if not datadict:
            logger.error('datadict needed for Download, returning False')
            return False
        filetype = etree.SubElement(soapobject, 'FileType')
        filetype.text = "1 Firmware Upgrade Image"
        url = etree.SubElement(soapobject, 'URL')
        url.text = datadict['url']

    elif cwmp_rpc_method=='Upload':
        logger.error("Unimplemented")
        return False

    elif cwmp_rpc_method=='FactoryReset':
        ### nothing else to add for this call
        pass

    elif cwmp_rpc_method=='ScheduleInform':
        logger.error("Unimplemented")
        return False

    else:
        ### unsupported for now
        logger.error('unsupported xml object: %s - returning False' % cwmp_rpc_method)
        return False

    ### return a string representation of the XML
    return etree.tostring(soapobject, encoding='utf-8', xml_declaration=True)


def get_soap_envelope(cwmp_id, acs_session):
    '''
    Returns an lxml.etree element representing an empty soap XML envelopes
    Returns both root and body (for convenience).
    '''
    ### begin SOAP envelope
    root = etree.Element(nse('soap-env', 'Envelope'), nsmap=acs_session.soap_namespaces)

    ### add SOAP Header
    header = etree.SubElement(root, nse('soap-env', 'Header'))

    ### add cwmp id to Header
    cwmpid = etree.SubElement(header, nse('cwmp', 'ID'))
    cwmpid.set(nse('soap-env', 'mustUnderstand'), "1")
    cwmpid.text = cwmp_id

    ### add SOAP Body
    body = etree.SubElement(root, nse('soap-env', 'Body'))

    ### return
    return root, body


def nse(namespace, element):
    '''
    Return a namespaced element based on the settings.SOAP_NAMESPACES
    '''
    if namespace=='cwmp' and namespace not in settings.SOAP_NAMESPACES:
        # default to cwmp1.0 if we have no session to decide from
        return '{urn:dslforum-org:cwmp-1-0}%s' % element
    return '{%s}%s' % (settings.SOAP_NAMESPACES[namespace], element)


def add_pvs(element, key, value):
    '''
    Given an etree Element, a key, and a value;
    add_pvs() will add a cwmp:ParameterValueStruct (without the namespace)
    containing a Name and a Value element. Only supports int bool and str/unicode for now.
    '''
    struct = etree.SubElement(element, 'ParameterValueStruct')
    nameobj = etree.SubElement(struct, 'Name')
    nameobj.text = key
    valueobj = etree.SubElement(struct, 'Value')

    if isinstance(value, bool):
        valueobj.set(nse('xsi', 'type'), "xsd:boolean")
        valueobj.text = "true" if value else "false"
    elif isinstance(value, int):
        valueobj.set(nse('xsi', 'type'), "xsd:unsignedInt")
        valueobj.text = str(value)
    elif isinstance(value, str) or isinstance(value, str):
        valueobj.set(nse('xsi', 'type'), "xsd:string")
        valueobj.text = value

def add_pas(element, name, value):
    '''
    Given an etree Element, a name and a value;
    add_pas() will add a cwmp:SetParameterAttributeStruct (without the namespace, according to spec)
    containing a Name and Notification and a few more elements.
    '''
    struct = etree.SubElement(element, 'SetParameterAttributeStruct')
    # Name element
    nameobj = etree.SubElement(struct, 'Name')
    nameobj.text = name

    # Notification element
    notifobj = etree.SubElement(struct, 'Notification')
    #notifobj.set(nse('xsi', 'type'), "xsd:unsignedInt")
    notifobj.text = str(value)

    # NotificationChange element
    notifchobj = etree.SubElement(struct, 'NotificationChange')
    #notifchobj.set(nse('xsi', 'type'), "xsd:boolean")
    notifchobj.text = "true"

    # AccessListChange element
    notifchobj = etree.SubElement(struct, 'AccessListChange')
    #notifchobj.set(nse('xsi', 'type'), "xsd:boolean")
    notifchobj.text = "false"

    # AccessList element
    notifchobj = etree.SubElement(struct, 'AccessList')
    notifchobj.set(nse('soap-enc', 'arrayType'), "xsd:string[0]")

