# django-acs
Django ACS Server

NOTE: THIS IS VERY MUCH A WORK IN PROGRESS. EXPECT NOTHING TO WORK UNTIL I GET SOME MORE STUFF DONE.


## XML Storage Model
django-acs saves the full history of the ACS sessions. For this purpose it needs a model for XML storage. You need to create this model, and a manager.

The XML Storage Model must have a property called "document" which returns the XML as a string. It must also have a manager with a .create_xml_document() method. This method should accept a single argument named xml, which is the bytes representing the XML, and it must return an instance of the configured XML Storage Model.

For example:

    class XMLDocumentManager(models.Manager):
        """
        A custom manager with the required create_xml_document() method
        """
        def create_xml_document(self, xml):
            f = io.BytesIO()
            f.write(xml)
            xmlfile = File(f)
            xmldoc = self.model.objects.create()
            xmldoc.file_document.save("%s.xml" % str(xmldoc.uuid), xmlfile)
            return xmldoc

    class XMLDocument(models.Model):
        """
        The XMLDocument model saves XML files to disk and keeps only a reference to the filename in the database.
        """
        objects = XMLDocumentManager()
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


You can start out with just a TextField to save the XML, but for any type of large scale operation you should use the filesystem or an object store which can handle millions of files.


Finally configure django-acs to use the class like so:

    DJANGO_ACS={
        'xml_storage_model': 'xmlarchive.XMLDocument'
    }


# Settings
An alphabetical list of all supported settings.

## inform_interval (optional)
The inform interval to configure for ACS devices, in seconds.

Default: 3600

## inform_limit_per_interval (optional)
The maximum number of Informs (ACS sessions really) we allow a single ACS device to do in the span of a single informinterval. Any more sessions will be rejected with HTTP 420.

Default: 2

## xml_storage_model (required)
Sets the model used to store XML documents. See the section XML Storage Model above.

No default.

