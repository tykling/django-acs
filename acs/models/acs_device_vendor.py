
from django.db import models
from django.urls import reverse
from mrxcore.models import BaseModel


class AcsDeviceVendor(BaseModel):
    name = models.CharField(max_length=100)
    oui = models.CharField(max_length=6)

    def __str__(self):
        return str('%s - %s' % (self.tag, self.name))

    def get_absolute_url(self):
        return reverse('acsdevicevendor_detail', kwargs={'pk': self.pk})

