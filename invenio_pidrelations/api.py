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

from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_db import db
from .models import PIDRelation, RelationType


class PIDVersionRelation(object):
    """API for PID version relations."""

    def __init__(self, pid):
        # TODO: Use as a wrapper?
        pass

    @staticmethod
    def create_head(pid, head_pid_value):
        """
        Create a Head PID for the Version PID.

        :param pid: Version PID for which a Head PID should be created.
        :type pid: invenio_pidstore.models.PersistentIdentifier
        :param head_pid_value: Head PID value of the new Head PID
        :type head_pid_value: str
        :return: Resulting Head PID
        :rtype: PersistentIdentifier
        """
        head_pid = PersistentIdentifier.create(
            pid_type=pid.pid_type,
            pid_value=head_pid_value,
            object_type=pid.object_type,
            status=PIDStatus.REGISTERED
        )
        head_pid.redirect(pid)
        PIDRelation.create(head_pid, pid, RelationType.VERSION, 0)
        return head_pid

    @staticmethod
    def is_head(pid):
        """Determine if 'pid' is a Head PID."""
        return PIDRelation.has_children(pid, RelationType.VERSION)

    @classmethod
    def get_head(cls, pid):
        """
        Get the Head PID of a PID in the argument.

        If 'pid' is already the Head PID, return it, otherwise
        return the Head PID as defined in the relation table.
        In case the PID does not have a Head PID, return None.
        """

        if cls.is_head(pid):
            return pid
        else:
            return PIDRelation.parent(pid, RelationType.VERSION)

    @staticmethod
    def is_version(pid):
        """
        Determine if 'pid' is a Version PID.

        Resolves as True for any PID which has a Head PID, False otherwise.
        """
        return PIDRelation.parents(pid, RelationType.VERSION).count() == 1

    @classmethod
    def is_latest(cls, pid):
        """
        Determine if 'pid' is the latest version of a resource.

        Resolves True for Versioned PIDs which are the oldest of its siblings.
        False otherwise, also for Head PIDs.
        """
        latest_pid = cls.get_latest(pid)
        if latest_pid is None:
            return False
        return latest_pid == pid

    @classmethod
    def get_latest(cls, pid):
        """
        Get the latest PID as pointed by the Head PID.

        If the 'pid' is a Head PID, return the latest of its children.
        If the 'pid' is a Version PID, return the latest of its siblings.
        Return None for the non-versioned PIDs.
        """

        head = cls.get_head(pid)
        if head is None:
            return None
        else:
            return head.child_relations.order_by(
                PIDRelation.order.desc()).first().child_pid

    @classmethod
    def get_all_versions(cls, pid):
        """
        Works both for Head PIDS (return the children) and Version PIDs (return
        all sibling including self).
        Return None otherwise.
        """
        head = cls.get_head(pid)
        if head is None:
            return None
        return [pr.child_pid for pr in
                head.child_relations.order_by(PIDRelation.order).all()]

    @classmethod
    def insert_version(cls, head_pid, pid, index):
        """Insert 'pid' to the versioning scheme."""
        # TODO: For linking usecase: check if 'pid' has a Head already,
        #       if so, remove it first
        with db.session.begin_nested():
            PIDRelation.insert(head_pid, pid, RelationType.VERSION,
                               index=index)
            latest_pid = cls.get_latest(head_pid)
            head_pid.redirect(latest_pid)

    @classmethod
    def remove_version(cls, pid):
        """Remove the 'pid' from the versioning scheme."""
        # TODO: Implement removing of a single versioned element (remove Head?)
        with db.session.begin_nested():
            head_pid = cls.get_head(pid)
            PIDRelation.remove(head_pid, pid, RelationType.VERSION,
                               reorder=True)
            latest_pid = cls.get_latest(head_pid)
            head_pid.redirect(latest_pid)


__all__ = (
    'PIDVersionRelation',
)
