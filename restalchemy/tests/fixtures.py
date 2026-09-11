# Copyright 2019 Eugene Frolov
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

import mock


class DialectFixture(mock.Mock):
    @property
    def name(self):
        return "mysql"


class EngineFixture(mock.Mock):
    def escape(self, value):
        return f"`{value}`"

    @property
    def dialect(self):
        return DialectFixture()


class SessionFixture(mock.Mock):
    @property
    def engine(self):
        # One engine for the life of the session. An engine whose
        # identity changed on every access is not something a caller
        # could hold on to, and anything keyed by it would miss every
        # time.
        engine = self.__dict__.get("_engine_fixture")
        if engine is None:
            engine = EngineFixture()
            self.__dict__["_engine_fixture"] = engine
        return engine

    @engine.setter
    def engine(self, value):
        pass
