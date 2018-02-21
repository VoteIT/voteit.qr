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
from pyramid.threadlocal import get_current_request
from qrcode.image.svg import SvgPathImage
from six import StringIO
from six import string_types
from voteit.core.models.interfaces import IMeeting
from zope.component import adapter
from zope.interface import implementer

from voteit.qr.events import ParticipantCheckIn
from voteit.qr.events import ParticipantCheckOut
from voteit.qr.interfaces import IPresenceQR


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


def includeme(config):
    config.registry.registerAdapter(PresenceQR)
