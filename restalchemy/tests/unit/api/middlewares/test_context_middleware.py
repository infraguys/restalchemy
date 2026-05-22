#    Copyright 2026 Genesis Corporation.
#    Copyright 2026 George Melikov.
#
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
import pytest

from restalchemy.api.middlewares import contexts
from restalchemy.storage.sql import engines


class TestIsReadonlyRequest:
    @pytest.fixture(autouse=True)
    def setup_middleware(self):
        self._middleware = None

    def _make_middleware(self, readonly_whitelist=None):
        app = mock.Mock()
        self._middleware = contexts.ContextMiddleware(
            application=app,
            readonly_whitelist=readonly_whitelist,
        )

    def _make_request(self, method="GET", path="/v1/resources"):
        req = mock.Mock()
        req.method = method
        req.path = path
        return req

    @pytest.mark.parametrize(
        "readonly_whitelist,method,path,expected",
        [
            (None, "GET", "/v1/resources", False),
            ({}, "GET", "/v1/resources", False),
            ({"GET": r"^/v1/.*"}, "GET", "/v1/resources", True),
            ({"GET": r"^/v1/.*"}, "GET", "/v2/resources", False),
            ({"GET": r"^/v1/.*"}, "POST", "/v1/resources", False),
            ({"GET": r"^/v1/.*", "POST": r"^/v2/.*"}, "GET", "/v1/resources", True),
            ({"GET": r"^/v1/.*", "POST": r"^/v2/.*"}, "POST", "/v2/resources", True),
            ({"DELETE": r"^/v1/.*"}, "DELETE", "/v1/resources/123", True),
            ({"GET": [r"^/v1/.*", r"^/api/.*"]}, "GET", "/v1/resources", True),
            ({"GET": [r"^/v1/.*", r"^/api/.*"]}, "GET", "/api/other", True),
            ({"GET": [r"^/v1/.*", r"^/api/.*"]}, "GET", "/v2/resources", False),
        ],
        ids=[
            "no_whitelist",
            "empty_whitelist",
            "matching_method_and_path",
            "matching_method_wrong_path",
            "wrong_method_matching_path",
            "multiple_rules_first_match",
            "multiple_rules_second_match",
            "delete_method_matching",
            "list_of_patterns_first_match",
            "list_of_patterns_second_match",
            "list_of_patterns_no_match",
        ],
    )
    def test_is_readonly_request(self, readonly_whitelist, method, path, expected):
        self._make_middleware(readonly_whitelist=readonly_whitelist)
        req = self._make_request(method=method, path=path)

        assert self._middleware._is_readonly_request(req) is expected


