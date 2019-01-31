
from django.db import models
from django.urls import reverse
from mrxcore.models import BaseModel


class AcsDeviceCategory(BaseModel):
    """ The category of an ACS device model. Used to determine what to do with the device. """
    WIFI = "WIFI"
    SETTOPBOX = "SETTOPBOX"
    UNKNOWN = "UNKNOWN"

    CATEGORY_CHOICES = (
        (UNKNOWN, 'Unknown'),
        (WIFI, 'Wifi Device'),
        (SETTOPBOX, 'Settop Box')
    )

    name = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default=UNKNOWN)

    class Meta:
        ### make sure the category name is unique
        unique_together = ('name', 'active')

    def __str__(self):
        return str("%s - %s" % (self.tag, self.name))

    def get_absolute_url(self):
        return reverse('acsdevicecategory_detail', kwargs={'pk': self.pk})

