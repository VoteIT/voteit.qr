# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import string
from UserDict import IterableUserDict
from persistent import Persistent
from uuid import uuid4

import jwt
from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from pyramid.threadlocal import get_current_request
from qrcode.image.svg import SvgPathImage

from voteit.core.models.interfaces import IMeeting
from voteit.irl.models.elegible_voters_method import ElegibleVotersMethod
from voteit.irl.models.interfaces import IMeetingPresence
from zope.component import adapter
from zope.interface import implementer

from voteit.qr import _
from voteit.qr.interfaces import IPresenceQR

@implementer(IPresenceQR)
@adapter(IMeeting)
class PresenceQR(object):
    """ See .interfaces.IPresenceQR """

    def __init__(self, context):
        self.context = context
        if not hasattr(context, '__presence_qr__'):
            context.__presence_qr__ = OOBTree()
            context.__presence_qr__['secret'] = self.generate_random_secret()

    def generate_random_secret(self, length=40):
        # type: (int) -> unicode
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    @property
    def secret(self):
        # type: () -> unicode
        return self.context.__presence_qr__['secret']

    @property
    def svg_factory(self):
        return SvgPathImage

    def decode(self, encoded):
        # type: (unicode) -> dict
        return jwt.decode(encoded, self.secret)

    def encode(self, payload):
        # type: (dict) -> unicode
        return jwt.encode(payload, self.secret)


def includeme(config):
    config.registry.registerAdapter(PresenceQR)
