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

"""PIDRelation JSON Schema for metadata."""

from marshmallow import Schema, fields

from ..utils import resolve_relation_type_config
from .utils import serialize_relations


class PIDSchema(Schema):
    """PID schema."""

    pid_type = fields.String()
    pid_value = fields.String()


class RelationSchema(Schema):
    """Generic PID relation schema."""

    # NOTE: Maybe do `fields.Function` for all of these and put them in `utils`
    parent = fields.Method('dump_parent')
    parents = fields.Method('dump_parents')
    child = fields.Method('dump_child')
    children = fields.Method('dump_children')
    type = fields.Method('dump_type')
    is_ordered = fields.Boolean()
    is_parent = fields.Method('_is_parent')
    is_child = fields.Method('_is_child')
    is_last = fields.Method('dump_is_last')
    # is_first = fields.Method('dump_is_first')
    index = fields.Method('dump_index')
    next = fields.Method('dump_next')
    previous = fields.Method('dump_previous')

    def _dump_relative(self, relative):
        if relative:
            data, errors = PIDSchema().dump(relative)
            return data
        else:
            return None

    def dump_next(self, obj):
        """Dump the parent of a PID."""
        if self._is_child(obj):
            return self._dump_relative(obj.next)

    def dump_previous(self, obj):
        """Dump the parent of a PID."""
        if self._is_child(obj):
            return self._dump_relative(obj.previous)

    def dump_index(self, obj):
        """Dump the index of the child in the relation."""
        if obj.is_ordered and self._is_child(obj):
            return obj.index
        else:
            return None

    def _is_parent(self, obj):
        """Check if the PID from the context is the parent in the relation."""
        return obj.parent == self.context['pid']

    def _is_child(self, obj):
        """Check if the PID from the context is the child in the relation."""
        return obj.child == self.context['pid']

    def dump_is_last(self, obj):
        """Dump the boolean stating if the child in the relation is last.

        Dumps `None` for parent serialization.
        """
        if self._is_child(obj) and obj.is_ordered:
            # TODO: This method exists in API
            return obj.children.all()[-1] == self.context['pid']
        else:
            return None

    #def dump_is_first(self, obj):
    #    """Dump the boolean stating if the child in the relation is first.
    #    Dumps `None` for parent serialization.
    #    """
    #    if self._is_child(obj) and obj.is_ordered:
    #        return obj.children.first() == self.context['pid']
    #    else:
    #        return None

    def dump_type(self, obj):
        """Dump the text name of the relation."""
        return resolve_relation_type_config(obj.relation_type).name

    def dump_parent(self, obj):
        """Dump the parent of a PID."""
        return self._dump_relative(obj.parent)

    def dump_parents(self, obj):
        """Dump the parents of a PID."""
        data, errors = PIDSchema(many=True).dump(obj.parents.all())
        return data

    def dump_child(self, obj):
        """Dump the single child of a PID."""
        return self._dump_relative(obj.child)

    def dump_children(self, obj):
        """Dump the siblings of a PID."""
        data, errors = PIDSchema(many=True).dump(obj.children.all())
        return data


class PIDRelationsMixin(object):
    """Mixin for easy inclusion of relations information in Record schemas."""

    relations = fields.Method('dump_relations')

    def dump_relations(self, obj):
        """Dump the relations to a dictionary."""
        pid = self.context['pid']
        return serialize_relations(pid)
