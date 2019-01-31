from django.core.management.base import BaseCommand
from django.utils import timezone
from time import sleep
from acs.models import AcsQueueJob
import sys, sleekxmpp
from django.conf import settings
import logging

logger = logging.getLogger('mrx.%s' % __name__)

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

class Command(BaseCommand):
    args = 'none'
    help = 'Loop through unprocessed AcsQueueJob entries marked urgent and do an XMPP ConnectionRequest for each'

    def __init__(self):
        self.xmpp = sleekxmpp.ClientXMPP(settings.ACS_XMPP_JABBERID, settings.ACS_XMPP_PASSWORD)
        self.xmpp.add_event_handler('session_start', self.xmpp_init)

    def xmpp_init(self, event):
        self.xmpp.send_presence()
        self.xmpp.get_roster()

    def handle(self, *args, **options):
        if self.xmpp.connect():
            xmpp.schedule('Run pending XMPP ConnectionRequests', 5, check_for_messages, repeat=True) 
            logger.info('-----------------------------')
            logger.info(str(timezone.localtime(timezone.now())))
            logger.info('Entering main xmpp loop...')
            xmpp.process(block=True)

    def check_for_messages(self):
        logger.info('-----------------------------')
        logger.info(str(timezone.localtime(timezone.now())))
        logger.info('Checking for pending XMPP ConnectionRequests...')

