# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
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

import abc
import builtins
import collections
from collections import abc as collections_abc
import copy
import inspect

from restalchemy.common import exceptions as exc
from restalchemy.common import utils
from restalchemy.dm import types


class PropertyMeta(abc.ABCMeta):
    """Refuses `value` written onto a property *class*.

    A model built without its constructor has no properties of its own, so
    `self.properties` is still the class's collection — and what that yields
    for a name is the property *class*, not an instance of it. The write in
    `Model.__setattr__` then lands on the class, where it shadows the `value`
    descriptor for every property of every model in the process, including
    objects created afterwards. Nothing raised, and the damage showed up
    wherever somebody next read a model.

    Checked here rather than in `Model.__setattr__` because here it is free:
    this fires only on an assignment to a class object, which no working path
    does, while a property write on an instance never reaches it.
    """

    def __setattr__(cls, name, value):
        if name == "value":
            raise exc.PropertyClassAssignment()
        super().__setattr__(name, value)


class AbstractProperty(metaclass=PropertyMeta):
    @property
    @abc.abstractmethod
    def value(self):
        pass

    @abc.abstractmethod
    def set_value_force(self, value):
        pass

    @abc.abstractmethod
    def is_dirty(self):
        pass

    @classmethod
    def is_prefetch(cls):
        return False


class BaseProperty(AbstractProperty):
    pass


# `isinstance` against an abstract base walks the subclass machinery, and a
# property type is checked once per property per model built. The answer
# depends only on the type's class, so the classes that passed are
# remembered. Only passes are: a class can be registered with the base
# later, but never unregistered.
_verified_property_types = set()


def _check_property_type(property_type):
    property_type_class = type(property_type)
    if property_type_class in _verified_property_types:
        return
    if not isinstance(property_type, types.BaseType):
        raise TypeError("Property type must be instance of %s" % types.BaseType)
    _verified_property_types.add(property_type_class)


# Bumped whenever a declaration that was already readable changes -- which
# `sort_properties()` does. Anything that reads a model's properties once
# and builds from them (the SQL layer builds every query's column list
# that way) compares this against what it last saw, instead of the data
# model having to know who those readers are.
declaration_version = 0


class Property(BaseProperty):
    def __init__(
        self,
        property_type,
        default=None,
        required=False,
        read_only=False,
        value=None,
        mutable=False,
        example=None,
    ):
        _check_property_type(property_type)
        self._type = property_type
        self._required = bool(required)
        self._read_only = bool(read_only)
        if value is not None:
            self.set_value_force(value)
        elif callable(default):
            self.set_value_force(default())
        else:
            self.set_value_force(default)
        self._first_value = copy.deepcopy(self.value) if mutable else self.value
        self._example = example

    def is_dirty(self):
        return not self._first_value == self.value

    def _safe_value(self, value):
        if value is None or self._type.validate(value):
            if value is None and self.is_required():
                raise exc.PropertyRequired()
            return value
        else:
            raise exc.TypeError(value=value, property_type=self._type)

    def is_read_only(self):
        return self._read_only

    def is_required(self):
        return self._required

    @classmethod
    def is_id_property(cls):
        return False

    @builtins.property
    def old_value(self):
        return self._first_value

    @builtins.property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if self.is_read_only() or self.is_id_property():
            if value != self._value:
                raise exc.ReadOnlyProperty()
        self._value = self._safe_value(value)

    def set_value_force(self, value):
        self._value = self._safe_value(value)

    @builtins.property
    def property_type(self):
        return self._type

    def get_property_type(self):
        return self._type

    def example(self):
        return self._example


class IDProperty(Property):
    @classmethod
    def is_id_property(cls):
        return True


# The keyword arguments `Property.__init__` understands, minus `value`,
# which a creator supplies per property built.
_PLAIN_PROPERTY_KWARGS = frozenset(
    ("default", "required", "read_only", "mutable", "example")
)


