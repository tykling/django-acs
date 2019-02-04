import io, paramiko, re
from radius.models import Radacct

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

