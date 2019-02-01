from django.core.management.base import BaseCommand
from django.conf import settings
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
import logging


class Command(BaseCommand):
    args = 'none'
    help = 'Connects to XMPP server and sends/receives messages'

    def handle(self, *args, **options):
        ### Initiate logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')

        ### create AcsXmppBot instance
        xmpp = AcsXmppBot(settings.ACS_XMPP_JABBERID, settings.ACS_XMPP_PASSWORD)
        xmpp.connect(address=settings.ACS_XMPP_SERVERTUPLE)
        xmpp.process(block=True)


class AcsXmppBot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            msg.reply("Thanks for sending\n%(body)s" % msg).send()

