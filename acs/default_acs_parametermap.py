# This dict contains the default mapping between the internal django-acs representation of attributes,
# and the actual name of the parameter in the xml tree.

default_acs_device_parametermap = {
    # acs server stuff
    "django_acs.acs.informinterval": "ManagementServer.PeriodicInformInterval",
    "django_acs.acs.acs_managed_upgrades": "ManagementServer.UpgradesManaged",
    "django_acs.acs.connection_request_user": "ManagementServer.ConnectionRequestUsername",
    "django_acs.acs.connection_request_password": "ManagementServer.ConnectionRequestPassword",
    "django_acs.acs.parameterkey": "ManagementServer.ParameterKey",
    "django_acs.acs.connrequrl": "ManagementServer.ConnectionRequestURL",

    # acs server xmpp stuff
    "django_acs.acs.xmpp_server": "XMPP.Connection.1.Server.1.ServerAddress",
    "django_acs.acs.xmpp_server_port": "XMPP.Connection.1.Server.1.Port",
    "django_acs.acs.xmpp_connection_enable": "XMPP.Connection.1.Enable",
    "django_acs.acs.xmpp_connection_username": "XMPP.Connection.1.Username",
    "django_acs.acs.xmpp_connection_password": "XMPP.Connection.1.Password",
    "django_acs.acs.xmpp_connection_domain": "XMPP.Connection.1.Domain",
    "django_acs.acs.xmpp_connection_usetls": "XMPP.Connection.1.UseTLS",
    "django_acs.acs.xmpp_connreq_connection": "ManagementServer.ConnReqXMPPConnection",

    # device info
    "django_acs.deviceinfo.softwareversion": "DeviceInfo.SoftwareVersion",
    "django_acs.deviceinfo.uptime": "DeviceInfo.UpTime",

    # wifi 2.4g
    "django_acs.wifi.bg_ssid": "WiFi.SSID.1.SSID",
    "django_acs.wifi.bg_wpapsk": "WiFi.AccessPoint.1.Security.KeyPassphrase",
    "django_acs.wifi.bg_autochannel": "WiFi.Radio.1.AutoChannelEnable",
    "django_acs.wifi.bg_channel": "WiFi.Radio.1.Channel",

    # wifi 5g
    "django_acs.wifi.n_ssid": "WiFi.SSID.5.SSID",
    "django_acs.wifi.n_wpapsk": "WiFi.AccessPoint.5.Security.KeyPassphrase",
    "django_acs.wifi.n_autochannel": "WiFi.Radio.2.AutoChannelEnable",
    "django_acs.wifi.n_channel": "WiFi.Radio.2.Channel",
}

