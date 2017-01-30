# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015, 2016 CERN.
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

"""API for PID relations concepts."""

from __future__ import absolute_import, print_function

from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from werkzeug.local import LocalProxy

# from .models import PIDRelation, RelationType
from .api import PIDConcept
from .proxies import current_pidrelations


class PIDVersioning(PIDConcept):
    """API for PID versioning relations.

    - Adds automatic redirection handling for Parent-LastChild
    - Sets stricter method signatures, e.g.: 'index' is mandatory parameter
        when calling 'insert'.
    """

    relation_type = LocalProxy(
        lambda: current_pidrelations.relation_types['VERSION']
    )

    def __init__(self, pid=None, child=None, parent=None, relation=None):
        if relation:
            super(PIDVersioning, self).__init__(relation=relation)
        if pid:
            if PIDVersioning.is_child(pid):
                child = pid
                parent = PIDVersioning.get_parent(pid)
            else:
                parent = pid
            super(PIDVersioning, self).__init__(
                child=child, parent=parent, relation_type=self.relation_type,
                relation=relation)
        else:
            self.child = child
            self.parent = parent

        if not self.parent:
            self.parent = self.get_parent(self.child)

    def insert(self, child, index):
        # Impose index as mandatory key
        # TODO: For linking usecase: check if 'pid' has a parent already,
        #       if so, raise or remove it first
        assert index is not None, "You must specify the insertion index."
        with db.session.begin_nested():
            super(PIDVersioning, self).insert(child, index=index)
            self.parent.redirect(child)

    def remove(self):
        # Impose index as mandatory key
        # TODO: When removing single versioned element remove the redirection
        # always reorders after removing
        with db.session.begin_nested():
            return super(PIDVersioning).remove(reorder=True)
            last_child = self.get_last_child()
            self.parent.redirect(last_child)

    def create_relation(self, order):
        assert order is not None, "Relation cannot be unordered"
        super(PIDVersioning, self).create_relation(order=order)

    def create_parent(self, parent_pid_value):
        relation = super(PIDVersioning, self).create_parent(parent_pid_value)
        self.parent.redirect(self.child)
        return relation


__all__ = (
    'PIDVersioning',
)
