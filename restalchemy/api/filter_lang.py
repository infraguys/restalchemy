# Copyright 2026 Genesis Corporation
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

"""A filter language for collection endpoints, a subset of AIP-160.

`Controller` reads it from the query parameter its `__filter_param__`
names (`q` unless a resource renames it) and ANDs the result onto the
field parameters; nothing else in `restalchemy.api` calls this module.

The point of departure is that the DM layer already speaks a filter
language -- `dm.filters` is an expression tree of AND/OR/NOT over clauses,
and `storage.sql.filters` already compiles that tree to SQL for both
dialects. What the HTTP surface can express is a flat AND of EQ and In,
which is far less. So this module is a *parser into the existing tree*,
not a new filtering mechanism: `parse` turns a string into an AST, `build`
turns the AST into what `get_all(filters=...)` already accepts.

Grammar implemented, a subset of
https://google.aip.dev/assets/misc/ebnf-filtering.txt ::

    filter      : [expression]
    expression  : sequence {WS AND WS sequence}
    sequence    : factor {WS factor}
    factor      : term {WS OR WS term}
    term        : [NOT WS] simple
    simple      : restriction | composite
    restriction : comparable [comparator arg]
    comparable  : member
    member      : value {DOT field}
    composite   : LPAREN expression RPAREN
    comparator  : "<=" | "<" | ">=" | ">" | "!=" | "=" | ":"
    value       : TEXT | STRING

Note the precedence, which is AIP-160's and is not the usual one: OR binds
*tighter* than AND, because `factor` (the OR level) sits inside `sequence`
(the implicit-AND level) which sits inside `expression` (the AND level).
`a OR b AND c OR d` is `(a OR b) AND (c OR d)`.

What the operators mean here::

    name = "vm1"              EQ("vm1")
    name != "vm1"             NE("vm1")
    size > 10                 GT(10)
    name = null               Is(None)          # and != null -> IsNot(None)
    tags:"env:prod"           ContainsAll(["env:prod"])   # array column
    description:*             IsNot(None)                 # field is set
    spec.kind = "totp"        JSONFields({"kind": EQ("totp")})
    NOT (a = 1 AND b = 2)     NOT(...)

There is no operator for `ContainsAny`, and none is missing: the boolean
operators already say it. `tags:"a"` is `tags @> ARRAY['a']`, so

    tags:"a" AND tags:"b"     ContainsAll(["a", "b"])     ->  @> ARRAY[a,b]
    tags:"a" OR tags:"b"      ContainsAny(["a", "b"])     ->  && ARRAY[a,b]
    a = 1 OR a = 2            In([1, 2])                  ->  = ANY(...)

fall out of folding same-field clauses together (`_FOLDS`). Expressing
this with query parameters alone would take two operator names, one for
each direction, because a list of parameters has no AND and no OR to
carry the difference; a language does, and one operator covers both.
Folding is not just tidiness -- it is one index probe instead of one per
element.

Values carrying punctuation must be quoted -- `tags:"env:prod"`, not
`tags:env:prod`, since the second `:` would read as another comparator.
That covers timestamps (`"2026-07-31T11:30:00Z"`) too. Quoting is the
answer a language can give to that ambiguity and a bare query parameter,
where the value has no delimiters of its own, cannot.

Not implemented, deliberately:

* functions (`call(arg)`) -- nothing to call yet;
* bare literals (`"prod"` on its own, a fuzzy match across fields) -- the
  resource does not say which fields such a search should cover;
* `-` as a synonym for NOT -- it collides with negative numbers and with
  hyphens inside unquoted values; `NOT` is unambiguous;
* wildcards in `=` (`name = "*.foo"`) -- they would compile to LIKE, and
  escaping the `%` and `_` already inside the value needs an ESCAPE clause
  that `filters.Like` does not emit;
* field-to-field comparison (`a = b`): the right side is always a literal;
* traversal deeper than one key (`spec.a.b`) -- `JSONFields` maps a single
  key to a clause.

Everything not implemented is refused at parse or bind time with a 400,
never silently ignored: AIP-160 explicitly allows a service to restrict
the language, provided it says so and errors on the rest.
"""

import logging
import re

from restalchemy.common import exceptions as exc
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import types as dm_types

LOG = logging.getLogger(__name__)

# What a key inside a JSON column may be called; see `_bind_json`.
_JSON_KEY = re.compile(r"^[\w-]+$")

