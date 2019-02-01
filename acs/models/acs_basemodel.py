from django.db import models

class AcsBaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, db_index=True)
    modified_date = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def tag(self):
        return "%s#%s" % (self.__class__.__name__, self.pk)

