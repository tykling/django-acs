import io, paramiko, re

from django.conf import settings
from django.apps import apps

from radius.models import Radacct
from .default_settings import django_acs_default_settings


def create_xml_document(xml):
    """
    Takes some bytes representing an XML document and returns an instance
    of the configured XML storage model.
    """
    return get_xml_storage_model().objects.create_xml_document(xml=xml)


def get_xml_storage_model():
    """
    Return the configured xml storage model class using apps.get_model()
    """
    app, model = settings.DJANGO_ACS['xml_storage_model'].split(".")
    return apps.get_model(
        app_label=app,
        model_name=model
    )


def get_django_acs_setting(setting):
    """
    A convenience method for getting DJANGO_ACS settings.
    Falls back to defaults for undefined settings.
    """
    if not hasattr(settings, "DJANGO_ACS"):
        return False

    if setting in settings.DJANGO_ACS:
        # return user setting
        return settings.DJANGO_ACS[setting]
    else:
        # return our default
        return django_acs_default_settings[setting]


def get_value_from_parameterlist(parameterlist, key):
    '''
      Uses lxml.etree xpath to extract the text inside a Value element,
      given the 'lookup key' inside the Name element, and the following XML structure:
      <ParameterList xsi:type="SOAP-ENC:Array" SOAP-ENC:arrayType="cwmp:ParameterValueStruct[9]">
        <ParameterValueStruct>
          <Name>Device.DeviceInfo.HardwareVersion</Name>
          <Value xsi:type="xsd:string">TW_0.7</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>Device.DeviceInfo.SoftwareVersion</Name>
          <Value xsi:type="xsd:string">1.23.4.6.2969</Value>
        </ParameterValueStruct>
        <ParameterValueStruct>
          <Name>Device.DeviceInfo.ProvisioningCode</Name>
          <Value xsi:type="xsd:string"/>
        </ParameterValueStruct>
      </ParameterList>
    '''
    elementlist = parameterlist.xpath('.//Name[text()="%s"]/following-sibling::Value' % key)
    if elementlist:
        element = elementlist[0]
    else:
        return False

    # return int() for integers
    if element.attrib['{http://www.w3.org/2001/XMLSchema-instance}type'] == 'xsd:unsignedInt':
        return int(element.text)
    else:
        return element.text


def run_ssh_command(server, username, private_key, command):
    try:
        private_key_file = io.StringIO(private_key)
        private_key = paramiko.RSAKey.from_private_key(private_key_file)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=username, pkey=private_key, timeout=15)
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        ssh.close()
    except Exception as E:
        return {
            'result': False,
            'exception': E,
        }

    return {
        'result': True,
        'output': stdout.readlines(),
        'errorlines': stderr.readlines(),
        'exit_status': exit_status,
    }

def get_datamodel_from_devicesummary(summary):
    """
    Regex to return "Device:1.0" from "Device:1.0[](Baseline:1), ABCService:1.0[1](Baseline:1), XYZService:1.0[1](Baseline:1)"
    """
    match = re.search('(.*:\d.\d)\[\]', summary)
    if match:
        return match.group(1)
    else:
        return False

