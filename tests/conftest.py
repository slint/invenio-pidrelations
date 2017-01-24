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

"""Pytest configuration."""

from __future__ import absolute_import, print_function

import shutil
import os
import tempfile

import pytest
from flask import Flask
from flask_babelex import Babel
from invenio_db import InvenioDB, db as db_
from invenio_pidstore import InvenioPIDStore
from invenio_pidrelations import InvenioPIDRelations

from sqlalchemy_utils.functions import create_database, database_exists
from invenio_pidrelations.models import PIDRelation, RelationType
from invenio_pidstore.models import PersistentIdentifier


@pytest.yield_fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    """Flask application fixture."""
    app_ = Flask('testapp', instance_path=instance_path)
    app_.config.update(
        SECRET_KEY='SECRET_KEY',
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        TESTING=True,
    )
    InvenioPIDStore(app_)
    InvenioPIDRelations(app_)
    InvenioDB(app_)
    Babel(app_)
    return app_


@pytest.yield_fixture()
def app(base_app):
    """Flask application fixture."""
    with base_app.app_context():
        yield base_app


@pytest.yield_fixture()
def db(app):
    """Database fixture."""
    if not database_exists(str(db_.engine.url)):
        create_database(str(db_.engine.url))
    db_.create_all()
    yield db_
    db_.session.remove()
    db_.drop_all()


@pytest.fixture()
def pids(db):
    """Test PIDs fixture."""
    # TODO: Head PIDs do not have redirects as they are created outside API
    h1 = PersistentIdentifier.create('doi', 'foobar', object_type='rec')
    h1v1 = PersistentIdentifier.create('doi', 'foobar.v1', object_type='rec')
    h1v2 = PersistentIdentifier.create('doi', 'foobar.v2', object_type='rec')
    PIDRelation.create(h1, h1v2, RelationType.VERSION, 1)
    PIDRelation.create(h1, h1v1, RelationType.VERSION, 0)

    h2 = PersistentIdentifier.create('doi', 'spam')
    h2v1 = PersistentIdentifier.create('doi', 'spam.v1')
    PIDRelation.create(h2, h2v1, RelationType.VERSION, 0)

    c1 = PersistentIdentifier.create('doi', 'collA')
    c1r1 = PersistentIdentifier.create('doi', 'res1')
    c1r2 = PersistentIdentifier.create('doi', 'res2')

    pid1 = PersistentIdentifier.create('doi', 'eggs')
    PIDRelation.create(c1, c1r1, RelationType.COLLECTION, None)
    PIDRelation.create(c1, c1r2, RelationType.COLLECTION, None)
    return {
        'h1': h1,
        'h1v1': h1v1,
        'h1v2': h1v2,
        'h2': h2,
        'h2v1': h2v1,
        'c1': c1,
        'c1r1': c1r1,
        'c1r2': c1r2,
        'pid1': pid1,
    }
