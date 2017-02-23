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

"""Module tests."""

from __future__ import absolute_import, print_function

from invenio_pidrelations.api import PIDConcept
from invenio_pidrelations.models import PIDRelation
from invenio_pidrelations.utils import resolve_relation_type_config


def test_basic_api_methods(app, db, pids):
    # Set-up
    h1, h1v1, h1v2, h1v3, h2, h2v1, c1, c1r1, c1r2, pid1 = \
        (pids[p] for p in ['h1', 'h1v1', 'h1v2', 'h1v3', 'h2', 'h2v1',
                           'c1', 'c1r1', 'c1r2', 'pid1'])
    ORDERED = resolve_relation_type_config('ordered').id
    UNORDERED = resolve_relation_type_config('unordered').id

    # Test the "children" property and "get_children" method
    # Ordered relations
    assert PIDConcept(
        parent=h1, relation_type=ORDERED).children.count() == 3
    assert set([h1v3, h1v2, h1v1]) == set(PIDConcept(
        parent=h1, relation_type=ORDERED).children.all())
    assert [h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    assert PIDConcept(
        parent=h1v1, relation_type=ORDERED).children.count() == 0
    # Unordered relations
    assert PIDConcept(
        parent=c1, relation_type=UNORDERED).children.count() == 2
    assert set([c1r1, c1r2]) == set(PIDConcept(
        parent=c1, relation_type=UNORDERED).children.all())
    assert PIDConcept(
        parent=c1r1, relation_type=UNORDERED).children.count() == 0
    # Unrelated PIDs
    assert PIDConcept(
        parent=pid1, relation_type=ORDERED).children.count() == 0

    # Test the "parents" property
    assert PIDConcept(child=h1, relation_type=ORDERED).parents.count() == 0
    assert h1 == PIDConcept(child=h1v1, relation_type=ORDERED).parents.one()
    assert h1 == PIDConcept(child=h1v2, relation_type=ORDERED).parents.one()

    # # Test the "parent" property
    assert h1 == PIDConcept(child=h1v1, relation_type=ORDERED).parent
    assert h1 == PIDConcept(child=h1v2, relation_type=ORDERED).parent

    # Test "has_children", "has_parents"
    # Ordered relations
    assert PIDConcept(parent=h1, relation_type=ORDERED).has_children is True
    assert PIDConcept(child=h1, relation_type=ORDERED).has_parents is False

    assert PIDConcept(
        parent=h1v1, relation_type=ORDERED).has_children is False
    assert PIDConcept(
        child=h1v1, relation_type=ORDERED).has_parents is True

    # Unordered relations
    assert PIDConcept(
        parent=c1, relation_type=UNORDERED).has_children is True
    assert PIDConcept(
        child=c1, relation_type=UNORDERED).has_parents is False

    # Unrelated PIDs
    assert PIDConcept(
        parent=pid1, relation_type=ORDERED).has_children is False
    assert PIDConcept(
        child=pid1, relation_type=ORDERED).has_parents is False

    # Test "is_child", "is_parent" properties
    assert PIDConcept(parent=h1, relation_type=ORDERED).is_parent is True
    assert PIDConcept(parent=h1v1, relation_type=ORDERED).is_parent is False
    assert PIDConcept(child=h1v1, relation_type=ORDERED).is_child is True
    assert PIDConcept(child=h1, relation_type=ORDERED).is_child is False
    pidc1 = PIDConcept(parent=h1, child=h1v1, relation_type=ORDERED)
    assert pidc1.is_child is True
    assert pidc1.is_parent is True

    assert PIDConcept(parent=pid1, relation_type=ORDERED).is_parent is False
    assert PIDConcept(child=pid1, relation_type=ORDERED).is_child is False
    pidc1 = PIDConcept(parent=pid1, child=pid1, relation_type=ORDERED)
    assert pidc1.is_child is False
    assert pidc1.is_parent is False

    # Test "last_child", "is_last_child" properties
    # Ordered relations
    assert h1v3 == PIDConcept(parent=h1, relation_type=ORDERED).last_child
    assert PIDConcept(child=h1v3, relation_type=ORDERED).is_last_child is True
    assert PIDConcept(child=h1v2, relation_type=ORDERED).is_last_child is False
    assert PIDConcept(child=h1v1, relation_type=ORDERED).is_last_child is False

    # Unordered relations
    assert PIDConcept(parent=c1, relation_type=UNORDERED).last_child is None
    assert PIDConcept(parent=c1r1,
                      relation_type=UNORDERED).is_last_child is False
    assert PIDConcept(parent=c1r2,
                      relation_type=UNORDERED).is_last_child is False

    # Unrelated PIDs
    assert PIDConcept(parent=pid1, relation_type=ORDERED).last_child is None
    assert PIDConcept(parent=pid1,
                      relation_type=ORDERED).is_last_child is False
    assert PIDConcept(parent=pid1, relation_type=UNORDERED).last_child is None
    assert PIDConcept(parent=pid1,
                      relation_type=UNORDERED).is_last_child is False

    # Test the "insert" method for ordered relations
    # Insert at the end (index=-1)
    PIDConcept(parent=h1, relation_type=ORDERED).insert_child(pid1, index=-1)
    assert [h1v1, h1v2, h1v3, pid1] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    # Make sure relations order is preserved
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1
    assert h1_c[2].child == h1v3
    assert h1_c[2].index == 2
    assert h1_c[3].child == pid1
    assert h1_c[3].index == 3

    # Return to previous state
    PIDConcept(parent=h1, relation_type=ORDERED).remove_child(
        pid1, reorder=True)
    assert [h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1

    # Insert at the first position (index=0)
    PIDConcept(parent=h1, relation_type=ORDERED).insert_child(pid1, index=0)
    assert [pid1, h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == pid1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v1
    assert h1_c[1].index == 1
    assert h1_c[2].child == h1v2
    assert h1_c[2].index == 2
    PIDConcept(parent=h1, relation_type=ORDERED).remove_child(
        pid1, reorder=True)
    assert [h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1

    # Insert at the second position (index=1)
    PIDConcept(parent=h1, relation_type=ORDERED).insert_child(pid1, index=1)
    assert [h1v1, pid1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == pid1
    assert h1_c[1].index == 1
    assert h1_c[2].child == h1v2
    assert h1_c[2].index == 2
    PIDConcept(parent=h1, relation_type=ORDERED).remove_child(
        pid1, reorder=True)
    assert [h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1

    # Insert at an arbitrarily large position (appends to the end)
    PIDConcept(parent=h1, relation_type=ORDERED).insert_child(pid1, index=100)
    assert [h1v1, h1v2, h1v3, pid1] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1
    assert h1_c[2].child == h1v3
    assert h1_c[2].index == 2
    assert h1_c[3].child == pid1
    assert h1_c[3].index == 3
    PIDConcept(parent=h1, relation_type=ORDERED).remove_child(
        pid1, reorder=True)
    assert [h1v1, h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1_c[0].child == h1v1
    assert h1_c[0].index == 0
    assert h1_c[1].child == h1v2
    assert h1_c[1].index == 1

    # Remove an extra child
    PIDConcept(parent=h1, relation_type=ORDERED).remove_child(
        h1v1, reorder=True)
    assert [h1v2, h1v3] == PIDConcept(
        parent=h1, relation_type=ORDERED).get_children(ordered=True).all()
    h1_c = h1.child_relations.order_by(PIDRelation.index).all()
    assert h1.child_relations.count() == 2
    assert h1_c[0].child == h1v2
    assert h1_c[0].index == 0
