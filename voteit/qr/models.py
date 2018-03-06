# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import string
from json import dumps
from logging import getLogger

import jwt
import qrcode
from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from arche.utils import utcnow
from datetime import timedelta
from persistent.list import PersistentList
from pyramid.threadlocal import get_current_request
from qrcode.image.svg import SvgPathImage
from six import StringIO
from six import string_types
from voteit.core.models.interfaces import IMeeting
from voteit.irl.models.interfaces import IParticipantNumbers
from zope.component import adapter
from zope.interface import implementer

from voteit.qr.events import ParticipantCheckIn
from voteit.qr.events import ParticipantCheckOut
from voteit.qr.interfaces import IPresenceQR
from voteit.qr.interfaces import IPresenceEventLog
from voteit.qr.interfaces import IPresenceEvent
from voteit.qr.interfaces import IParticipantCheckIn
from voteit.qr.interfaces import IParticipantCheckOut

logger = getLogger(__name__)


@implementer(IPresenceQR)
@adapter(IMeeting)
class PresenceQR(object):
    """ See .interfaces.IPresenceQR """

    def __init__(self, context):
        self.context = context

    def _generate_random_secret(self, length=20):
        # type: (int) -> unicode
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for x in range(length))

    @property
    def active(self):
        return bool(self.secret)
    @active.setter
    def active(self, value):
       if value and self.secret is None:
           self.secret = self._generate_random_secret()
       if not value and self.secret is not None:
           del self.secret

    @property
    def userids(self):
        try:
            return self.context._qr_presence_users
        except AttributeError:
            self.context._qr_presence_users = OOSet()
            return self.context._qr_presence_users

    @property
    def settings(self):
        try:
            return self.context._qr_presence_settings
        except AttributeError:
            self.context._qr_presence_settings = OOBTree()
            return self.context._qr_presence_settings
    @settings.setter
    def settings(self, value):
        if dict(value) != dict(self.settings):
            self.context._qr_presence_settings.clear()
            self.context._qr_presence_settings.update(value)

    @property
    def secret(self):
        # type: () -> unicode or None
        return getattr(self.context, '_qr_presence_secret', None)
    @secret.setter
    def secret(self, value):
        self.context._qr_presence_secret = value
    @secret.deleter
    def secret(self):
        self.context._qr_presence_secret = None

    def checkin(self, userid, request=None, event=True):
        """ Checkin user, returns userid or None if user was already checked in."""
        if userid not in self.userids:
            logger.debug('%r checked in @ %r', userid, self.context.__name__)
            self.userids.add(userid)
            if event:
                if not request:
                    request = get_current_request()
                request.registry.notify(ParticipantCheckIn(userid, self.context))
            return userid
        else:
            logger.debug('%r already checked in @ %r', userid, self.context.__name__)

    def checkout(self, userid, request=None, event=True):
        """ Checkout user, returns userid or None if user was already checked out."""
        if userid in self.userids:
            logger.debug('%r checked out @ %r', userid, self.context.__name__)
            self.userids.remove(userid)
            if event:
                if not request:
                    request = get_current_request()
                request.registry.notify(ParticipantCheckOut(userid, self.context))
            return userid
        else:
            logger.debug('%r is not present @ %r', userid, self.context.__name__)

    def make_svg(self, payload, is_secret=True):
        # type: (dict) -> unicode
        if is_secret:
            payload_str = self.encode(payload)
        else:
            payload_str = dumps(payload)
        output = StringIO()
        qrcode.make(payload_str, image_factory=SvgPathImage).save(output)
        return output.getvalue()

    def decode(self, encoded):
        # type: (unicode) -> dict
        return jwt.decode(encoded, self.secret)

    def encode(self, payload):
        # type: (dict) -> unicode
        assert isinstance(self.secret, string_types)
        return jwt.encode(payload, self.secret)

    def __contains__(self, userid):
        #Basically if someone has checked in
        return userid in self.userids

    def __iter__(self):
        return iter(self.userids)

    def __len__(self):
        return len(self.userids)


@implementer(IPresenceEventLog)
@adapter(IMeeting)
class PresenceEventLog(object):

    def __init__(self, context):
        self.context = context

    @property
    def data(self):
        try:
            return self.context._qr_presence_log
        except AttributeError:
            self.context._qr_presence_log = OOBTree()
            return self.context._qr_presence_log

    def add(self, userid, event_name):
        # It shouldn't be possible to the same event several times,
        # so we don't need to check for that
        if userid not in self:
            self[userid] = PersistentList()
        if event_name == 'checkin':
            self[userid].append({'in': utcnow()})
        elif event_name == 'checkout':
            try:
                self[userid][-1]['in']
            except (KeyError, IndexError):
                # in case logging was added while users where checked in, they won't exist
                return
            self[userid][-1]['out'] = utcnow()
        else: # pragma: no coverage
            raise ValueError("Wrong event name")

    def total(self, userid):
        """ Check total time, returns timedelta. """
        if userid not in self:
            return None
        total = timedelta()
        for item in self.get(userid, ()):
            checkin = item['in']
            checkout = item.get('out', utcnow())
            total += checkout - checkin
        return total

    def first_entry(self, userid):
        if userid in self:
            return self[userid][0]['in']

    def last_exit(self, userid):
        if userid in self:
            try:
                return self[userid][-1]['out']
            except KeyError:
                pass

    def get(self, userid, default=None):
        if userid in self:
            return self[userid]
        return default

    def __setitem__(self, userid, value):
        assert isinstance(value, PersistentList)
        self.data[userid] = value

    def __getitem__(self, userid):
        return self.data[userid]

    def __contains__(self, userid):
        return userid in self.data

    def __iter__(self):
        return iter(self.data.keys())


def register_presence_event(event):
    """ Register events if that's switched on for this meeting. """
    meeting = event.meeting
    pqr = IPresenceQR(meeting)
    if not pqr.settings.get('log_time', None):
        return
    if IParticipantCheckOut.providedBy(event):
        event_name = 'checkout'
    elif IParticipantCheckIn.providedBy(event):
        event_name = 'checkin'
    else:
        raise TypeError("Subscriber caught wrong event")
    log = IPresenceEventLog(meeting)
    log.add(event.userid, event_name)


def assign_pn_if_user_lacks_one(event):
    meeting = event.meeting
    pqr = IPresenceQR(meeting)
    if not pqr.settings.get('assign_pn', None):
        return
    pns = IParticipantNumbers(meeting)
    if event.userid not in pns.userid_to_number:
        pn = pns.next_free()
        pns.new_tickets(event.userid, pn)
        pns.claim_ticket(event.userid, pns.tickets[pn].token)


def includeme(config):
    config.registry.registerAdapter(PresenceQR)
    config.registry.registerAdapter(PresenceEventLog)
    config.add_subscriber(register_presence_event, IPresenceEvent)
    config.add_subscriber(assign_pn_if_user_lacks_one, IParticipantCheckIn)