class TestConstructContext:
    def _make_middleware(self, readonly_whitelist=None, context_kwargs=None):
        from restalchemy.common import contexts as common_contexts

        app = mock.Mock()
        return contexts.ContextMiddleware(
            application=app,
            context_class=common_contexts.Context,
            context_kwargs=context_kwargs,
            readonly_whitelist=readonly_whitelist,
        )

    @mock.patch("restalchemy.storage.sql.engines.engine_factory")
    def test_readonly_context_set_on_matching_request(self, engine_factory_mock):
        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")
        mw._engine = mock.Mock()
        mock_session = mock.Mock()
        mock_storage = mock.Mock()
        mw._engine.get_session.return_value = mock_session
        mw._engine.get_session_storage.return_value = mock_storage
        req.context = mock.Mock()

        mw.process_request(req)

        assert req.context._is_readonly is True

    @mock.patch("restalchemy.storage.sql.engines.engine_factory")
    def test_readonly_context_not_set_on_non_matching_request(
        self, engine_factory_mock
    ):
        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "POST"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")
        mw._engine = mock.Mock()
        mock_session = mock.Mock()
        mock_storage = mock.Mock()
        mw._engine.get_session.return_value = mock_session
        mw._engine.get_session_storage.return_value = mock_storage
        req.context = mock.Mock()

        mw.process_request(req)

        assert req.context._is_readonly is False

    @mock.patch("restalchemy.storage.sql.engines.engine_factory")
    def test_no_whitelist_context_not_readonly(self, engine_factory_mock):
        mw = self._make_middleware(
            readonly_whitelist=None,
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")
        mw._engine = mock.Mock()
        mock_session = mock.Mock()
        mock_storage = mock.Mock()
        mw._engine.get_session.return_value = mock_session
        mw._engine.get_session_storage.return_value = mock_storage
        req.context = mock.Mock()

        mw.process_request(req)

        assert req.context._is_readonly is False


class TestReadonlyIntegration:
    """Integration tests for readonly replica support."""

    def _make_middleware(self, readonly_whitelist=None, context_kwargs=None):
        from restalchemy.common import contexts as common_contexts

        app = mock.Mock()
        return contexts.ContextMiddleware(
            application=app,
            context_class=common_contexts.Context,
            context_kwargs=context_kwargs,
            readonly_whitelist=readonly_whitelist,
        )

    def test_readonly_context_uses_readonly_engine(self):
        """Test that readonly context uses the readonly engine."""
        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")

        primary_engine = mock.Mock()
        readonly_engine = mock.Mock()

        def _get_engine(name=engines.DEFAULT_NAME):
            if name == "readonly":
                return readonly_engine
            return primary_engine

        with mock.patch.object(
            engines.engine_factory, "get_engine", side_effect=_get_engine
        ):
            with mock.patch.object(readonly_engine, "get_session") as mock_get_session:
                mock_session = mock.Mock()
                mock_storage = mock.Mock()
                mock_get_session.return_value = mock_session
                readonly_engine.get_session_storage.return_value = mock_storage

                _ = mw.process_request(req)

                readonly_engine.get_session.assert_called_once()
                primary_engine.get_session.assert_not_called()

    def test_readonly_session_skips_commit(self):
        """Test that readonly session skips commit."""
        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")

        mock_engine = mock.Mock()
        mock_session = mock.Mock()
        mock_storage = mock.Mock()
        mock_engine.get_session.return_value = mock_session
        mock_engine.get_session_storage.return_value = mock_storage

        with mock.patch.object(
            engines.engine_factory, "get_engine", return_value=mock_engine
        ):
            _ = mw.process_request(req)

            mock_session.commit.assert_not_called()

    def test_normal_session_commits(self):
        """Test that normal session commits."""
        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "POST"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")

        mock_engine = mock.Mock()
        mock_session = mock.Mock()
        mock_storage = mock.Mock()
        mock_engine.get_session.return_value = mock_session
        mock_engine.get_session_storage.return_value = mock_storage

        with mock.patch.object(
            engines.engine_factory, "get_engine", return_value=mock_engine
        ):
            _ = mw.process_request(req)

            mock_session.commit.assert_called_once()

    def test_get_readonly_engine(self):
        """Test that get_readonly_engine returns the readonly engine."""

        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")

        primary_engine = mock.Mock()
        readonly_engine = mock.Mock()

        def _get_engine(name=engines.DEFAULT_NAME):
            if name == "readonly":
                return readonly_engine
            return primary_engine

        with mock.patch.object(
            engines.engine_factory, "get_engine", side_effect=_get_engine
        ):
            _ = mw.process_request(req)

            ro_engine = req.context.get_readonly_engine()
            assert ro_engine is readonly_engine

    def test_get_readonly_engine_raises_when_not_configured(self):
        """Test that get_readonly_engine raises ValueError when not configured."""
        from restalchemy.common import contexts as common_contexts

        ctx = common_contexts.Context(
            engine_name=engines.DEFAULT_NAME,
            readonly_engine_name=None,
        )

        with pytest.raises(ValueError, match="Read-only engine is not configured"):
            ctx.get_readonly_engine()

    def test_get_readwrite_engine(self):
        """Test that get_readwrite_engine returns the primary engine."""

        mw = self._make_middleware(
            readonly_whitelist={"GET": r"^/v1/.*"},
            context_kwargs={"readonly_engine_name": "readonly"},
        )
        req = mock.Mock()
        req.method = "GET"
        req.path = "/v1/resources"
        req.get_response = mock.Mock(return_value="response")

        primary_engine = mock.Mock()
        readonly_engine = mock.Mock()

        def _get_engine(name=engines.DEFAULT_NAME):
            if name == "readonly":
                return readonly_engine
            return primary_engine

        with mock.patch.object(
            engines.engine_factory, "get_engine", side_effect=_get_engine
        ):
            _ = mw.process_request(req)

            rw_engine = req.context.get_readwrite_engine()
            assert rw_engine is primary_engine
