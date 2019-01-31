
from django.db import models
from django.urls import reverse
from mrxcore.models import BaseModel
from django.contrib.postgres.fields import JSONField
from django.conf import settings


class AcsDeviceModel(BaseModel):
    vendor = models.ForeignKey('acs.AcsDeviceVendor', related_name='acsdevicemodels', on_delete=models.PROTECT)
    category = models.ForeignKey('acs.AcsDeviceCategory', related_name='acsdevicemodels', default=1, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)
    desired_config_level = models.DateTimeField(null=True, blank=True)
    desired_software_version = models.CharField(max_length=50, blank=True)
    acs_parameter_map_overrides = JSONField(null=True, blank=True)

    def __str__(self):
        return str("%s - %s" % (self.tag, self.name))

    def get_absolute_url(self):
        return reverse('acsdevicemodel_detail', kwargs={'pk': self.pk})

    @property
    def acs_parameter_map(self):
        # return the default acs_parameter_map with overrides for this device
        parametermap = settings.DEFAULT_ACS_DEVICE_PARAMETER_MAP
        if self.acs_parameter_map_overrides:
            parametermap.update(self.acs_parameter_map_overrides)
        return parametermap

    def get_active_notification_parameterlist(self, root_object):
        """
        Return the list of parameters which needs active notifications,
        based on the category of devicemodel
        """
        parameterlist = []
        if self.category.name == "WIFI":
            #This acs device category needs notifications for the whole Wifi tree
            parameterlist.append("%s.Wifi." % root_object)
        return parameterlist

