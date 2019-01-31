# django-acs
Django ACS Server

# Settings

## XML storage
django-acs needs a model for XML storage. Configure the class like so:

`
DJANGO_ACS={
    'xml_storage_model': 'xmlarchive.XMLDocument'
}
`

The specified model must have a property called "document" which returns the XML as a string, for example:

`
class XMLDocument(models.Model):
    """
    The XMLDocument model saves XML files to disk and keeps only a reference to the filename in the database.
    """
    xml_document = models.FileField(
        upload_to='xmlarchive/',
        null=True,
        blank=True,
        help_text='The XML Document FileField'
    )

    @cached_property
    def document(self):
        if self.file_document:
            try:
                return self.xml_document.read().decode('utf-8')
            except Exception as E:
                logger.info("got exception while reading XML file %s: %s" % (self.xml_document.path, E))
        # no file or error reading
        return None
`

You can start out with just a TextField to save the XML, but for any type of large scale operation use the filesystem or an object store which can handle millions of files.

