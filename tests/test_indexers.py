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

"""Test indexers."""

from __future__ import absolute_import, print_function

# from invenio_indexer.tasks import process_bulk_queue
from invenio_search import current_search_client

from invenio_pidrelations.api import PIDConceptOrdered


def test_indexers(app, indexed_records, pids):
    """Test that the default indexer correctly index version relations."""
    hits = current_search_client.search()['hits']['hits']
    for name, record in indexed_records.items():
        pid = pids[name]
        hit = next(hit for hit in hits
                   if hit['_source']['recid'] == pid.pid_value)
        relations = hit['_source']['relations']
        pc_api = PIDConceptOrdered(child=pid)
        assert len(relations['ordered']) == 1
        assert relations['ordered'][0]['parent']['pid_value'] == \
            pc_api.parent.pid_value
        assert relations['ordered'][0]['is_last'] == \
            pc_api.is_last_child
