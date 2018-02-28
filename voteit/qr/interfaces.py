# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from zope.interface import Interface
from zope.interface import Attribute


class IPresenceQR(Interface):
    """ An adapter that handles meeting presence through QR-reader.
    """
    active = Attribute("Is this plugin active?")
    secret = Attribute("JWT secret for this meeting")
    userids = Attribute("A persistent set with all present userids")
    settings = Attribute("Persistent settings.")

    def checkin(userid, request=None, event=True):
        """Checkin user"""

    def checkout(userid, request=None, event=True):
        """Checkout user"""

    def decode(encoded):
        """ Decode a JSON Web Token into a python object (dict) """

    def encode(payload):
        """ Encode a python object (dict) into a JSON Web Token """

    def make_svg(payload, is_secret=True):
        """ Create an SVG from payload. If secret is supplied, encode the data as JWT.
        """

    def __contains__(userid):
        """ Basically if someone has checked in. """

    def __iter__():
        """ Iter over checked in userids """

    def __len__():
        """ Of checked in users """


class IPresenceEventLog(Interface):
    """ Handle logging of check-in/out"""


class IPresenceEvent(Interface):
    """ Base for check-in check-out events. If you want to catch all use this."""
    userid = Attribute("UserID")
    meeting = Attribute("Meeting event is for")


class IParticipantCheckIn(IPresenceEvent):
    """ User has checked in """


class IParticipantCheckOut(IPresenceEvent):
    """ User has checked out """