class PropertyCreator(object):
    def __init__(self, prop_class, prop_type, args, kwargs):
        self._property = prop_class
        self._property_type = prop_type
        self._args = args
        self._kwargs = kwargs
        self._prefetch = kwargs.pop("prefetch", False)

        # A declaration is read once and built from per model, so
        # everything about it that does not depend on the value is settled
        # here. What is left per property is a validate and an allocation
        # -- `Property.__init__` used to re-answer, per property per
        # model, questions the declaration had already answered.
        #
        # Only the two property classes shipped here take the short path:
        # a subclass may mean anything by these arguments, and gets the
        # constructor call it always got.
        self._fast = (
            prop_class in (Property, IDProperty)
            and not args
            and not (set(kwargs) - _PLAIN_PROPERTY_KWARGS)
        )
        if self._fast:
            _check_property_type(prop_type)
            default = kwargs.get("default")
            self._default = default
            self._default_is_callable = callable(default)
            self._required = bool(kwargs.get("required", False))
            self._read_only = bool(kwargs.get("read_only", False))
            self._mutable = bool(kwargs.get("mutable", False))
            self._example = kwargs.get("example")

    def build_value(self, value):
        """The value a property built from this would hold.

        The declaration decides everything about it except the value
        itself, so a model that is only going to be read can keep the
        value and leave the property unbuilt. What is checked is what
        the constructor checks: a default where nothing was given, a
        type that accepts it, a required property that got something.
        """
        if value is None:
            value = self._default() if self._default_is_callable else self._default
        if value is None:
            if self._required:
                raise exc.PropertyRequired()
        elif not self._property_type.validate(value):
            raise exc.TypeError(value=value, property_type=self._property_type)
        return value

    def build_first_value(self, value):
        """What `is_dirty` will compare against later."""
        return copy.deepcopy(value) if self._mutable else value

    def adopt(self, value, first_value):
        """A property carrying a value this creator already checked."""
        prop = self._property.__new__(self._property)
        prop._type = self._property_type
        prop._required = self._required
        prop._read_only = self._read_only
        prop._value = value
        prop._first_value = first_value
        prop._example = self._example
        return prop

    @builtins.property
    def is_plain(self):
        """Whether a value of this can stand on its own, unwrapped."""
        return self._fast

    def __call__(self, value):
        if not self._fast:
            return self._property(
                value=value,
                property_type=self._property_type,
                *self._args,
                **self._kwargs,
            )

        if value is None:
            value = self._default() if self._default_is_callable else self._default

        property_type = self._property_type
        if value is None:
            if self._required:
                raise exc.PropertyRequired()
        elif not property_type.validate(value):
            raise exc.TypeError(value=value, property_type=property_type)

        prop = self._property.__new__(self._property)
        prop._type = property_type
        prop._required = self._required
        prop._read_only = self._read_only
        prop._value = value
        prop._first_value = copy.deepcopy(value) if self._mutable else value
        prop._example = self._example
        return prop

    def get_property_class(self):
        return self._property

    def get_property_type(self):
        return self._property_type

    def get_kwargs(self):
        return self._kwargs

    def is_prefetch(self):
        return self._prefetch


class PropertyMapping(collections_abc.Mapping, metaclass=abc.ABCMeta):
    """A mapping over `self._properties`, exposed read-only.

    A subclass sets `_properties` before this class is of any use; there
    is deliberately no default, so forgetting it fails loudly rather than
    behaving as an empty mapping.

    The `properties` proxy is built once per instance and handed out on
    every request: it is a view over `_properties`, so a fresh one says
    nothing new, and building one per lookup put an allocation on the path
    of every model attribute read. Subclasses that replace `_properties`
    wholesale must call `_reset_properties_proxy`.
    """

    @property
    def properties(self):
        try:
            return self.__proxy
        except AttributeError:
            self.__proxy = utils.ReadOnlyDictProxy(self._properties)
            return self.__proxy

    def _reset_properties_proxy(self):
        self.__proxy = utils.ReadOnlyDictProxy(self._properties)

    def __getitem__(self, name):
        return self._properties[name]

    def __contains__(self, name):
        # The Mapping version asks `__getitem__` and catches the KeyError,
        # which puts a raised exception on the path of every attribute a
        # model sets that is not a property.
        return name in self._properties

    def __iter__(self):
        return iter(self._properties)

    def __len__(self):
        return len(self._properties)


