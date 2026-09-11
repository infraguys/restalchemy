#    Copyright 2026 Genesis Corporation.
#
#    All Rights Reserved.
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

"""What a resource may resolve once and hand to more than one request.

A resource resolves its fields for a request and keeps the answer for
every other request that would be told the same. These are the requests
that must not be told the same.
"""

import itertools

import mock
import webob

from restalchemy.api import constants
from restalchemy.api import contexts
from restalchemy.api import field_permissions as fp
from restalchemy.api import packers
from restalchemy.api import resources
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.tests.unit import base


class VisibilityModel(models.ModelWithUUID):
    name = properties.property(types.String(), default="n")
    secret = properties.property(types.String(), default="s")
    other = properties.property(types.String(), default="o")


class WideModel(models.ModelWithUUID):
    """Enough fields that a caller can name more projections than are kept."""

    for _number in range(8):
        vars()["field%d" % _number] = properties.property(types.String(), default="v")
    del _number


def request_for(method=constants.GET, roles=(), fields=()):
    query = "&".join("fields=%s" % name for name in fields)
    req = webob.Request.blank("/things/" + ("?" + query if query else ""))
    req.api_context = contexts.RequestContext(req)
    req.api_context.set_active_method(method)
    req.context = mock.Mock(roles=list(roles))
    return req


def packed_names(resource, req):
    packer = packers.BaseResourcePacker(resource, req)
    return sorted(name for name, _, _ in packer._get_visible_fields())


class FieldVisibilityTestCase(base.BaseTestCase):
    def tearDown(self):
        super(FieldVisibilityTestCase, self).tearDown()
        resources.ResourceMap.model_type_to_resource = {}


class MethodTestCase(FieldVisibilityTestCase):
    def setUp(self):
        super(MethodTestCase, self).setUp()
        self.resource = resources.ResourceByRAModel(
            VisibilityModel,
            hidden_fields=resources.HiddenFieldMap(
                get=["secret"],
                filter=["other"],
            ),
        )

    def test_each_method_is_told_what_it_hides(self):
        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(self.resource, request_for(constants.GET)),
        )
        self.assertEqual(
            ["name", "secret", "uuid"],
            packed_names(self.resource, request_for(constants.FILTER)),
        )
        # ...and the first answer is not what the second one gets, nor
        # the other way round when the same pair runs again.
        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(self.resource, request_for(constants.GET)),
        )

    def test_permissions_are_asked_per_method_too(self):
        resource = resources.ResourceByRAModel(
            VisibilityModel,
            fields_permissions=fp.FieldsPermissions(
                default=fp.Permissions.RW,
                fields={"secret": {constants.GET: fp.Permissions.HIDDEN}},
            ),
        )

        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(constants.GET)),
        )
        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(constants.FILTER)),
        )


class RoleTestCase(FieldVisibilityTestCase):
    def test_roles_choose_the_hidden_fields(self):
        resource = resources.ResourceByRAModel(
            VisibilityModel,
            hidden_fields=resources.RoleBasedHiddenFieldContainer(
                default=resources.HiddenFieldMap(get=["secret"]),
                admin=resources.HiddenFieldMap(get=[]),
            ),
        )

        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(roles=["user"])),
        )
        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(roles=["admin"])),
        )
        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(roles=["user"])),
        )

    def test_roles_choose_the_permissions(self):
        resource = resources.ResourceByRAModel(
            VisibilityModel,
            fields_permissions=fp.FieldsPermissionsByRole(
                default=fp.UniversalPermissions(permission=fp.Permissions.RW),
                admin=fp.FieldsPermissions(
                    default=fp.Permissions.RW,
                    fields={"secret": {constants.ALL: fp.Permissions.HIDDEN}},
                ),
            ),
        )

        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(roles=["user"])),
        )
        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(roles=["admin"])),
        )
        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(roles=["user"])),
        )

    def _by_role_resource(self):
        """A resource where two roles answer differently about `secret`."""
        return resources.ResourceByRAModel(
            VisibilityModel,
            fields_permissions=fp.FieldsPermissionsByRole(
                default=fp.UniversalPermissions(permission=fp.Permissions.RW),
                hide=fp.FieldsPermissions(
                    default=fp.Permissions.RW,
                    fields={"secret": {constants.ALL: fp.Permissions.HIDDEN}},
                ),
                show=fp.UniversalPermissions(permission=fp.Permissions.RW),
            ),
        )

    def test_the_order_of_the_roles_decides_and_is_not_shared_away(self):
        # The first role a request carries that the resource was told
        # about is the one that answers, so these two are not the same
        # request even though they carry the same two roles.
        resource = self._by_role_resource()

        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(roles=["hide", "show"])),
        )
        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(roles=["show", "hide"])),
        )

    def test_the_order_decides_whichever_request_comes_first(self):
        resource = self._by_role_resource()

        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(resource, request_for(roles=["show", "hide"])),
        )
        self.assertEqual(
            ["name", "other", "uuid"],
            packed_names(resource, request_for(roles=["hide", "show"])),
        )

    def test_roles_the_resource_was_not_told_about_are_not_part_of_it(self):
        # Only the role that wins decides, so a request carrying others
        # before it is told the same thing -- and may share the answer.
        resource = self._by_role_resource()
        plain = request_for(roles=["hide"])
        padded = request_for(roles=["stranger", "hide"])

        self.assertEqual(
            resource.resolve_visibility(plain),
            resource.resolve_visibility(padded),
        )
        self.assertEqual(packed_names(resource, plain), packed_names(resource, padded))

    def test_a_flood_of_roles_does_not_grow_without_bound(self):
        resource = resources.ResourceByRAModel(
            VisibilityModel,
            hidden_fields=resources.RoleBasedHiddenFieldContainer(
                default=resources.HiddenFieldMap(get=["secret"]),
            ),
        )

        for number in range(resource._MAX_VISIBILITY_CACHES * 3):
            self.assertEqual(
                ["name", "other", "uuid"],
                packed_names(resource, request_for(roles=["role-%d" % number])),
            )

        self.assertLessEqual(
            len(resource._visibility_caches),
            resource._MAX_VISIBILITY_CACHES,
        )


