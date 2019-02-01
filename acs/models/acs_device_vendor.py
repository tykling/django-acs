from acs.models import AcsBaseModel
from django.urls import reverse


class AcsDeviceVendor(AcsBaseModel):
    name = models.CharField(max_length=100)
    oui = models.CharField(max_length=6)

    def __str__(self):
        return str('%s - %s' % (self.tag, self.name))

    def get_absolute_url(self):
        return reverse('acsdevicevendor_detail', kwargs={'pk': self.pk})

