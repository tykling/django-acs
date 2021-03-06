from acs.models import AcsBaseModel
from django.db import models


class CwmpDataModel(AcsBaseModel):
    name = models.TextField()
    xml_filename = models.TextField(blank=True)
    html_link = models.TextField(blank=True)

    def __str__(self):
        return str("%s - %s - %s" % (self.tag, self.name, self.xml_filename))

    @property
    def root_object(self):
        """
        Return "Device" from "Device:2.11"
        """
        return self.name.split(":")[0]

