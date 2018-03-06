from unittest import TestCase

from BTrees.OOBTree import OOBTree
from datetime import datetime, timedelta

from persistent.list import PersistentList
from pyramid import testing
from pyramid.request import apply_request_extensions
from six import string_types
from voteit.core.models.meeting import Meeting
from voteit.core.models.user import User
from voteit.core.security import ROLE_VIEWER
from voteit.core.testing_helpers import bootstrap_and_fixture
from voteit.irl.models.interfaces import IParticipantNumbers
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from voteit.qr.interfaces import IPresenceQR
from voteit.qr.interfaces import IPresenceEventLog
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


class PresenceEventLogTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from voteit.qr.models import PresenceEventLog
        return PresenceEventLog

    def _mk_one(self):
        from voteit.core.models.meeting import Meeting
        return self._cut(Meeting())

    def test_verify_class(self):
        self.assertTrue(verifyClass(IPresenceEventLog, self._cut))

    def test_verify_obj(self):
        self.assertTrue(verifyObject(IPresenceEventLog, self._mk_one()))

    def test_add(self):
        obj = self._mk_one()
        obj.add('jane', 'checkin')
        self.assertIn('jane', obj)
        obj.add('jane', 'checkout')
        self.assertEqual(len(obj['jane']), 1)
        self.assertRaises(ValueError, obj.add, 'jane', 'what')

    def test_total(self):
        obj = self._mk_one()
        obj['jane'] = PersistentList()
        # 3 before lunch
        obj['jane'].append(
            {'in': datetime(2018, 2, 28, hour=9, minute=30),
             'out': datetime(2018, 2, 28, hour=12, minute=30)})
        # 4 after
        obj['jane'].append(
            {'in': datetime(2018, 2, 28, hour=13, minute=30),
             'out': datetime(2018, 2, 28, hour=17, minute=30)})
        self.assertEqual(obj.total('jane'), timedelta(hours=7))


class SubscriberIntegrationTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _fixture(self):
        root = bootstrap_and_fixture(self.config)
        self.config.include('arche.portlets')
        self.config.include('voteit.irl')
        self.config.include('voteit.qr')
        request = testing.DummyRequest()
        request.root = root
        apply_request_extensions(request)
        self.config.begin(request)
        root['m'] = Meeting()
        root['users']['jane'] = User()
        root['m'].local_roles['jane'] = [ROLE_VIEWER]
        return root, request

    def test_assign_pn_if_user_lacks_one(self):
        from voteit.qr.events import ParticipantCheckIn
        root, request = self._fixture()
        meeting = root['m']
        pqr = IPresenceQR(meeting)
        pqr.settings = {'assign_pn': True}
        event = ParticipantCheckIn('jane', meeting)
        request.registry.notify(event)
        pns = IParticipantNumbers(meeting)
        self.assertEqual(pns.userid_to_number.get('jane', None), 1)

    def test_assign_pn_if_user_lacks_one_not_enabled(self):
        from voteit.qr.events import ParticipantCheckIn
        root, request = self._fixture()
        meeting = root['m']
        pqr = IPresenceQR(meeting)
        pqr.settings = {'assign_pn': False}
        event = ParticipantCheckIn('jane', meeting)
        request.registry.notify(event)
        pns = IParticipantNumbers(meeting)
        self.assertEqual(pns.userid_to_number.get('jane', None), None)
