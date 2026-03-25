.. image:: https://github.com/infraguys/restalchemy/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/infraguys/restalchemy/actions/workflows/tests.yml
.. image:: https://img.shields.io/pypi/pyversions/restalchemy
   :target: https://img.shields.io/pypi/pyversions/restalchemy
.. image:: https://img.shields.io/pypi/dm/restalchemy
   :target: https://img.shields.io/pypi/dm/restalchemy

|

RESTAlchemy
============

RESTAlchemy is a Python toolkit for building HTTP REST APIs on top of a flexible data model and storage abstraction.

It combines:

- A **Data Model (DM)** layer for defining domain models and validation.
- A **Storage** layer for persisting models (for example, SQL databases).
- An **API** layer for exposing models as RESTful HTTP resources.
- Optional **OpenAPI** support for discoverable, documented APIs.


Features
--------

- Clear separation between domain models, storage implementation details, and HTTP API.
- Strongly typed, validated data model with reusable properties.
- Minimal boilerplate to expose models as REST resources.
- Built-in migration tooling for evolving database schemas.


Documentation
-------------

All documentation is available in four languages. The structure of files and sections is identical across languages:

- English: `docs/en/index.md <docs/en/index.md>`_
- Russian: `docs/ru/index.md <docs/ru/index.md>`_
- German: `docs/de/index.md <docs/de/index.md>`_
- Chinese: `docs/zh/index.md <docs/zh/index.md>`_

If you are new to RESTAlchemy, start with:

- `Installation <docs/en/installation.md>`_
- `Getting started <docs/en/getting-started.md>`_


Quick start
-----------

Install from PyPI:

.. code-block:: bash

   pip install restalchemy

Define a simple DM model (simplified from the getting started guide):

.. code-block:: python

   from restalchemy.dm import models
   from restalchemy.dm import properties
   from restalchemy.dm import types


   class FooModel(models.ModelWithUUID):
       value = properties.property(types.Integer(), required=True)


For a complete in-memory REST service example, including controllers, routes and a WSGI application, see
`docs/en/getting-started.md <docs/en/getting-started.md>`_.


Examples
--------

Real code examples live in the ``examples/`` directory:

- ``examples/restapi_foo_bar_service.py`` – a simple REST API service built with in-memory storage.
- ``examples/dm_mysql_storage.py`` – data model with MySQL storage example.
- ``examples/openapi_app.py`` – example API with OpenAPI specification generation.


Migration commands
------------------

RESTAlchemy provides command-line tools for managing database migrations.

.. warning::
  New naming scheme is implemented for migration file names. The old naming scheme is supported as well.
  Recommended new file name format:

::

  <migration number>-<message>-<hash>.py

.. note::

  In order to rename the migration files for the new naming scheme, please use the following command:

::

  $ ra-rename-migrations -p <path-to-migrations>

Create migrations:

.. warning::
    Auto migration should not depend on manual one.

::

  $ ra-new-migration --path examples/migrations/ --message "1st migration"
  $ ra-new-migration --path examples/migrations/ --message "2st migration" --depend 1st
  $ ra-new-migration --path examples/migrations/ --message "3st migration" --depend 2st
  $ ra-new-migration --path examples/migrations/ --message "4st migration"
  $ ra-new-migration --path examples/migrations/ --message "5st migration" --depend 3st --depend 4st

.. note::
    You can create MANUAL migrations using --manual parameter

    $ ra-new-migration --path examples/migrations/ --message "manual migration" --manual


Apply migrations:

::

  $ ra-apply-migration --path examples/migrations/ --db-connection mysql://test:test@localhost/test -m 5st
  > upgrade 1st
  > upgrade 2st
  > upgrade 3st
  > upgrade 4st
  > upgrade 5st

.. note::
    If you want to apply the latest migration, run ``ra-apply-migration`` without the ``-m`` parameter.

    $ ra-apply-migration --path examples/migrations/ --db-connection mysql://test:test@localhost/test

    If it is impossible to find the latest migration, the tool will crash with the error
    "Head migration for current migrations couldnt be found".


Rolled back migrations:

::

  $ ra-rollback-migration --path examples/migrations/ --db-connection mysql://test:test@localhost/test -m 4st
  > downgrade 5st
  > downgrade 4st

::

  $ ra-rollback-migration --path examples/migrations/ --db-connection mysql://test:test@localhost/test -m 1st
  > downgrade 3st
  > downgrade 2st
  > downgrade 1st


Tests
-----

Tests are managed via ``tox``. The default environment list includes Python 3.8, 3.10, 3.12 and 3.13.

Run the full test suite:

.. code-block:: bash

   tox

Run tests for a specific Python version (for example, Python 3.10):

.. code-block:: bash

   tox -e py310

Run functional tests (require access to a MySQL database):

.. code-block:: bash

   export DATABASE_URI="mysql://root:@localhost:3306/radatabase"
   tox -e py310-functional

Run functional tests with PostgreSQL:

.. code-block:: bash

   export DATABASE_URI="postgresql://postgres:password@localhost:5432/radatabase"
   tox -e py310-functional


License
-------

RESTAlchemy is licensed under the Apache License, Version 2.0.

Copyright (c) Genesis Corporation, 2025.

See the ``LICENSE`` file in this repository or
https://www.apache.org/licenses/LICENSE-2.0 for the full license text.
