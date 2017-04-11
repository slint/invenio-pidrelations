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

"""Records integration for PIDRelations."""

from functools import wraps

from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PersistentIdentifier, PIDStatus, \
    RecordIdentifier
from invenio_records_files.models import RecordsBuckets
from marshmallow import fields

from ..api import PIDConcept
from ..contrib.versioning import PIDVersioning
from ..models import PIDRelation
from ..serializers.schemas import RelationSchema
from ..utils import resolve_relation_type_config


## TODO: To be removed, done manually in minters
def default_parent_minter(record_uuid, data, pid_type, object_type):
    """Basic RecordIdentifier-based minter for parent PIDs."""
    parent_id = RecordIdentifier.next()
    return PersistentIdentifier.create(
        pid_type=pid_type,
        pid_value=str(parent_id),
        object_type=object_type,
        status=PIDStatus.REGISTERED,
    )


## TODO: To be removed, done manually in minters
def versioned_minter(pid_type='recid', object_type='rec', parent_minter=None):
    """Parameterized minter decorator for automatic versioning.

    This decorator can be applied to any minter function. in order to introduce
    record versioning through the `relations` metadata key.
    """
    parent_minter = parent_minter or default_parent_minter

    def decorator(child_minter):
        @wraps(child_minter)
        def wrapper(record_uuid=None, data=None):
            parent = (data.get('relations', {}).get('version', {})
                      .get('parent'))
            if not parent:
                # Not yet versioned, create parent PID
                parent_pid = parent_minter(record_uuid, data, pid_type,
                                           object_type)
                data['relations'] = {
                    'version': {'parent': parent_pid.pid_value}
                }
            else:
                parent_pid = PersistentIdentifier.get(
                    pid_type=pid_type, pid_value=parent)

            # Call the decorated minter to get the new PID
            pid = child_minter(record_uuid, data)

            versioning = PIDVersioning(parent=parent_pid)
            versioning.insert_child(child=pid)
            return pid
        return wrapper
    return decorator


class RecordDraft(PIDConcept):
    """Record Draft relationship.

    Users of this class should make calls to `link` and `unlink` based on their
    specific use-cases. Typical scenario is that of creating a new Deposit
    which is linked to a not-yet published record PID (PID status is RESERVED).
    Linking these two makes it possible for creating new record versions and
    having the abiltiy to track their deposits.

    NOTE: This relation exists because usually newly created records are not
    immediately stored inside the database (they have no `RecordMetada`). This
    leads to having deposits that are hanging onto no actual record and only
    possess "soft" links to their records' PIDs through metadata.
    """

    def __init__(self, child=None, parent=None, relation=None):
        """Create a Record Draft API."""
        self.relation_type = resolve_relation_type_config('record_draft').id
        if relation is not None:
            if relation.relation_type != self.relation_type:
                raise ValueError('Provided PID relation ({0}) is not a '
                                 'version relation.'.format(relation))
            super(RecordDraft, self).__init__(relation=relation)
        else:
            super(RecordDraft, self).__init__(
                child=child, parent=parent, relation_type=self.relation_type,
                relation=relation)

    @classmethod
    def link(cls, recid, depid):
        """Link a recid and depid."""
        recid_api = cls(parent=recid)
        depid_api = cls(child=depid)
        if recid_api.has_children:
            raise Exception('Recid {} already has a depid as a draft.'
                            .format(recid))
        if depid_api.parent:
            raise Exception('Depid {} already is a draft of a recid.'
                            .format(recid))
        recid_api.insert_child(depid)

    @classmethod
    def unlink(cls, recid, depid):
        """Unlink a recid and depid."""
        return cls(parent=recid).remove_child(depid)

    @classmethod
    def get_draft(cls, recid):
        """Get the draft of a record."""
        return cls(parent=recid).children.one_or_none()

    @classmethod
    def get_recid(cls, depid):
        """Get the recid of a record."""
        return cls(child=depid).parent


class PIDRecordVersioning(PIDVersioning):
    """Record-aware PID versioning API."""

    @property
    def draft_child(self):
        """Get the last non-registered child."""
        return self.get_children(ordered=False).filter(
                PIDRelation.index.isnot(None),
                PersistentIdentifier.status != PIDStatus.REGISTERED).order_by(
                    PIDRelation.index.desc()).one_or_none()

    @property
    def draft_child_deposit(self):
        """Get last non-registered child's linked depid."""
        return RecordDraft.get_draft(self.draft_child)

    def insert_draft_child(self, child, index=-1):
        """Insert child into versioning scheme as draft."""
        assert child.status != PIDStatus.REGISTERED
        if not self.draft_child:
            with db.session.begin_nested():
                super(PIDVersioning, self).insert_child(child, index=index)
        else:
            raise Exception(
                "Draft child already exists for this relation: {0}".format(
                    self.draft_child))

    def remove_draft_child(self):
        """Remove the draft child from a versioning scheme."""
        if self.draft_child:
            with db.session.begin_nested():
                super(PIDVersioning, self).remove_child(self.draft_child,
                                                        reorder=True)


def get_latest_draft(recid_pid):
    """Return the latest draft for a record."""
    pv = PIDVersioning(child=recid_pid)
    if pv.draft_child:
        last_deposit = RecordDraft.get_draft(pv.draft_child)
    else:
        last_deposit = None
    return pv.last_child, last_deposit


## TODO: To be removed
def clone_record_files(src_record, dst_record):
    """Create copy a record's files."""
    # NOTE `Bucket.snapshot` doesn't set `locked`
    snapshot = src_record.files.bucket.snapshot(lock=False)
    snapshot.locked = False

    RecordsBuckets.create(record=dst_record.model, bucket=snapshot)

    dst_record['_files'] = dst_record.files.dumps()
    dst_record['_buckets'] = {'deposit': str(snapshot.id)}


def index_siblings(pid, only_neighbors=False):
    """Send sibling records of the passed pid for indexing."""
    siblings = (PIDVersioning(child=pid).children.all())

    index_pids = siblings
    if only_neighbors:
        pid_index = siblings.index(pid)
        index_pids = siblings[(pid_index - 1):(pid_index + 2)]
    for p in index_pids:
        if p != pid:
            RecordIndexer().index_by_id(str(p.object_uuid))


class RecordVersionRelationSchema(RelationSchema):
    """PID version relation schema."""

    last_child = fields.Method('dump_last_child')
    last_draft = fields.Method('dump_last_draft')
    last_draft_deposit = fields.Method('dump_last_draft_deposit')

    def dump_last_child(self, obj):
        """Dump the last child."""
        if obj.is_ordered:
            return self._dump_relative(obj.last_child)

    def dump_last_draft(self, obj):
        """Dump the last non-registered PID."""
        return self._dump_relative(obj.draft_child)

    def dump_last_draft_deposit(self, obj):
        """Dump the last non-registered recid's deposit PID."""
        return self._dump_relative(obj.draft_child_deposit)