class PropertyCollection(PropertyMapping):
    # A declaration keeps no values, so a model reaching here before it
    # has any finds none -- the same shape a manager has.
    _values = {}

    def __init__(self, **kwargs):
        self._properties = kwargs
        self._nested_names = frozenset(
            name
            for name, item in kwargs.items()
            if isinstance(item, PropertyCollection)
        )
        self._plain = None
        super(PropertyCollection, self).__init__()

    @builtins.property
    def values_can_stand_alone(self):
        """Whether a model of this can keep values instead of properties.

        Every property has to be one this package builds -- a subclass
        may mean anything by a value -- and none of them a nested
        collection, which is a manager of its own.
        """
        if self._plain is None:
            self._plain = not self._nested_names and all(
                getattr(item, "is_plain", False) for item in self._properties.values()
            )
        return self._plain

    @builtins.property
    def nested_names(self):
        """The names holding a nested collection rather than a property.

        A declaration decides this, so it is answered once here instead of
        per model built from the collection: the check is an abstract-base
        `isinstance`, which is not cheap and ran per property per model.
        """
        return self._nested_names

    def sort_properties(self):
        """Switch the model to sorted properties

        After call this method all requests to Model.properties will return
        sorted values. For example:

        ```
        class Model(Model):
            b = properties.property(type.B())
            a = properties.property(type.A())

        Model.properties.keys()  #-> ['b', 'a']
        Model.properties.sort_properties()
        Model.properties.keys()  #-> ['a', 'b']
        ```

        Most often, this functionality is needed for tests.
        """
        global declaration_version

        result = collections.OrderedDict()
        for key in sorted(self._properties):
            result[key] = self._properties[key]
        self._properties = result
        self._plain = None
        self._reset_properties_proxy()

        declaration_version += 1

    def __getitem__(self, name):
        return self._properties[name].get_property_class()

    def __add__(self, other):
        if isinstance(other, PropertyCollection):
            props = dict(self.properties)
            props.update(other.properties)
            return type(self)(**props)
        raise TypeError(
            "Cannot concatenate %s and %s objects"
            % (type(self).__name__, type(other).__name__)
        )

    def instantiate_property(self, name, value=None):
        return self._properties[name](value)

    def get_property_class(self):
        return type(self)


