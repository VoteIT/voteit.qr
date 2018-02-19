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
