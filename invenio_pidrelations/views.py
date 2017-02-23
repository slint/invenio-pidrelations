# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Views for PID Relations."""

from flask import Blueprint

from .contrib.versioning import PIDVersioning

blueprint = Blueprint(
    'invenio_pidrelation',
    __name__,
    template_folder='templates'
)


@blueprint.app_template_filter()
def latest_pid_version(pid):
    """Get last PID."""
    return PIDVersioning(child=pid).get_last_child()


@blueprint.app_template_filter()
def head_pid_version(pid):
    """Get head PID of a PID."""
    return PIDVersioning.get_parent(pid)


@blueprint.app_template_test()
def latest_version(pid):
    """Determine if PID is the last version."""
    return PIDVersioning.is_latest(pid)


@blueprint.app_template_filter()
def all_versions(pid):
    """Get all versions of a PID."""
    return PIDVersioning(pid).children()
