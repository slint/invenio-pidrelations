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

"""Persistent identifier store and registration."""

from __future__ import absolute_import, print_function

import logging
from enum import Enum

from flask_babelex import gettext
from invenio_db import db
from speaklater import make_lazy_gettext
from sqlalchemy.orm import backref
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import ChoiceType
from sqlalchemy.exc import IntegrityError

from invenio_pidstore.models import PersistentIdentifier, PIDStatus

_ = make_lazy_gettext(lambda: gettext)

logger = logging.getLogger('invenio-pidstore')


PIDRELATION_TYPE_TITLES = {
    'VERSION': _('Version'),
    'COLLECTION': _('Collection'),
}


class RelationType(Enum):
    """Constants for possible status of any given PID."""

    VERSION = 0
    """Two PIDs are subsequent versions of one another."""

    COLLECTION = 1
    """PIDs are aggregated into a collection of PIDs."""

    def __init__(self, value):
        """Hack."""

    def __eq__(self, other):
        """Equality test."""
        return self.value == other

    def __str__(self):
        """Return its name."""
        return self.name

    @property
    def title(self):
        """Return human readable title."""
        return PIDRELATION_TYPE_TITLES[self.name]


class PIDRelation(db.Model, Timestamp):
    """Store and register persistent identifiers.

    Assumptions:
      * Persistent identifiers can be represented as a string of max 255 chars.
      * An object has many persistent identifiers.
      * A persistent identifier has one and only one object.
    """

    __tablename__ = 'pidrelations_pidrelation'

    # TODO: Remove explicit PK
    id = db.Column(db.Integer, primary_key=True)
    """Id of persistent identifier entry."""

    parent_pid_id = db.Column(
        db.Integer,
        db.ForeignKey(PersistentIdentifier.id, onupdate="CASCADE",
                      ondelete="RESTRICT"),
        nullable=False)

    child_pid_id = db.Column(
        db.Integer,
        db.ForeignKey(PersistentIdentifier.id, onupdate="CASCADE",
                      ondelete="RESTRICT"),
        nullable=False)

    relation_type = db.Column(ChoiceType(RelationType, impl=db.SmallInteger()),
                              nullable=False)
    """Type of relation between the parent and child PIDs."""

    order = db.Column(db.Integer, nullable=True)
    """Order in which the PID relations (e.g.: versions sequence)."""

    #
    # Relations
    #
    parent_pid = db.relationship(
        PersistentIdentifier,
        primaryjoin=PersistentIdentifier.id == parent_pid_id,
        backref=backref('child_relations', lazy='dynamic'))

    child_pid = db.relationship(
        PersistentIdentifier,
        primaryjoin=PersistentIdentifier.id == child_pid_id,
        backref=backref('parent_relations', lazy='dynamic'))

    def __repr__(self):
        return "<PIDRelation: {parent} -> {child} ({type}, {order})>".format(
            parent=self.parent_pid.pid_value,
            child=self.child_pid.pid_value,
            type=RelationType(self.relation_type),
            order=self.order)

    @classmethod
    def children(cls, pid, relation_type, ordered=False):
        q = db.session.query(PersistentIdentifier).join(
            PIDRelation,
            PIDRelation.child_pid_id == PersistentIdentifier.id
        ).filter(
            PIDRelation.parent_pid_id == pid.id,
            PIDRelation.relation_type == relation_type
        )
        if ordered:
            return q.order_by(PIDRelation.order)
        else:
            return q

    @classmethod
    def parents(cls, pid, relation_type):
        return db.session.query(PersistentIdentifier).join(
            PIDRelation,
            PIDRelation.parent_pid_id == PersistentIdentifier.id
        ).filter(
            PIDRelation.child_pid_id == pid.id,
            PIDRelation.relation_type == relation_type
        )

    @classmethod
    def siblings(cls, pid, relation_type, ordered=False):
        parent = cls.parent(pid, relation_type)
        if parent is None:
            raise Exception("PID does not have a parent for this relation. "
                            "Impossible to determine siblings.")
        q = db.session.query(PersistentIdentifier).join(
            PIDRelation,
            PIDRelation.child_pid_id == PersistentIdentifier.id
        ).filter(
            PIDRelation.parent_pid_id == parent.id,
            PIDRelation.relation_type == relation_type
        )
        if ordered:
            return q.order_by(PIDRelation.order)
        else:
            return q

    @classmethod
    def has_children(cls, pid, relation_type):
        return cls.children.count() > 0

    @classmethod
    def has_parent(cls, pid, relation_type):
        return cls.parents.count() > 0

    @classmethod
    def insert(cls, parent_pid, child_pid, relation_type, index=None):
        """
        Argument 'index' can take the following values:
            0,1,2,... - insert child PID at the specified position
            -1 - insert the child PID at the last position
            None - insert child without order (no re-ordering is done)

            NOTE: If 'index' is specified, all sibling relations should
                  have PIDRelation.order information.

        """
        try:
            with db.session.begin_nested():
                if index is not None:
                    children = parent_pid.child_relations.filter(
                        PIDRelation.relation_type == relation_type).order_by(
                            PIDRelation.order).all()
                    relation_obj = cls.create(
                        parent_pid, child_pid, relation_type, None)
                    if index == -1:
                        children.append(relation_obj)
                    else:
                        children.insert(index, relation_obj)
                    for idx, c in enumerate(children):
                        c.order = idx
                else:
                    relation_obj = cls.create(
                        parent_pid, child_pid, relation_type, None)
        except IntegrityError:
            raise Exception("PID Relation already exists.")

    @classmethod
    def remove(cls, parent_pid, child_pid, relation_type, reorder=False):
        """
        Removes a PID relation.
        """
        with db.session.begin_nested():
            relation = PIDRelation.query.filter_by(
                parent_pid_id=parent_pid.id,
                child_pid_id=child_pid.id,
                relation_type=relation_type).one()
            db.session.delete(relation)
            if reorder:
                children = parent_pid.child_relations.filter(
                    PIDRelation.relation_type == relation_type).order_by(
                        PIDRelation.order).all()
                for idx, c in enumerate(children):
                    c.order = idx

    @classmethod
    def parent(cls, pid, relation_type):
        """Return the parent of the PID in given relation.

        NOTE: Not supporting relations, which allow for multiple
              parents, e.g. Collection.
        """
        q = cls.parents(pid, relation_type)
        if q.count() > 1:
            raise Exception("PID has more than one parent for this relation.")
        else:
            return q.first()

    @classmethod
    def create(cls, parent_pid, child_pid, relation_type, order=None):
        """Create a PID relation for given parent and child."""

        try:
            with db.session.begin_nested():
                obj = cls(parent_pid_id=parent_pid.id,
                          child_pid_id=child_pid.id,
                          relation_type=relation_type,
                          order=order)
                db.session.add(obj)
                # logger.info("Created PIDRelation {obj.parent_pid_id} -> "
                #             "{obj.child_pid_id} ({obj.relation_type}, "
                #             "order:{obj.order})".format(obj=obj))
        except IntegrityError:
            raise Exception("PID Relation already exists.")
            # msg = "PIDRelation already exists: " \
            #       "{0} -> {1} ({2})".format(
            #         parent_pid, child_pid, relation_type)
            # logger.exception(msg)
            # raise Exception(msg)
        return obj

    #
    # Version-specific methods
    #

    @classmethod
    def create_head_pid(cls, pid, head_pid_value):
        """
        Create a Head PID for the Version PID.

        :param pid: Version PID for which a Head PID should be created.
        :type pid: invenio_pidstore.models.PersistentIdentifier
        :param head_pid_value: Head PID value of the new Head PID
        :type head_pid_value: str
        :return: Resulting Head PID and PIDRelation object (tuple)
        :rtype: (PersistentIdentifier, PIDRelation)
        """
        # Create new pid here of type 'HEAD'
        # Create a PID redirect
        head_pid = PersistentIdentifier.create(
            pid_type=pid.pid_type,
            pid_value=head_pid_value,
            object_type=pid.object_type,
            status=PIDStatus.REGISTERED
        )
        head_pid.redirect(pid)
        return head_pid, cls.create(head_pid, pid, RelationType.VERSION, 0)

    @staticmethod
    def is_head_pid(pid):
        """Determine if 'pid' is a Head PID."""
        return db.session.query(PIDRelation).join(
            PersistentIdentifier,
            PIDRelation.parent_pid_id == PersistentIdentifier.id
        ).filter(
            PersistentIdentifier.id == pid.id,
            PIDRelation.relation_type == RelationType.VERSION
        ).count() > 0

    @classmethod
    def get_head_pid(cls, pid):
        """
        Get the Head PID of a PID in the argument.

        If 'pid' is already the Head PID, return it, otherwise
        return the Head PID as defined in the relation table.
        In case the PID does not have a Head PID, return None.
        """

        if cls.is_head_pid(pid):
            return pid
        else:
            q = db.session.query(PIDRelation).filter(
                PIDRelation.child_pid_id == pid.id,
                PIDRelation.relation_type == RelationType.VERSION
            )
            if q.count() == 0:
                return None
            else:
                return PersistentIdentifier.query.get(q.one().parent_pid_id)

    @staticmethod
    def is_version_pid(pid):
        """
        Determine if 'pid' is a Version PID.

        Resolves as True for any PID which has a Head PID, False otherwise.
        """
        return db.session.query(PIDRelation).filter(
            PIDRelation.child_pid_id == pid.id,
            PIDRelation.relation_type == RelationType.VERSION
        ).count() > 0

    @classmethod
    def is_latest_pid(cls, pid):
        """
        Determine if 'pid' is the latest version of a resource.

        Resolves True for Versioned PIDs which are the oldest of its siblings.
        False otherwise, also for Head PIDs.
        """
        latest_pid = cls.get_latest_pid(pid)
        if latest_pid is None:
            return False
        return latest_pid == pid

    @classmethod
    def get_latest_pid(cls, pid):
        """
        Get the latest PID as pointed by the Head PID.

        If the 'pid' is a Head PID, return the latest of its children.
        If the 'pid' is a Version PID, return the latest of its siblings.
        Return None for the non-versioned PIDs.
        """

        head = cls.get_head_pid(pid)
        if head is None:
            return None
        else:
            return head.child_relations.order_by(
                PIDRelation.order.desc()).first().child_pid

    @classmethod
    def get_all_version_pids(cls, pid):
        """
        Works both for Head PIDS (return the children) and Version PIDs (return
        all sibling including self)
        """
        head = cls.get_head_pid(pid)
        return [pr.child_pid for pr in
                head.child_relations.order_by(PIDRelation.order).all()]

    @staticmethod
    def insert_version_pid(head_pid, pid, index):
        # As regular insert but with Head PID redirect
        pass

    @staticmethod
    def remove_version_pid(pid):
        pass


__all__ = (
    'PIDRelation',
    'RelationType',
)
