# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from zope.interface import Interface
from zope.interface import Attribute


class IPresenceQR(Interface):
    """ An adapter that handles meeting presence through QR-reader.
    """

    secret = Attribute('JWT secret for this meeting')

    def decode(jwt_string):
        """ Decode a JSON Web Token into a python object (dict) """

    def encode(payload):
        """ Encode a python object (dict) into a JSON Web Token """
