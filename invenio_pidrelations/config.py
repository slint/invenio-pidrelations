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

"""Invenio module that adds PID relations to the Invenio-PIDStore module."""

from collections import namedtuple

RelationType = namedtuple('RelationType',
                          ['id', 'name', 'label', 'api', 'schema'])

PIDRELATIONS_RELATION_TYPES = [
    RelationType(0, 'ordered', 'Ordered',
                 'invenio_pidrelations.api:PIDConceptOrdered',
                 'invenio_pidrelations.serializers.schemas.RelationSchema'),
    RelationType(1, 'unordered', 'Unordered',
                 'invenio_pidrelations.api:PIDConcept',
                 'invenio_pidrelations.serializers.schemas.RelationSchema'),
    RelationType(2, 'version', 'Version',
                 'invenio_pidrelations.contrib.versioning:PIDVersioning',
                 'invenio_pidrelations.serializers.schemas.RelationSchema'),
]

PIDRELATIONS_RELATION_TYPES2 = {
    'ORDERED': 0,
    'UNORDERED': 1,
    'VERSION': 2,
}
"""Relation types definition."""

PIDRELATIONS_RELATION_TYPES_SERIALIZED_NAMES = \
    dict((v, k.lower()) for k, v in PIDRELATIONS_RELATION_TYPES2.items())
"""Serialized names of the relation types."""

PIDRELATIONS_RELATION_TYPES_SERIALIZED_NAMES = \
    dict((v, k.lower()) for k, v in PIDRELATIONS_RELATION_TYPES2.items())
"""Serialized names of the relation types."""

PIDRELATIONS_RELATIONS_API = {
    0: 'invenio_pidrelations.api:PIDConceptOrdered',
    1: 'invenio_pidrelations.api:PIDConcept',
    2: 'invenio_pidrelations.contrib.versioning:PIDVersioning',
}

PIDRELATIONS_PRIMARY_PID_TYPE = 'recid'
"""Default PID type for relations."""

PIDRELATIONS_INDEX_RELATIONS = True
"""Enable or disable relations indexing."""