# Caps on the parsed tree. A filter string is attacker-controlled input, and
# a recursive-descent parser over an unbounded one is a stack overflow --
# this is CVE-2018-8269 in OData, where "1 add 1 add 1 ..." repeated enough
# times killed the process. MAX_NODES is OData's own default for the same
# job (MaxNodeCount); MAX_DEPTH bounds the recursion directly.
MAX_NODES = 100
MAX_DEPTH = 8

# The caps above bound the tree; this one bounds the scan that builds it,
# which runs to the end of the string before a single node is counted. A
# megabyte of `a=1 ` is seconds of CPU spent to reach a cap that rejects
# it. Far above what MAX_NODES admits, short of very long values.
MAX_LENGTH = 4096

AND = "AND"
OR = "OR"
NOT = "NOT"
KEYWORDS = frozenset((AND, OR, NOT))

HAS = ":"
PRESENCE = "*"
NULL = "null"

# Two-character comparators first: `<` is a prefix of `<=`.
_COMPARATORS = ("<=", ">=", "!=", "=", "<", ">", HAS)

_COMPARATOR_CLAUSES = {
    "=": dm_filters.EQ,
    "!=": dm_filters.NE,
    "<": dm_filters.LT,
    "<=": dm_filters.LE,
    ">": dm_filters.GT,
    ">=": dm_filters.GE,
}

_TEXT_STOP = frozenset(" \t\r\n()\"'<>=!:,.")

# Token kinds.
_TEXT = "text"
_STRING = "string"
_OP = "op"
_LPAREN = "("
_RPAREN = ")"
_DOT = "."
_EOF = "eof"

_STRING_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "'": "'",
    "\\": "\\",
}


def _syntax_error(pos, reason):
    return exc.ValidationFilterSyntaxError(pos=pos, reason=reason)


class _Token:
    __slots__ = ("kind", "pos", "value", "ws_before")

    def __init__(self, kind, value, pos, ws_before):
        self.kind = kind
        self.value = value
        self.pos = pos
        self.ws_before = ws_before

    def __repr__(self):
        return f"<{self.kind} {self.value!r}@{self.pos}>"


def _scan_string(text, start):
    """Read a quoted literal starting at `start`, return (value, next)."""
    quote = text[start]
    chars = []
    i = start + 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            if i + 1 >= len(text):
                raise _syntax_error(i, "escape at end of string")
            escaped = text[i + 1]
            if escaped not in _STRING_ESCAPES:
                raise _syntax_error(i, f"unknown escape '\\{escaped}'")
            chars.append(_STRING_ESCAPES[escaped])
            i += 2
            continue
        if char == quote:
            return "".join(chars), i + 1
        chars.append(char)
        i += 1
    raise _syntax_error(start, "unterminated string")


def _scan_text(text, start):
    """Read an unquoted literal starting at `start`, return (value, next)."""
    i = start
    while i < len(text):
        char = text[i]
        if char not in _TEXT_STOP:
            i += 1
            continue
        # A dot between digits belongs to the number, not to a traversal:
        # `1.5` is one literal, `spec.kind` is two.
        if (
            char == "."
            and i > start
            and text[i - 1].isdigit()
            and i + 1 < len(text)
            and text[i + 1].isdigit()
        ):
            i += 1
            continue
        break
    return text[start:i], i


def tokenize(text):
    tokens = []
    i = 0
    length = len(text)
    ws_before = False
    while i < length:
        char = text[i]
        if char in " \t\r\n":
            ws_before = True
            i += 1
            continue
        if char in "()":
            tokens.append(_Token(char, char, i, ws_before))
            i += 1
        elif char == ".":
            tokens.append(_Token(_DOT, char, i, ws_before))
            i += 1
        elif char in "\"'":
            value, end = _scan_string(text, i)
            tokens.append(_Token(_STRING, value, i, ws_before))
            i = end
        elif char == ",":
            raise _syntax_error(i, "',' is only used by functions, unsupported")
        else:
            comparator = None
            for candidate in _COMPARATORS:
                if text.startswith(candidate, i):
                    comparator = candidate
                    break
            if comparator is not None:
                tokens.append(_Token(_OP, comparator, i, ws_before))
                i += len(comparator)
            else:
                if char == "!":
                    raise _syntax_error(i, "'!' is only valid as '!='")
                value, end = _scan_text(text, i)
                if not value:
                    raise _syntax_error(i, f"unexpected character {char!r}")
                tokens.append(_Token(_TEXT, value, i, ws_before))
                i = end
        ws_before = False
    tokens.append(_Token(_EOF, "", length, ws_before))
    return tokens


