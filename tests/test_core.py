import re

import pytest

from parametrize import parametrize


def test_parametrize_errors():
    # TODO: test other edge cases

    with pytest.raises(
        ValueError, match=re.escape("Wrong number of values at index 0, expected 2, got 1: (1,)")
    ):

        @parametrize("a,b", (1, 2))
        def f1(a, b):
            ...

    with pytest.raises(TypeError, match=re.escape("Arguments names reused: {'b'}")):

        @parametrize("a,b", [(1, 2), (3, 4)])
        @parametrize("b", (1, 2))
        def f1(a, b):
            ...

    with pytest.raises(
        TypeError, match=re.escape("Unexpected argument(s) {'b'} for function f1(a)")
    ):

        @parametrize("b", (1, 2))
        def f1(a):
            ...
