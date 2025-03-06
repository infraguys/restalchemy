# Copyright 2022 George Melikov
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from restalchemy.common import utils
from restalchemy.storage.sql import engines
from restalchemy.tests.functional import consts


class DBEngineMixin(object):

    __ENGINE__ = None

    @utils.classproperty
    def engine(cls):
        return cls.__ENGINE__

    @classmethod
    def init_engine(cls):
        engines.engine_factory.configure_factory(db_url=consts.DATABASE_URI)
        cls.__ENGINE__ = engines.engine_factory.get_engine()

    @classmethod
    def destroy_engine(cls):
        # Note(efrolov): Must be deleted otherwise we will start collect
        #                connections and get an error "too many connections"
        #                from MySQL
        del cls.__ENGINE__
        engines.engine_factory.destroy_engine()

    @classmethod
    def get_all_tables(cls, session=None):
        with cls.engine.session_manager(session=session) as s:
            if session.engine.dialect.name == "mysql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.tables
                    where table_schema = database();
                """
                ).fetchall()
            elif session.engine.dialect.name == "postgresql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.tables
                    where table_schema = current_schema();
                """
                ).fetchall()
            else:
                raise NotImplementedError("Unsupported dialect")
        tables = {row["table_name"] for row in res}
        return tables

    @classmethod
    def is_table_exists(cls, table_name, session=None):
        with cls.engine.session_manager(session=session) as s:
            tables = cls.get_all_tables(session=s)
        res = table_name in tables
        return res

    @classmethod
    def drop_table(cls, table_name, session=None, cascade=False):
        cascade = " CASCADE" if cascade else ""
        with cls.engine.session_manager(session=session) as s:
            s.execute(
                f"drop table if exists {session.engine.escape(table_name)}{cascade}"
            )

    @classmethod
    def truncate_table(cls, table_name, session=None):
        with cls.engine.session_manager(session=session) as s:
            s.execute(f"truncate table {session.engine.escape(table_name)}")

    @classmethod
    def drop_all_tables(cls, session=None, cascade=False):
        with cls.engine.session_manager(session=session) as s:
            tables = cls.get_all_tables(session=s)
            for table in tables:
                cls.drop_table(table, session=s, cascade=cascade)

    @classmethod
    def get_all_views(cls, session=None):
        with cls.engine.session_manager(session=session) as s:
            if session.engine.dialect.name == "mysql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = database();
                """
                ).fetchall()
            elif session.engine.dialect.name == "postgresql":
                res = s.execute(
                    """
                    select
                        table_name as table_name
                    from information_schema.views
                    where table_schema = current_schema();
                """
                ).fetchall()
            else:
                raise NotImplementedError("Unsupported dialect")
        return {row["table_name"] for row in res}

    @classmethod
    def drop_all_views(cls, session=None):
        with cls.engine.session_manager(session=session) as s:
            views = cls.get_all_views(session=s)
            for view in views:
                cls.drop_view(view, session=s)

    @classmethod
    def drop_view(cls, view_name, session=None):
        with cls.engine.session_manager(session=session) as s:
            s.execute(
                f"drop view if exists {session.engine.escape(view_name)}"
            )