class Node:
    """Base of the parsed tree. Carries no resource knowledge."""

    _FIELDS = ()

    def __eq__(self, other):
        # Identity, not isinstance: Disjunction is a Conjunction, and an
        # AND that compared equal to an OR would make every test lie.
        return type(other) is type(self) and all(
            getattr(self, name) == getattr(other, name) for name in self._FIELDS
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<{} {}>".format(
            type(self).__name__,
            " ".join(f"{n}={getattr(self, n)!r}" for n in self._FIELDS),
        )


class Literal(Node):
    """A value as written: its text, and whether it was quoted.

    Quoting is kept because it is meaningful -- `null` is the null literal,
    `"null"` is the four-character string, and `*` is a presence check
    where `"*"` is an asterisk.
    """

    _FIELDS = ("text", "quoted")

    def __init__(self, text, quoted=False):
        self.text = text
        self.quoted = quoted


class Conjunction(Node):
    _FIELDS = ("operands",)

    def __init__(self, *operands):
        self.operands = list(operands)


class Disjunction(Conjunction):
    pass


class Negation(Node):
    _FIELDS = ("operand",)

    def __init__(self, operand):
        self.operand = operand


class Restriction(Node):
    """`member comparator arg`, e.g. `spec.kind = "totp"`.

    `path` is the member split on dots: one element for a column, two for
    a key inside a JSON column. `comparator` is None for a bare member,
    which parses but does not bind.
    """

    _FIELDS = ("path", "comparator", "value")

    def __init__(self, path, comparator=None, value=None):
        self.path = path
        self.comparator = comparator
        self.value = value

    @property
    def name(self):
        return ".".join(part.text for part in self.path)


class _Parser:
    def __init__(self, tokens, max_nodes, max_depth):
        self._tokens = tokens
        self._pos = 0
        self._nodes = 0
        self._max_nodes = max_nodes
        self._max_depth = max_depth

    def parse(self):
        if self._peek().kind == _EOF:
            return None
        node = self._expression(depth=1)
        token = self._peek()
        if token.kind != _EOF:
            raise _syntax_error(token.pos, f"unexpected {token.value!r}")
        return node

    # Token helpers.

    def _peek(self):
        return self._tokens[self._pos]

    def _advance(self):
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _at_keyword(self, keyword):
        token = self._peek()
        return token.kind == _TEXT and token.value == keyword

    def _starts_factor(self):
        """Whether the next token opens another factor of a sequence.

        Whitespace is required: the grammar joins factors with WS, and
        without that rule `(a)(b)` would quietly mean `a AND b`.
        """
        token = self._peek()
        if not token.ws_before:
            return False
        if token.kind in (_STRING, _LPAREN):
            return True
        return token.kind == _TEXT and token.value not in (AND, OR)

    def _count(self, node):
        self._nodes += 1
        if self._nodes > self._max_nodes:
            raise exc.ValidationFilterTooComplexError(
                reason=f"more than {self._max_nodes} nodes"
            )
        return node

    def _check_depth(self, depth):
        if depth > self._max_depth:
            raise exc.ValidationFilterTooComplexError(
                reason=f"nested deeper than {self._max_depth}"
            )

    # Grammar.

    def _expression(self, depth):
        self._check_depth(depth)
        operands = [self._sequence(depth)]
        while self._at_keyword(AND):
            self._advance()
            operands.append(self._sequence(depth))
        if len(operands) == 1:
            return operands[0]
        return self._count(Conjunction(*operands))

    def _sequence(self, depth):
        operands = [self._factor(depth)]
        while self._starts_factor():
            operands.append(self._factor(depth))
        if len(operands) == 1:
            return operands[0]
        return self._count(Conjunction(*operands))

    def _factor(self, depth):
        operands = [self._term(depth)]
        while self._at_keyword(OR):
            self._advance()
            operands.append(self._term(depth))
        if len(operands) == 1:
            return operands[0]
        return self._count(Disjunction(*operands))

    def _term(self, depth):
        if self._at_keyword(NOT):
            self._advance()
            return self._count(Negation(self._simple(depth)))
        return self._simple(depth)

    def _simple(self, depth):
        if self._peek().kind == _LPAREN:
            self._advance()
            node = self._expression(depth + 1)
            token = self._advance()
            if token.kind != _RPAREN:
                raise _syntax_error(token.pos, "expected ')'")
            return node
        return self._restriction()

    def _restriction(self):
        start = self._peek()
        path = self._member()
        if self._peek().kind != _OP:
            self._reject_lowercase_keyword(start, path)
            return self._count(Restriction(path))
        comparator = self._advance().value
        return self._count(Restriction(path, comparator, self._arg()))

    @staticmethod
    def _reject_lowercase_keyword(token, path):
        """Say so when `and` was meant as AND.

        The keywords are case-sensitive, so `a = 1 and b = 2` reads `and`
        as a field name and dies as an unknown field, pointing at the
        wrong thing entirely.
        """
        if len(path) != 1 or path[0].quoted:
            return
        text = path[0].text
        if text.upper() in KEYWORDS and text not in KEYWORDS:
            raise _syntax_error(
                token.pos,
                f"{text!r} is a field name here; the keyword is {text.upper()}",
            )

    def _member(self):
        parts = [self._literal("a field name")]
        while self._peek().kind == _DOT:
            self._advance()
            parts.append(self._literal("a field name after '.'"))
        return parts

    def _arg(self):
        return self._literal("a value")

    def _literal(self, expected):
        token = self._advance()
        if token.kind not in (_TEXT, _STRING):
            raise _syntax_error(
                token.pos,
                "expected {}, got {!r}".format(
                    expected, token.value or "end of filter"
                ),
            )
        return self._count(Literal(token.value, token.kind == _STRING))


