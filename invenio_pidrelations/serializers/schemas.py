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

from .utils import serialize_relations
from marshmallow import Schema, fields, pre_dump
from invenio_pidrelations.models import PIDRelation, RelationType
# from .utils import serialize_relations


class RelationSchema(Schema):
    """Relation metadata schema."""

    __RELATION_TYPE__ = RelationType.VERSION

    # NOTE: Maybe do `fields.Function` for all of these and put them in `utils`
    parent = fields.Method('dump_parent', dump_only=True)
    siblings = fields.Method('dump_siblings', dump_only=True)

    @pre_dump
    def _prepare_relation_info(self, obj):
        # Raise validation error (or maybe runtime?)
        assert 'pid' in self.context
        return obj

    def dump_parent(self, obj):
        rv = (PIDRelation
              .parent(self.context['pid'], self.__RELATION_TYPE__)
              .pid_value)
        return rv

    def dump_siblings(self, obj):
        siblings = PIDRelation.siblings(
            self.context['pid'], self.__RELATION_TYPE__).all()
        self.context['_siblings'] = siblings
        rv = [pid.pid_value for pid in siblings]
        return rv


class OrderedRelationSchema(RelationSchema):
    """Versions metadata schema."""

    def dump_siblings(self, obj):
        pass

    def get_next(self, obj):
        siblings = self.context['_siblings']
        next_idx = siblings.index(self.context['pid']) + 1
        return (siblings[next_idx].pid_value if next_idx < len(siblings)
                else None)

    def get_prev(self, obj):
        siblings = self.context['_siblings']
        prev_idx = siblings.index(self.context['pid']) - 1
        return siblings[prev_idx].pid_value if prev_idx >= 0 else None

    order = fields.Function(
        lambda v, ctx: ctx['_siblings'].index(ctx['pid']),
        dump_only=True)

    next = fields.Method('get_next', dump_only=True)
    prev = fields.Method('get_prev', dump_only=True)

    is_first = fields.Function(
        lambda x, ctx: ctx['_siblings'][0] == ctx['pid'],
        dump_only=True)
    is_last = fields.Function(
        lambda x, ctx: ctx['_siblings'][-1] == ctx['pid'],
        dump_only=True)


def make_relation_schema(relation_type, schema_class):
    assert relation_type in RelationType

    class relation_schema_class(schema_class):
        __RELATION_TYPE__ = relation_type
        pass
    return relation_schema_class


## TODO: Check if RelationSchema above is not duplicate
class RelationsSchema(Schema):
    """Relation metadata schema."""

    version = fields.Nested(make_relation_schema(RelationType.VERSION,
                                                 OrderedRelationSchema),
                            dump_only=True)

    # collections = fields.List(
    #     UnorderedRelationSchema(RelationType.COLLECTION))
