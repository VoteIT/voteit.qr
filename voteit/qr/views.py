# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import jwt
import qrcode
from arche.views.base import BaseView
from arche.views.base import DefaultDeleteForm
from arche.views.base import DefaultEditForm
from deform_autoneed import need_lib
from pkg_resources._vendor.six import StringIO
from pyramid.decorator import reify
from pyramid import httpexceptions
from pyramid.response import Response
from pyramid.traversal import resource_path
from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED

from voteit.core import security
from voteit.core.models.interfaces import IMeeting

from voteit.qr import _
from voteit.qr.interfaces import IPresenceQR
from voteit.qr.models import PresenceQR

from voteit.core.views.control_panel import control_panel_category, control_panel_link


class SVGResponse(Response):
    def __init__(self, *args, **kw):
        kw['content_type'] = b'image/svg+xml'
        super(SVGResponse, self).__init__(*args, **kw)


class JsonResponse(Response):
    def __init__(self, body, secret=None, *args, **kw):
        if secret:
            body = jwt.encode(body, secret)
            kw['content_type'] = b'application/jwt'
        else:
            body = json.dumps(body)
            kw['content_type'] = b'application/json'
        super(JsonResponse, self).__init__(body, charset='utf8', *args, **kw)


class QRViews(BaseView):
    @reify
    def presence_qr(self):
        # type: () -> PresenceQR
        return self.request.registry.getAdapter(self.request.meeting, IPresenceQR)

    def get_payload(self):
        try:
            return self.presence_qr.decode(self.request.body)
        except jwt.DecodeError:
            raise httpexceptions.HTTPBadRequest('Invalid Json Web Token')

    def make_svg(self, payload, is_secret=True):
        # type: (dict) -> unicode
        if is_secret:
            payload_str = self.presence_qr.encode(payload)
        else:
            payload_str = json.dumps(payload)

        output = StringIO()
        qrcode.make(payload_str, image_factory=self.presence_qr.svg_factory).save(output)
        return output.getvalue()

    @view_config(name='meeting_qr_endpoint.svg', permission=security.MODERATE_MEETING)
    def endpoint_svg(self):
        url = self.request.resource_url(self.context, 'meeting_qr_receiver')
        payload = {
            'action': 'register_endpoint',
            'endpoint': url,
            'secret': self.presence_qr.secret,
        }
        return SVGResponse(self.make_svg(payload, is_secret=False))

    @view_config(name='meeting_qr_userid.svg')
    def userid_svg(self):
        payload = {
            'userid': self.request.authenticated_userid,
        }
        return SVGResponse(self.make_svg(payload))

    @view_config(request_method='POST', name='meeting_qr_receiver', permission=NO_PERMISSION_REQUIRED)
    def receiver(self):
        payload = self.get_payload()
        if 'userid' not in payload:
            raise httpexceptions.HTTPBadRequest('Invalid data')
        response_payload = {
            'question': {
                'text': 'Hi there, ' + payload['userid'] + '. What do you think?',
                'buttons': (
                    ('no', 'Horrible'),
                    ('yes', 'Amazing'),
                ),
                'data': payload,
            }
        }
        # response_payload = {'message': 'Hi there, ' + payload['userid']}
        return JsonResponse(response_payload, secret=self.presence_qr.secret)


def includeme(config):
    config.scan(__name__)
    # config.add_view_action(
    #     control_panel_category,
    #     'control_panel', 'vote_groups',
    #     panel_group='control_panel_vote_groups',
    #     title=_("Vote groups"),
    #     description=_("Handle voter rights with vote groups."),
    #     permission=security.MODERATE_MEETING,
    #     check_active=vote_groups_active
    # )
    # config.add_view_action(
    #     control_panel_link,
    #     'control_panel_vote_groups', 'vote_groups',
    #     title=_("Manage vote groups"),
    #     view_name='vote_groups',
    # )
