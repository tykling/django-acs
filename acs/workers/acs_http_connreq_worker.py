import logging

from django.utils import timezone
from acs.models import AcsQueueJob

logger = logging.getLogger('mrx.%s' % __name__)

def do_work():
    """
    The acs_http_connreq_worker loops through unprocessed AcsQueueJob entries marked as urgent and does a HTTP ConnectionRequest for each unique ACS device found
    """
    for aqj in AcsQueueJob.objects.filter(urgent=True, processed=False, notification_sent=False).order_by('acs_device', 'created_date').distinct('acs_device'):
        logger.info('Processing HTTP connectionrequest for acs device %s (because job %s is urgent)' % (aqj.acs_device, aqj.tag))

        # do the http connection request
        r = aqj.acs_device.acs_http_connection_request()
        if not r:
            logger.info('Unable to send HTTP connectionrequest for acs device %s (job %s is urgent)' % (aqj.acs_device, aqj.tag))
        else:
            logger.info('Called ACS ConnectionRequest url for acs device %s because job %s is urgent: result HTTP %s' % (aqj.wifidevice, aqj.tag, r.status_code))
            # all good, update and save aqj
            aqj.notification_sent=True
            aqj.save()