class PropertyManager(PropertyMapping):
    """A model's properties -- as objects, or as the values behind them.

    A property object answers questions about itself: what type it is,
    whether it may be written, what it held to begin with. Reading a
    model asks none of them, and building one object per column per row
    is most of what reading a row costs.

    So a model whose properties are all ones this package builds keeps
    the values, and builds the property the moment something asks for
    one -- by name, or by walking the mapping. Each name lives in
    exactly one of the two places, never both.
    """

    #: what a name absent from the values given is, before defaults
    MISSING = object()

    def __init__(self, property_collection, **kwargs):
        self._collection = property_collection
        self._properties = {}
        self._values = {}
        self._first_values = {}

        if property_collection.values_can_stand_alone:
            self._pour_values(property_collection, kwargs, None)
        else:
            self._build_properties(property_collection, kwargs)

        # commented because kwargs can contain 'context' etc. Figure out
        #        if len(kwargs) > 0:
        #            raise TypeError("Unknown parameters: %s" % str(kwargs))
        super(PropertyManager, self).__init__()

    @classmethod
    def poured(cls, property_collection, values, convert=None):
        """A manager over `values`, without spelling them out as keywords.

        `convert` is what turns a stored value into a model one, by name:
        given it, a row is walked once here instead of being converted
        into a mapping of its own and walked again.
        """
        manager = cls.__new__(cls)
        manager._collection = property_collection
        manager._properties = {}
        manager._values = {}
        manager._first_values = {}
        if property_collection.values_can_stand_alone:
            manager._pour_values(property_collection, values, convert)
        else:
            # Properties are built from model values, so a stored row is
            # turned into one first -- the walk this saves is the flat
            # path's, and there is none to save here.
            manager._build_properties(
                property_collection,
                (
                    {name: convert[name](value) for name, value in values.items()}
                    if convert is not None
                    else dict(values)
                ),
            )
        return manager

    def _pour_values(self, property_collection, values, convert):
        """What `build_value` says, said inline.

        This is the loop a page of rows runs per column, so it reads the
        answers off the declaration rather than calling for each of
        them. `build_value` and `build_first_value` are the same rules
        written once, and a test holds the two together.
        """
        given = values
        missing = self.MISSING
        values = self._values
        first_values = self._first_values
        for name, creator in property_collection.properties.items():
            value = given.get(name, missing)
            if value is missing:
                value = None
            elif convert is not None:
                value = convert[name](value)
            if value is None:
                value = (
                    creator._default()
                    if creator._default_is_callable
                    else creator._default
                )
            if value is None:
                if creator._required:
                    raise exc.PropertyRequired(name=name)
            elif not creator._property_type.validate(value):
                raise exc.TypeError(value=value, property_type=creator._property_type)
            values[name] = value
            if creator._mutable:
                # The one value that can change without passing through
                # the model: a list appended to, a dict written into.
                first_values[name] = copy.deepcopy(value)

    def _build_properties(self, property_collection, kwargs):
        nested_names = property_collection.nested_names
        # What a collection instantiates a property with is the creator
        # this loop is already holding; going back through the collection
        # to look it up again put a frame on the path of every property of
        # every model built. A collection that instantiates its own way
        # keeps being asked to.
        direct = (
            getattr(type(property_collection), "instantiate_property", None)
            is PropertyCollection.instantiate_property
        )
        for name, item in property_collection.properties.items():
            if name in nested_names:
                prop = PropertyManager(item, **kwargs.pop(name, {}))
            else:
                try:
                    prop = (
                        item(kwargs.pop(name, None))
                        if direct
                        else property_collection.instantiate_property(
                            name, kwargs.pop(name, None)
                        )
                    )
                except exc.PropertyRequired:
                    raise exc.PropertyRequired(name=name)
            self._properties[name] = prop

    def materialise(self, name):
        """The property object for `name`, built if it was not yet.

        Nothing has written to it -- a write goes through the model,
        which asks for the property first -- so unless the value is one
        that can be changed in place, what it holds now is what it was
        built with.
        """
        value = self._values.pop(name)
        prop = self._collection.properties[name].adopt(
            value, self._first_values.get(name, value)
        )
        self._properties[name] = prop
        return prop

    def materialise_all(self):
        """Every property as an object -- for whoever walks them all."""
        for name in list(self._values):
            self.materialise(name)
        return self._properties

    @builtins.property
    def properties(self):
        # Whoever asks for the mapping itself gets objects: the view is
        # over property objects, and a value standing on its own is not
        # one yet.
        self.materialise_all()
        return PropertyMapping.properties.fget(self)

    def is_dirty(self):
        """Whether anything here is not what it was built with.

        A value the model still keeps was never written to -- a write
        goes through the property -- so the only one that can have
        changed is one that can be changed in place.
        """
        first_values = self._first_values
        if first_values:
            values = self._values
            for name, first in first_values.items():
                if name in values and not first == values[name]:
                    return True
        for prop in self._properties.values():
            if prop.is_dirty():
                return True
        return False

    def get_value(self, name):
        values = self._values
        if name in values:
            return values[name]
        return self._properties[name].value

    def __getitem__(self, name):
        if name in self._values:
            return self.materialise(name)
        return self._properties[name]

    def __contains__(self, name):
        return name in self._values or name in self._properties

    def __iter__(self):
        return (
            iter(self._collection.properties)
            if self._values
            else iter(self._properties)
        )

    def __len__(self):
        return len(self._values) + len(self._properties)

    def keys(self):
        return list(self._values) + list(self._properties)

    def values(self):
        return self.materialise_all().values()

    def items(self):
        return self.materialise_all().items()

    @builtins.property
    def value(self):
        result = dict(self._values)
        for name, prop in self._properties.items():
            result[name] = prop.value
        return result

    @value.setter
    def value(self, values):
        for name, value in values.items():
            self[name].value = value


def property(property_type, *args, **kwargs):
    id_property = kwargs.pop("id_property", False)
    property_class = kwargs.pop(
        "property_class", IDProperty if id_property else Property
    )
    if inspect.isclass(property_class) and issubclass(property_class, AbstractProperty):
        return PropertyCreator(
            prop_class=property_class,
            prop_type=property_type,
            args=args,
            kwargs=kwargs,
        )
    else:
        raise ValueError(
            "Value of property class argument (%s) must be"
            " inherited on AbstractProperty class"
            "" % str(property_class)
        )


def container(**kwargs):
    kwargs = copy.deepcopy(kwargs)
    for prop in kwargs.values():
        if not isinstance(prop, (PropertyCreator, PropertyCollection)):
            raise Exception("Only property, relationship and container are allowed.")
    return PropertyCollection(**kwargs)


def required_property(property_type, *args, **kwargs):
    kwargs["required"] = True
    return property(property_type, *args, **kwargs)


def readonly_property(property_type, *args, **kwargs):
    kwargs["read_only"] = True
    return required_property(property_type, *args, **kwargs)
