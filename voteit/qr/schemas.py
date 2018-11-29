# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import colander
from arche.widgets import deferred_autocompleting_userid_widget
from arche.security import principal_has_permisson
from voteit.core.security import VIEW
from voteit.irl.schemas import deferred_existing_participant_number_validator

from voteit.qr import _


@colander.deferred
class UserCanViewMeeting(object):

    def __init__(self, node, kw):
        self.context = kw['context']
        self.request = kw['request']

    def __call__(self, node, value):
        if not value:
            raise colander.Invalid(node, _("No UserID"))
        if not principal_has_permisson(self.request, value, VIEW, context=self.context):
            raise colander.Invalid(
                node,
                _("That user doesn't have permission to view this meeting.")
            )


class QRSettingsSchema(colander.Schema):
    active = colander.SchemaNode(
        colander.Bool(),
        title = _("Enable QR code checkin?"),
    )
    log_time = colander.SchemaNode(
        colander.Bool(),
        title=_("Log time present for all users?"),
        default=True,
    )
    assign_pn = colander.SchemaNode(
        colander.Bool(),
        title = _("Create and assign a participant number at checkin if the user lacks one?"),
    )


@colander.deferred
def submitted_userid(node, kw):
    request = kw['request']
    return request.params.get('userid', '')


class QRManualCheckin(colander.Schema):
    userid = colander.SchemaNode(
        colander.String(),
        title=_("UserID"),
        widget=deferred_autocompleting_userid_widget,
        validator=UserCanViewMeeting,
        default=submitted_userid,
    )
    pn = colander.SchemaNode(
        colander.Int(),
        title=_('Set participant number'),
        missing=None,
    )


def includeme(config):
    config.add_schema('QR', QRSettingsSchema, 'settings')
    config.add_schema('QR', QRManualCheckin, 'manual_checkin')