def parse(text, max_nodes=MAX_NODES, max_depth=MAX_DEPTH, max_length=MAX_LENGTH):
    """Parse a filter string into an AST, or None if it is empty.

    Raises ValidationFilterSyntaxError / ValidationFilterTooComplexError,
    both of which are 400s.
    """
    if max_length is not None and len(text) > max_length:
        raise exc.ValidationFilterTooComplexError(
            reason=f"longer than {max_length} characters"
        )
    return _Parser(tokenize(text), max_nodes, max_depth).parse()


class FieldResolver:
    """What binding an AST to one resource needs to know.

    Split out from the binder so the language stays testable without a
    request, and so the API layer can supply the resolution it already
    does -- `__resource__.get_model_field_name` for the name, and
    `parse_value_from_unicode` for the value -- instead of a second,
    divergent copy of it.
    """

    def resolve(self, name):
        """Return (storage field name, dm type) or raise a 400."""
        raise NotImplementedError()

    def parse_value(self, name, field_type, text):
        """Turn the literal's text into a value of the field's type."""
        raise NotImplementedError()

    def supports(self, clause_class):
        """Whether the storage dialect can compile this clause."""
        return True


def supported_clauses(dialect):
    """The clauses a storage dialect can compile, or None for no gate.

    Pass a dialect ("postgresql", "mysql") to refuse a clause it has no
    mapping for -- `ContainsAll` and `JSONFields` are PostgreSQL only.
    Without the gate the filter would reach `convert_filters` and die
    there as a ValueError, which is a 500 for what is a client error.
    """
    if dialect is None:
        return None
    # Imported here: this is the only line of the language that knows
    # storage exists at all.
    from restalchemy.storage.sql import filters as sql_filters

    return sql_filters.FILTER_MAPPING[dialect]


class ModelFieldResolver(FieldResolver):
    """Resolves against a DM model, with an optional dialect gate."""

    def __init__(self, model, dialect=None):
        super().__init__()
        self._model = model
        self._supported = supported_clauses(dialect)

    def resolve(self, name):
        try:
            prop = self._model.properties.properties[name]
        except KeyError:
            raise exc.ValidationFilterIncompatibleError(val=name)
        return name, prop.get_property_type()

    def parse_value(self, name, field_type, text):
        try:
            return field_type.from_unicode(text)
        except (TypeError, ValueError) as e:
            raise exc.ValidationFilterSyntaxError(pos=0, reason=f"{name}: {e}")

    def supports(self, clause_class):
        return self._supported is None or clause_class in self._supported


