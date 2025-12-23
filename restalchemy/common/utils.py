# Copyright 2014 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2014 Mirantis Inc
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

from collections import abc as collections_abc

from restalchemy.common import exceptions as ra_exc


class ReadOnlyDictProxy(collections_abc.Mapping):
    """A hashable, immutable dict proxy.

    Return a proxy object for a mapping which enforces read-only behavior.
    This is normally used to create a proxy to prevent modification of the
    dictionary for non-dynamic class types.
    """

    def __init__(self, d):
        self._d = d
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        if self._hash is None:
            self._hash = 0
            for key, value in self.items():
                self._hash ^= hash(key)
                self._hash ^= hash(value)

        return self._hash

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self._d)


class classproperty(property):
    """Property for classes

    Standard property cannot be used on classes only on instances.
    This one was created to overcome this problem. The only limitation
    is that setter is not working for classes, only getter.

    This property could be used as:
        class A(object):
            @classproperty
            def test(cls):
                ...some cls processing...
                return result

        test = A.test  # method 'test' will be called with A class argument
    """

    def __get__(self, obj, cls):
        # Calls property function
        return self.fget(cls)


def lastslash(url):
    if url and url[-1] != "/":
        return url + "/"
    else:
        return url


def raise_parse_error_on_fail(func):
    """Decorator for handling model properties/relationships parsing errors

    Catches ValueError and TypeError exceptions during field validation and
    converts them into ParseError with HTTP 400 BadRequest status. Other
    exceptions are propagated to the error middleware for further processing.

    Any validation errors from controllers or properties related to validating
    the correctness of a value must be subclasses of ValueError or TypeError.
    """

    def wrapper(obj, name, value, *args, **kwargs):
        try:
            return func(obj, name, value, *args, **kwargs)
        except (ValueError, TypeError):
            raise ra_exc.ParseError(value="%s=%s" % (name, value))
        except ra_exc.ParseError as e:
            raise ra_exc.ParseError(value="%s=%s" % (name, e.value))

    return wrapper


def find_first(seq, predicate):
    """Return first item in seq for which predicate(item) is True"""
    return next((x for x in seq if predicate(x)), None)
