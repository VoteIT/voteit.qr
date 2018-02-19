from unittest import TestCase

from BTrees.OOBTree import OOBTree
from pyramid import testing
from six import string_types
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from voteit.qr.interfaces import IPresenceQR
from voteit.qr.interfaces import IParticipantCheckIn
from voteit.qr.interfaces import IParticipantCheckOut


class PresenceQRTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.qr.models import PresenceQR
        return PresenceQR

    def _mk_one(self):
        from voteit.core.models.meeting import Meeting
        return self._cut(Meeting())

    def test_verify_class(self):
        self.assertTrue(verifyClass(IPresenceQR, self._cut))

    def test_verify_obj(self):
        self.assertTrue(verifyObject(IPresenceQR, self._mk_one()))

    def test_active_generates_secret(self):
        obj = self._mk_one()
        #self.assertFalse(obj.secret)
        obj.active = True
        self.assertIsInstance(obj.secret, string_types)
        self.assertTrue(obj.active)
        obj.active = False
        self.assertEqual(obj.secret, None)
        self.assertFalse(obj.active)

    def test_checkin(self):
        obj = self._mk_one()
        request = testing.DummyRequest()
        obj.checkin('jane', request)
        self.assertIn('jane', obj)

    def test_checkin_event(self):
        L = []
        def _sub(event):
            L.append(event)
        self.config.add_subscriber(_sub, IParticipantCheckIn)
        self.assertFalse(L)
        obj = self._mk_one()
        request = testing.DummyRequest()
        obj.checkin('jane', request)
        self.assertEqual(len(L), 1)

    def test_checkout(self):
        obj = self._mk_one()
        obj.userids.add('jane')
        self.assertIn('jane', obj)
        request = testing.DummyRequest()
        obj.checkout('jane', request)
        self.assertNotIn('jane', obj)

    def test_checkout_event(self):
        L = []
        def _sub(event):
            L.append(event)
        self.config.add_subscriber(_sub, IParticipantCheckOut)
        self.assertFalse(L)
        obj = self._mk_one()
        request = testing.DummyRequest()
        obj.checkin('jane', request)
        self.assertEqual(len(L), 0)
        obj.checkout('jane', request)
        self.assertEqual(len(L), 1)

    def test_settings(self):
        obj = self._mk_one()
        obj.settings = {1: 1}
        self.assertIsInstance(obj.settings, OOBTree)
        self.assertEqual(dict(obj.settings), {1: 1})