def _unsupported(restriction, reason):
    # %r: the name can be a quoted literal, newlines and all.
    LOG.debug("Refusing filter %r: %s", restriction.name, reason)
    return exc.ValidationFilterIncompatibleError(val=restriction.name)


def _json_value(literal):
    """A literal's value where no declared type says what it should be.

    Inside a JSON column the schema is the caller's, not the model's, so
    the shape of the text is all there is to go on. The cast matters:
    `PostgreSqlJSONFields` picks its SQL cast off the Python type, and a
    string where a number was meant compares against the wrong index.
    """
    if literal.quoted:
        return literal.text
    text = literal.text
    if text == NULL:
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _bind_json(restriction, resolver, storage_name, field_type):
    key = restriction.path[1].text
    if restriction.comparator == HAS:
        raise _unsupported(restriction, "':' inside a JSON column")
    clause_class = _COMPARATOR_CLAUSES[restriction.comparator]
    if not resolver.supports(dm_filters.JSONFields):
        raise _unsupported(restriction, "JSON traversal needs PostgreSQL")
    if not isinstance(field_type, dm_types.Dict):
        # Traversing a column that holds no keys compiles to
        # `("name"->>'x')`, which PostgreSQL rejects as an undefined
        # operator -- a 500 for what the caller got wrong.
        raise _unsupported(restriction, "traversal needs a JSON field")
    if not _JSON_KEY.match(key):
        # The one name in an expression with no property to resolve it
        # against, and so the one that reaches the SQL as text rather than
        # as a parameter (see `sql.filters._JSONFieldClause`). Held to what
        # an unquoted member could have said: quoting buys no alphabet.
        raise _unsupported(restriction, "a JSON key is a bare name")
    value = _json_value(restriction.value)
    return {storage_name: dm_filters.JSONFields({key: clause_class(value)})}


def _bind_has(restriction, resolver, storage_name, field_type):
    literal = restriction.value
    if literal.text == PRESENCE and not literal.quoted:
        # `field:*` -- the field is set. Distinct from `field = null`.
        return {storage_name: dm_filters.IsNot(None)}
    if not isinstance(field_type, dm_types.List):
        # For a scalar AIP-160 leaves `:` to the service; substring
        # matching (Like) is the usual reading, and is left out until the
        # escaping question below is settled.
        raise _unsupported(restriction, "':' needs an array field")
    if not resolver.supports(dm_filters.ContainsAll):
        raise _unsupported(restriction, "array containment needs PostgreSQL")
    # An array type parses one query value into a one-element list, which
    # is exactly the array `@>` wants.
    value = resolver.parse_value(restriction.name, field_type, literal.text)
    return {storage_name: dm_filters.ContainsAll(value)}


def _bind_restriction(restriction, resolver):
    if restriction.comparator is None:
        raise _unsupported(restriction, "a bare literal names no field")
    if len(restriction.path) > 2:
        raise _unsupported(restriction, "traversal deeper than one key")
    storage_name, field_type = resolver.resolve(restriction.path[0].text)

    if len(restriction.path) == 2:
        return _bind_json(restriction, resolver, storage_name, field_type)

    if restriction.comparator == HAS:
        return _bind_has(restriction, resolver, storage_name, field_type)

    literal = restriction.value
    if literal.text == NULL and not literal.quoted:
        # NULL is not a value any comparison operator handles; `= null`
        # has to become IS, or it silently matches nothing.
        if restriction.comparator not in ("=", "!="):
            raise _unsupported(restriction, "null compares only with = and !=")
        clause_class = (
            dm_filters.Is if restriction.comparator == "=" else dm_filters.IsNot
        )
        return {storage_name: clause_class(None)}

    clause_class = _COMPARATOR_CLAUSES[restriction.comparator]
    if not resolver.supports(clause_class):
        raise _unsupported(restriction, f"{clause_class} is not supported here")
    value = resolver.parse_value(restriction.name, field_type, literal.text)
    return {storage_name: clause_class(value)}


