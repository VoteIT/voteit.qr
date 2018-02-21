# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from deform import Button
from jwt import DecodeError
from arche.views.base import BaseView
from arche.views.base import DefaultEditForm
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config
from pyramid.view import view_defaults
from voteit.core import security
from voteit.core.models.interfaces import IMeeting
from voteit.core.views.control_panel import control_panel_category
from voteit.core.views.control_panel import control_panel_link
from zope.interface.interfaces import ComponentLookupError
try:
    from voteit.irl.models.interfaces import IParticipantNumbers
    use_pns = True
except ImportError:
    use_pns = False
from voteit.qr.interfaces import IPresenceQR
from voteit.qr import _


@view_defaults(context=IMeeting)
class QRViews(BaseView):

    @reify
    def presence_qr(self):
        return self.request.registry.getAdapter(self.request.meeting, IPresenceQR)

    def get_payload(self):
        try:
            return self.presence_qr.decode(self.request.body)
        except DecodeError:
            raise HTTPBadRequest('Invalid Json Web Token')

    @view_config(name='meeting_qr_endpoint.svg',
                 permission=security.MODERATE_MEETING,
                 http_cache=0)
    def endpoint_svg(self):
        url = self.request.resource_url(self.context, 'meeting_qr_receiver')
        payload = {
            'action': 'register_endpoint',
            'endpoint': url,
            'secret': self.presence_qr.secret,
        }
        body = self.presence_qr.make_svg(payload, is_secret=False)
        return Response(body, content_type=b'image/svg+xml')

    @view_config(name='meeting_qr_userid.svg',
                 permission=security.VIEW,
                 http_cache=0)
    def userid_svg(self):
        payload = {
            'userid': self.request.authenticated_userid,
        }
        body = self.presence_qr.make_svg(payload)
        return Response(body, content_type=b'image/svg+xml')

    @view_config(request_method='POST',
                 name='meeting_qr_receiver',
                 renderer='json',
                 permission=NO_PERMISSION_REQUIRED)
    def receiver(self):
        payload = self.get_payload()
        try:
            userid = payload['userid']
        except KeyError:
            raise HTTPBadRequest('Invalid data')
        response = {}
        if not self.request.has_permission(security.VIEW, context=self.context, for_userid=userid):
            raise HTTPForbidden("Not part of this meeting")
        # Check actions against what's being sent?
        translate = self.request.localizer.translate
        if userid not in self.presence_qr:
            response['message'] = translate(_("You've checked in as ${userid}",
                                              mapping={'userid': userid}))
            self.presence_qr.checkin(userid, self.request)
        elif userid in self.presence_qr:
            # Essentially an action was performed
            value = payload.get('value', None)
            if value:
                if value == 'yes':
                    self.presence_qr.checkout(userid, self.request)
                    response['message'] = translate(_("Checked out"))
                elif value == 'no':
                    response['message'] = translate(_("OK, you're still checked in"))
                else:
                    response['message'] = translate(_("${act} is not a valid action",
                                                      mapping={'act': value}))
            else:
                response['question'] = {
                    'text': _("You're checked in. Do you want to exit and check out?"),
                    'buttons': (
                        ('no', 'No'),
                        ('yes', 'Yes'),
                    ),
                    'data': payload,
                }
        body = self.presence_qr.encode(response)
        return Response(body, content_type=b'application/jwt')

    @view_config(name='user_check_page',
                 renderer='voteit.qr:templates/user_check_page.pt',
                 permission=security.VIEW)
    def user_check_page(self):
        return {
            'qr_img_url': self.request.resource_url(self.context, 'meeting_qr_userid.svg'),
            'checked_in': self.request.authenticated_userid in self.presence_qr,
            'status_url': self.request.resource_url(self.context, 'my_checkin_status.json')
        }

    @view_config(name='register_endpoint_page',
                 renderer='voteit.qr:templates/register_endpoint_page.pt',
                 permission=security.MODERATE_MEETING)
    def register_endpoint_page(self):
        return {
            'qr_img_url': self.request.resource_url(self.context, 'meeting_qr_endpoint.svg'),
        }

    @view_config(name='checked_in_users',
                 renderer='voteit.qr:templates/checked_in_users.pt',
                 permission=security.MODERATE_MEETING)
    def checked_in_users(self):
        if use_pns:
            pns = IParticipantNumbers(self.context)
            if not len(pns):
                pns = None
        else:
            pns = None
        users = []
        for userid in self.presence_qr:
            try:
                user = self.request.root['users'][userid]
            except KeyError:
                user = None
            row = {'userid': userid,
                   'fullname': user and user.title or '',}
            if pns:
                row['pn'] = pns.userid_to_number.get(userid, '')
            users.append(row)
        users = sorted(users, key=lambda x: x['fullname'].lower())
        return {'pns': pns, 'users': users}


