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

"""Schema tests."""

from marshmallow import Schema, fields

from invenio_pidrelations.serializers.schemas import RelationsSchema


class SampleRecordSchema(Schema):
    """Sample record schema."""

    relations = fields.Nested(RelationsSchema)


def test_schema(app, pids):
    schema = SampleRecordSchema(strict=True)

    siblings = [pids['h1v1'].pid_value,
                pids['h1v2'].pid_value,
                pids['h1v3'].pid_value]

    parent = pids['h1'].pid_value

    pid = pids['h1v1']
    input_data = {'pid': pid, 'relations': {'version': {}}}
    schema.context['pid'] = pid
    data, errors = schema.dump(input_data)
    assert not errors
    assert data == {
        u'relations': {
            u'version': {
                u'order': 0,
                u'parent': parent,
                u'siblings': siblings,
                u'next': pids['h1v2'].pid_value,
                u'prev': None,
                u'is_first': True,
                u'is_last': False,
            },
        }
    }

    pid = pids['h1v2']
    input_data = {'pid': pid, 'relations': {'version': {}}}
    schema.context['pid'] = pid
    data, errors = schema.dump(input_data)
    assert not errors
    assert data == {
        u'relations': {
            u'version': {
                u'order': 1,
                u'parent': parent,
                u'siblings': siblings,
                u'next': pids['h1v3'].pid_value,
                u'prev': pids['h1v1'].pid_value,
                u'is_first': False,
                u'is_last': False,
            },
        }
    }

    pid = pids['h1v3']
    input_data = {'pid': pid, 'relations': {'version': {}}}
    schema.context['pid'] = pid
    data, errors = schema.dump(input_data)
    assert not errors
    assert data == {
        u'relations': {
            u'version': {
                u'order': 2,
                u'parent': parent,
                u'siblings': siblings,
                u'next': None,
                u'prev': pids['h1v2'].pid_value,
                u'is_first': False,
                u'is_last': True,
            },
        }
    }