# Clauses on one field that a boolean operator can merge into a single
# clause, keyed by (clause as bound, whether the operator is OR).
#
# This is where ContainsAny comes from: there is no operator that spells
# it, because the language does not need one. `tags:"a"` is `@> ARRAY['a']`,
# so ORing two of them is "holds either" -- which is `&&` -- and ANDing
# them is "holds both" -- which is one wider `@>`. Query parameters would
# need a named operator per direction precisely because a parameter list
# has no AND and no OR to carry the difference.
#
# Not listed, and so not folded: `AND` of EQ (`a = 1 AND a = 2` is a
# contradiction, not a wider filter) and `AND` of ContainsAny (holding one
# of {a,b} and one of {c,d} is not holding one of {a,b,c,d}).
_FOLDS = {
    (dm_filters.EQ, True): dm_filters.In,
    (dm_filters.ContainsAll, True): dm_filters.ContainsAny,
    (dm_filters.ContainsAll, False): dm_filters.ContainsAll,
}

# In collects whole values as elements; the array clauses collect the
# elements of the lists they already hold.
_SCALAR_FOLDS = frozenset((dm_filters.In,))


def _may_join(clause, target):
    """Whether `clause` may join a group folding into `target`.

    Only `ContainsAny` turns anything away, and it has to: `@>` over
    several elements is not the union of them. ORing `@> ARRAY['a','b']`
    -- "holds both" -- with `@> ARRAY['c']` is not `&& ARRAY['a','b','c']`,
    which lets a row holding only `a` through. A one-element `@>` *is* the
    same statement as its element, so those, and only those, merge.
    """
    if target is dm_filters.ContainsAny:
        return len(clause.value) == 1
    return True


def _single_leaf(operand):
    """(field, clause) if the operand is a one-field mapping, else None."""
    if not isinstance(operand, dict) or len(operand) != 1:
        return None
    return next(iter(operand.items()))


def _fold(operands, is_or, resolver):
    """Merge same-field clauses so one SQL operator does the work.

    `a = 1 OR a = 2` becomes `= ANY(%s)` rather than a chain of ORs the
    planner may not recognise as an index lookup, and a run of `tags:`
    becomes one array operator rather than one GIN probe per element.

    Folding is per field and partial: operands that do not take part are
    left where they are, so `tags:"a" OR tags:"b" OR name = x` keeps the
    OR and folds only the two array clauses inside it.
    """
    merged = []
    # (field, target clause) -> index into `merged`, so the second clause
    # of a group can rewrite the first one in place. Until a second one
    # turns up the first stays exactly as it was bound: a lone `a = 1` is
    # an EQ, not an In of one element.
    groups = {}
    for operand in operands:
        leaf = _single_leaf(operand)
        if leaf is None:
            merged.append(operand)
            continue
        name, clause = leaf
        target = _FOLDS.get((type(clause), is_or))
        if (
            target is None
            or not resolver.supports(target)
            or not _may_join(clause, target)
        ):
            merged.append(operand)
            continue
        key = (name, target)
        if key not in groups:
            groups[key] = len(merged)
            merged.append(operand)
            continue
        position = groups[key]
        held = merged[position][name]
        scalar = target in _SCALAR_FOLDS
        if scalar and type(held) is not target:
            # The first of a scalar group is still the EQ it was bound as.
            values = [held.value]
        else:
            values = list(held.value)
        if scalar:
            values.append(clause.value)
        else:
            values.extend(clause.value)
        merged[position] = {name: target(values)}
    return merged


def _bind(node, resolver):
    if isinstance(node, Restriction):
        return _bind_restriction(node, resolver)
    if isinstance(node, Negation):
        return dm_filters.NOT(_bind(node.operand, resolver))
    is_or = isinstance(node, Disjunction)
    operands = _fold(
        [_bind(operand, resolver) for operand in node.operands],
        is_or,
        resolver,
    )
    if len(operands) == 1:
        # Everything folded into one clause; the expression is spent.
        return operands[0]
    return dm_filters.OR(*operands) if is_or else dm_filters.AND(*operands)


def build(node, resolver):
    """Bind an AST to a resource, producing DM filters.

    The result is what `objects.get_all(filters=...)` already takes: a
    `{field: clause}` mapping for a single restriction, an expression tree
    otherwise. Every leaf mapping holds exactly one field -- inside an OR
    a two-key mapping would flatten into two ORed clauses rather than the
    AND it looks like.
    """
    if node is None:
        return {}
    return _bind(node, resolver)


def compile_filter(
    text,
    resolver,
    max_nodes=MAX_NODES,
    max_depth=MAX_DEPTH,
    max_length=MAX_LENGTH,
):
    """parse + build, for callers that have no use for the AST."""
    return build(parse(text, max_nodes, max_depth, max_length), resolver)