@view_config(context=IMeeting,
             name="qr_settings",
             renderer="arche:templates/form.pt",
             permission=security.MODERATE_MEETING)
class QRSettingsForm(DefaultEditForm):
    schema_name = 'settings'
    type_name = 'QR'
    title = _("QR settings")

    @reify
    def presence_qr(self):
       return IPresenceQR(self.context)

    def appstruct(self):
        appstruct = dict(self.presence_qr.settings)
        appstruct['active'] = self.presence_qr.active
        return appstruct

    def save_success(self, appstruct):
        self.presence_qr.active = appstruct.pop('active', False)
        self.presence_qr.settings = appstruct
        self.flash_messages.add(self.default_success, type="success")
        return HTTPFound(location=self.request.resource_url(self.context))


@view_config(context=IMeeting,
             name="manual_checkin",
             renderer="arche:templates/form.pt",
             permission=security.MODERATE_MEETING)
class QRManualCheckin(DefaultEditForm):
    schema_name = 'manual_checkin'
    type_name = 'QR'
    title = _("Manual checkin")
    buttons = (
        Button('checkin', title=_("Check-in"), ),
        Button('checkout', title=_("Check-out"), ),
        Button('status', title=_("Status"), ),
    )

    @reify
    def presence_qr(self):
        return IPresenceQR(self.context)

    def checkin_success(self, appstruct):
        userid = appstruct['userid']
        if self.presence_qr.checkin(userid, self.request):
            self.flash_messages.add(_("Checked in"), type="success")
        else:
            self.flash_messages.add(_("Already checked in"), type="warning")
        return HTTPFound(location=self.request.resource_url(self.context, 'manual_checkin'))

    def checkout_success(self, appstruct):
        userid = appstruct['userid']
        if self.presence_qr.checkout(userid, self.request):
            self.flash_messages.add(_("Checked out"), type="success")
        else:
            self.flash_messages.add(_("Already checked out"), type="warning")
        return HTTPFound(location=self.request.resource_url(self.context, 'manual_checkin'))

    def status_success(self, appstruct):
        userid = appstruct['userid']
        if userid in self.presence_qr:
            self.flash_messages.add(_("User is checked in"), type="success")
        else:
            self.flash_messages.add(_("User is checked out"), type="danger")
        return HTTPFound(location=self.request.resource_url(self.context, 'manual_checkin'))


def _qr_codes_active(context, request, va=None):
    try:
        pqr = IPresenceQR(request.meeting)
    except ComponentLookupError:
        return
    return bool(pqr.secret)


def meeting_nav_link(context, request, va, **kw):
    """ Link to check-in or check-out from meeting. """
    try:
        pqr = IPresenceQR(request.meeting)
    except ComponentLookupError:
        return
    if not pqr.active:
        return
    if request.authenticated_userid in pqr:
        title = _("Check-out")
    else:
        title = _("Check-in")
    url = request.resource_path(request.meeting, 'user_check_page')
    return """<li><a data-open-modal href="%s">%s</a></li>""" % (url, request.localizer.translate(title))


def includeme(config):
    config.scan(__name__)
    config.add_view_action(
        control_panel_category,
        'control_panel', 'qr',
        panel_group='control_panel_qr',
        title=_("QR codes"),
        description=_("Checkin with QR codes."),
        permission=security.MODERATE_MEETING,
        check_active=_qr_codes_active,
    )
    config.add_view_action(
        control_panel_link,
        'control_panel_qr', 'settings',
        title=_("Settings"),
        view_name='qr_settings',
    )
    config.add_view_action(
        control_panel_link,
        'control_panel_qr', 'register_endpoint',
        title=_("Register endpoint"),
        view_name='register_endpoint_page',
    )
    config.add_view_action(
        control_panel_link,
        'control_panel_qr', 'manual_checkin',
        title=_("Manual check-in"),
        view_name='manual_checkin',
    )
    config.add_view_action(
        control_panel_link,
        'control_panel_qr', 'checked_in_users',
        title=_("Show checked in users"),
        view_name='checked_in_users',
    )
    config.add_view_action(
        meeting_nav_link,
        'nav_meeting', 'qr_check_user',
        permission=security.VIEW,
    )
