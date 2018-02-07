# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import colander
import deform
from arche.schemas import userid_hinder_widget
from arche.validators import existing_userids, ExistingUserIDs
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPNotFound

from voteit.vote_groups import _
from voteit.vote_groups.interfaces import IVoteGroups
from voteit.vote_groups.mixins import VoteGroupEditMixin


def includeme(config):
    pass
