import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger('django_acs.%s' % __name__)


class AcsSettingsBuilder:
    """
    All django-acs settings are used through this module.

    Usage:

    from django_acs.conf import acs_settings
    print(acs_settings.INFORM_INTERVAL)
    """
    def __init__(self, *args, **kwargs):
        """
        Populate our acs_settings module
        """
        if not hasattr(settings, "DJANGO_ACS"):
            raise ImproperlyConfigured("DJANGO_ACS not found in settings.py")

        # First get all settings from the normal django settings.py
        for setting in settings.DJANGO_ACS:
            setattr(self, setting, settings.DJANGO_ACS[setting])

        # Then get whatever we are missing from default_acs_settings
        for setting in dir(AcsDefaultSettings):
            if setting not in dir(self):
                setattr(self, setting, getattr(AcsDefaultSettings, setting))

        # finally check if all the required settings are there
        if not hasattr(self, 'XML_STORAGE_MODEL'):
            raise ImproperlyConfigured("settings.DJANGO_ACS['XML_STORAGE_MODEL'] was not found. It is a required setting for django-acs. Bailing out.")


class AcsDefaultSettings:
    """
    Default settings for django-acs. Do not change anything here,
    set eg. DJANGO_ACS['INFORM_INTERVAL'] in settings.py instead.
    """
    INFORM_LIMIT_PER_INTERVAL = 2
    INFORM_INTERVAL = 3600
    CWMP_NAMESPACES = [
        'urn:dslforum-org:cwmp-1-0',
        'urn:dslforum-org:cwmp-1-1',
        'urn:dslforum-org:cwmp-1-2',
        'urn:dslforum-org:cwmp-1-3',
        'urn:dslforum-org:cwmp-1-4',
    ]

# initiate our settings object
acs_settings = AcsSettingsBuilder()

