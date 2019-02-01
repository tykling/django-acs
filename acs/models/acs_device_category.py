from acs.models import AcsBaseModel
from django.db import models
from django.urls import reverse


class AcsDeviceCategory(AcsBaseModel):
    """ The category of an ACS device model. Used to determine what to do with the device. """
    WIFI = "WIFI"
    SETTOPBOX = "SETTOPBOX"
    UNKNOWN = "UNKNOWN"

    CATEGORY_CHOICES = (
        (UNKNOWN, 'Unknown'),
        (WIFI, 'Wifi Device'),
        (SETTOPBOX, 'Settop Box')
    )

    name = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default=UNKNOWN, unique=True)

    def __str__(self):
        return str("%s - %s" % (self.tag, self.name))

    def get_absolute_url(self):
        return reverse('acsdevicecategory_detail', kwargs={'pk': self.pk})