class ProjectionTestCase(FieldVisibilityTestCase):
    def setUp(self):
        super(ProjectionTestCase, self).setUp()
        self.resource = resources.ResourceByRAModel(VisibilityModel)

    def test_a_projection_narrows_only_the_request_that_asked(self):
        self.assertEqual(
            ["name"],
            packed_names(self.resource, request_for(fields=["name"])),
        )
        self.assertEqual(
            ["name", "other", "secret", "uuid"],
            packed_names(self.resource, request_for()),
        )
        self.assertEqual(
            ["other"],
            packed_names(self.resource, request_for(fields=["other"])),
        )

    def test_a_projection_is_kept_for_the_ones_that_asked_for_it(self):
        # The projection is part of what a request is told, so two asking
        # for the same one share a resolution and neither shares with a
        # request that asked for none.
        packed_names(self.resource, request_for(fields=["name"]))
        packed_names(self.resource, request_for(fields=["name"]))
        self.assertEqual(1, len(self.resource._visibility_caches))

        packed_names(self.resource, request_for())
        self.assertEqual(2, len(self.resource._visibility_caches))


class DecidesItsOwnWayTestCase(FieldVisibilityTestCase):
    """A container of one's own is reused, and told apart, like any other.

    What a resource keeps its resolved fields by is what the containers
    answered, so a container written downstream needs to say nothing
    about itself: its answers are the key.
    """

    def test_a_hidden_fields_map_of_its_own(self):
        class ByRole(resources.BaseHiddenFieldsMap):
            def hidden_for(self, req, field_names):
                if "show" in req.context.roles:
                    return frozenset()
                return frozenset({"secret"}.intersection(field_names))

        resource = resources.ResourceByRAModel(VisibilityModel, hidden_fields=ByRole())

        self.assertIn("secret", packed_names(resource, request_for(roles=["show"])))
        self.assertNotIn("secret", packed_names(resource, request_for()))
        self.assertIn("secret", packed_names(resource, request_for(roles=["show"])))
        self.assertEqual(2, len(resource._visibility_caches))

    def test_permissions_of_its_own(self):
        class ByRole(fp.BasePermissions):
            def resolve(self, req, field_names):
                allowed = "show" in req.context.roles
                return {
                    name: (
                        fp.Permissions.RW
                        if name != "secret" or allowed
                        else fp.Permissions.HIDDEN
                    )
                    for name in field_names
                }

        resource = resources.ResourceByRAModel(
            VisibilityModel, fields_permissions=ByRole()
        )

        self.assertIn("secret", packed_names(resource, request_for(roles=["show"])))
        self.assertNotIn("secret", packed_names(resource, request_for()))
        self.assertIn("secret", packed_names(resource, request_for(roles=["show"])))
        self.assertEqual(2, len(resource._visibility_caches))

    def test_a_request_context_of_its_own(self):
        class PickyContext(contexts.RequestContext):
            def shown_fields(self, resource_field_names):
                return frozenset(
                    name for name in resource_field_names if name != "secret"
                )

        resource = resources.ResourceByRAModel(VisibilityModel)

        def picky():
            req = request_for()
            req.api_context = PickyContext(req)
            req.api_context.set_active_method(constants.GET)
            return req

        self.assertNotIn("secret", packed_names(resource, picky()))
        self.assertIn("secret", packed_names(resource, request_for()))
        self.assertNotIn("secret", packed_names(resource, picky()))

    def test_the_shipped_maps_are_reused(self):
        resource = resources.ResourceByRAModel(
            VisibilityModel, hidden_fields=["secret"]
        )

        packed_names(resource, request_for())
        packed_names(resource, request_for())

        self.assertEqual(1, len(resource._visibility_caches))


