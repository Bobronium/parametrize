import re
from unittest import mock

import pytest

from parametrize import parametrize


def test_wrong_number_of_values():
    with pytest.raises(
        ValueError, match=re.escape("Wrong number of values at index 0, expected 2, got 1: (1,)")
    ):

        @parametrize("a,b", (1, 2))
        def f(a, b):
            ...


def test_arguments_name_reused():
    with pytest.raises(TypeError, match=re.escape("Arguments names reused: {'b'}")):

        @parametrize("a,b", [(1, 2), (3, 4)])
        @parametrize("b", (1, 2))
        def f(a, b):
            ...


def test_unexpected_argument():
    with pytest.raises(
        TypeError, match=re.escape("Unexpected argument(s) {'b'} for function f(a)")
    ):

        @parametrize("b", (1, 2))
        def f(a):
            ...


def test_using_parametrize_as_a_function():
    def f(a):
        ...

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Unable to find any parametrizes in decorators, "
            "please rewrite decorator name to match any of detected names @{'parametrize'}"
        ),
    ):
        parametrize("a", (1, 2))(f)


def test_parametrized_function_defined_above_and_failing_to_complete_parametrization():
    @parametrize("a", (1, 2))
    def f(a, c):
        ...

    with pytest.raises(
        NameError, match=re.escape("'f' parametrized with [1] is already defined above")
    ):

        @parametrize("a", (1, 2))
        def f(a):
            ...

    with pytest.raises(
        TypeError,
        match="Failed to complete parametrization. "
        "Please make sure all parametrization done with decorators grouped in once place",
    ):
        parametrize("c", (1, 2))(f)


def test_args_must_not_repeat():
    with pytest.raises(TypeError, match="Arguments must not repeat"):
        parametrize("a,b,c,a", ((1, 2, 3, 4), (5, 6, 7, 8)))


def test_decoration_order():
    with pytest.raises(
        TypeError,
        match=re.escape(
            '@mock.patch(f"{__name__}.bar", "foo") '
            "must be defined before any of @{'parametrize'} decorators"
        ),
    ):

        @mock.patch(f"{__name__}.bar", "foo")
        @parametrize("a", (1, 2))
        @parametrize("b", (2, 3))
        def f(a, b):
            return a, b


def test_decoration_order_with_other_decorator_between_parametrizes():
    with pytest.raises(
        TypeError,
        match=re.escape(
            'Parametrize decorator @parametrize("b", (2, 3)) must be grouped '
            "together with other parametrize decorators"
        ),
    ):

        @parametrize("a", (1, 2))
        @mock.patch(f"{__name__}.bar", "foo")
        @parametrize("b", (2, 3))
        def f(a, b):
            return a, b


def test_calling_functon_during_parametrization():
    def bad_bad_decorator(func):
        func()  # oh, no, it called the function on decoration!

    # and it disguised as a parametrize decorator!
    bad_bad_decorator.__parametrize_decorator__ = parametrize

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Attempt to execute test_calling_functon_during_parametrization.<locals>.f "
            "before it was parametrized"
        ),
    ):

        @parametrize("a", (1, 2))
        @bad_bad_decorator
        @parametrize("b", (2, 3))
        def f(a, b):
            return a, b
