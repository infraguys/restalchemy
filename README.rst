.. image:: https://github.com/infraguys/restalchemy/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/infraguys/restalchemy/actions/workflows/tests.yml
.. image:: https://img.shields.io/pypi/pyversions/restalchemy
   :target: https://img.shields.io/pypi/pyversions/restalchemy
.. image:: https://img.shields.io/pypi/dm/restalchemy
   :target: https://img.shields.io/pypi/dm/restalchemy

|

REST Alchemy
============

The Python REST HTTP Toolkit and Object Relational Mapper.



Migration commands
------------------

.. warning::
  New naming scheme is implemented for migration file names. The old naming scheme is supported as well.
  Recommended new file name format:

::

  <migration number>-<message>-<hash>.py

.. Note::

  In order to rename the migration files for the new naming scheme, please use the following command:

::

  $ ra-rename-migrations  -p <path-to-migrations>

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
    if you want to apply the latest migration run ra-apply-migration without -m parameter

    $ ra-apply-migration --path examples/migrations/ --db-connection mysql://test:test@localhost/test

    if it is impossible to find the latests migration, the tool will crash with the error
    "Head migration for current migrations couldnt be found"

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

Run tests for python 2.7

::

  $ tox -e py27


Run functional tests (python 2.7)

::

  $ export DATABASE_URI="mysql://test:test@localhost/test"
  $ tox -e functional
