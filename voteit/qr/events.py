from voteit.core.models.interfaces import IMeeting
from zope.interface import implementer

from voteit.qr.interfaces import IParticipantCheckIn
from voteit.qr.interfaces import IParticipantCheckOut


class _BaseEvent(object):

    def __init__(self, userid, meeting):
        self.userid = userid
        assert IMeeting.providedBy(meeting)
        self.meeting = meeting


@implementer(IParticipantCheckIn)
class ParticipantCheckIn(_BaseEvent):
    """Participant arrived."""


@implementer(IParticipantCheckOut)
class ParticipantCheckOut(_BaseEvent):
    """Participant left."""

    def add(userid, event_name):
        """ Add an event for userid.
        """

    def total(userid):
        """ Total present time, returns timedelta.
        """

    def get(userid, default=None):
        """ similar to dict get.
        """
