# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import colander
from arche.widgets import deferred_autocompleting_userid_widget
from voteit.core.security import VIEW

from voteit.qr import _


@colander.deferred
class UserCanViewMeeting(object):

    def __init__(self, node, kw):
        self.request = kw['request']

    def __call__(self, node, value):
        if not value:
            raise colander.Invalid(node, _("No UserID"))
        if not self.request.has_permission(VIEW, context=self.request.meeting, for_userid=value):
            raise colander.Invalid(
                node,
                _("That user doesn't have permission to view this meeting.")
            )


class QRSettingsSchema(colander.Schema):
    active = colander.SchemaNode(
        colander.Bool(),
        title = _("Enable QR code checkin?"),
    )
    #Any other settings?


@colander.deferred
def submitted_userid(node, kw):
    request = kw['request']
    return request.params.get('userid', '')


class QRManualCheckin(colander.Schema):
    userid = colander.SchemaNode(
        colander.String(),
        title = _("UserID"),
        widget = deferred_autocompleting_userid_widget,
        validator = UserCanViewMeeting,
        default=submitted_userid,
    )


def includeme(config):
    config.add_schema('QR', QRSettingsSchema, 'settings')
    config.add_schema('QR', QRManualCheckin, 'manual_checkin')