class ARemovedHookIsRefusedTestCase(FieldVisibilityTestCase):
    """A class written against the old hooks does not run half-answered.

    Each hook has a replacement that answers for every field at once.
    Where the replacement's own answer is the permissive one, a class
    still writing the old name would be passed over in silence and the
    base would show what that class was hiding.
    """

    def test_a_hidden_fields_map_still_writing_the_old_hook(self):
        with self.assertRaises(TypeError):

            class Old(resources.BaseHiddenFieldsMap):
                def is_hidden_field(self, model_field_name, req):
                    return model_field_name == "secret"

    def test_a_hidden_fields_map_still_writing_the_old_method_hook(self):
        with self.assertRaises(TypeError):

            class Old(resources.BaseHiddenFieldsMap):
                def is_hidden_field_by_method(self, model_field_name, method):
                    return model_field_name == "secret"

    def test_a_request_context_still_writing_the_old_hook(self):
        with self.assertRaises(TypeError):

            class Old(contexts.RequestContext):
                def can_be_shown_field(self, resource_field_name):
                    return resource_field_name != "secret"

    def test_permissions_still_writing_the_old_hook(self):
        with self.assertRaises(TypeError):

            class Old(fp.BasePermissions):
                def meets_field_permission(
                    self, model_field_name, req, current_permission
                ):
                    return True

    def test_a_container_still_describing_its_answers(self):
        with self.assertRaises(TypeError):

            class Old(fp.BasePermissions):
                def resolve(self, req, field_names):
                    return {name: fp.Permissions.RW for name in field_names}

                def visibility_key(self, req):
                    return ()

    def test_the_name_it_asks_for_is_the_one_that_works(self):
        class New(resources.BaseHiddenFieldsMap):
            def hidden_for(self, req, field_names):
                return frozenset({"secret"}.intersection(field_names))

        resource = resources.ResourceByRAModel(VisibilityModel, hidden_fields=New())

        self.assertEqual(
            ["name", "other", "uuid"], packed_names(resource, request_for())
        )


class VisibilityCacheTestCase(FieldVisibilityTestCase):
    def test_a_flood_of_projections_does_not_cost_the_requests_without_one(self):
        # `fields` is the caller's to pick, so a stream of projections
        # nobody asks for twice must not take the room a plain request
        # keeps coming back to.
        resource = resources.ResourceByRAModel(WideModel)
        plain = resource.resolve_visibility(request_for())
        kept = resource.request_cache(plain)
        kept["fields"] = "resolved once"

        projections = itertools.combinations(WideModel.properties.properties, 2)
        for number, projection in enumerate(projections):
            if number >= resource._MAX_VISIBILITY_CACHES * 3:
                break
            packed_names(resource, request_for(fields=projection))
            self.assertIs(kept, resource.request_cache(plain))

        self.assertLessEqual(
            len(resource._visibility_caches),
            resource._MAX_VISIBILITY_CACHES,
        )


class SpecTestCase(FieldVisibilityTestCase):
    """What the OpenAPI schema of a role-guarded resource carries.

    The schema is built for a request carrying no roles, and asks the
    permissions about exactly that request. The hidden fields answer for
    the same one.
    """

    def _schema(self, hidden_fields):
        resource = resources.ResourceByRAModel(
            VisibilityModel, hidden_fields=hidden_fields
        )
        return resource.generate_schema_object(constants.GET, "3.0.3")

    def test_a_role_guarded_resource_still_has_properties(self):
        schema = self._schema(
            resources.RoleBasedHiddenFieldContainer(
                default=resources.HiddenFieldMap(get=["secret"]),
                admin=resources.HiddenFieldMap(get=[]),
            )
        )

        self.assertEqual(["name", "other", "uuid"], sorted(schema["properties"]))

    def test_what_only_a_role_may_see_is_not_in_a_spec_anyone_may_read(self):
        schema = self._schema(
            resources.RoleBasedHiddenFieldContainer(
                default=resources.HiddenFieldMap(get=["secret", "other"]),
                admin=resources.HiddenFieldMap(get=["other"]),
            )
        )

        self.assertEqual(["name", "uuid"], sorted(schema["properties"]))
