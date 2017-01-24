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

"""Persistent identifier's relations models."""

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

from invenio_pidstore.models import PersistentIdentifier

_ = make_lazy_gettext(lambda: gettext)

logger = logging.getLogger('invenio-pidrelations')


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
    """Model persistent identifier relations."""

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

    @staticmethod
    def children(pid, relation_type, ordered=False):
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

    @staticmethod
    def parents(pid, relation_type):
        """Return the PID parents for given relation."""
        return db.session.query(PersistentIdentifier).join(
            PIDRelation,
            PIDRelation.parent_pid_id == PersistentIdentifier.id
        ).filter(
            PIDRelation.child_pid_id == pid.id,
            PIDRelation.relation_type == relation_type
        )

    @classmethod
    def parent(cls, pid, relation_type):
        """Return the parent of the PID in given relation.

        NOTE: Not supporting relations, which allow for multiple parents,
              e.g. Collection.
        """
        q = cls.parents(pid, relation_type)
        if q.count() > 1:
            raise Exception("PID has more than one parent for this relation.")
        else:
            return q.first()

    @classmethod
    def siblings(cls, pid, relation_type, ordered=False, parent_pid=None):
        parent = parent_pid or cls.parent(pid, relation_type)
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
        return cls.children(pid, relation_type).count() > 0

    @classmethod
    def has_parents(cls, pid, relation_type):
        return cls.parents(pid, relation_type).count() > 0

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

    @staticmethod
    def remove(parent_pid, child_pid, relation_type, reorder=False):
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


__all__ = (
    'PIDRelation',
    'RelationType',
)
