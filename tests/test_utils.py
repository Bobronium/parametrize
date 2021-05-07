from inspect import signature

import pytest

from parametrize.utils import PY38, PY_36_37_CODE_ARGS, copy_code, copy_func


def test_copy_code():
    def f():
        return locals()["a"]

    old_code = f.__code__
    assert old_code.co_varnames == ()
    assert old_code.co_nlocals == 0
    assert old_code.co_argcount == 0

    f.__code__ = new_code = copy_code(f.__code__, co_varnames=("a",), co_argcount=1, co_nlocals=1)

    assert new_code.co_varnames == ("a",)
    assert new_code.co_nlocals == 1
    assert new_code.co_argcount == 1

    assert old_code.co_varnames == ()
    assert old_code.co_nlocals == 0
    assert old_code.co_argcount == 0

    new_args = {}
    old_args = {}

    unchanged_args = set(PY_36_37_CODE_ARGS) - {"co_varnames", "co_nlocals", "co_argcount"}
    if PY38:
        unchanged_args.add("co_posonlyargcount")

    for arg in unchanged_args:
        new_args[arg] = getattr(new_code, arg)
        old_args[arg] = getattr(old_code, arg)

    assert new_args == old_args

    assert f(1) == 1


def test_copy_code_error():
    with pytest.raises(TypeError, match="unknown_code_arg"):
        copy_code(test_copy_code_error.__code__, unknown_code_arg=1)


def test_copy_func():
    def f(a, b=1, *, c=2, d=5):
        return a, b, c, d

    f.important_attr = object()
    f2 = copy_func(f, "f", defaults=dict(a=3, d=2), signature=signature(f))
    assert f2.__code__ == f.__code__
    assert f2.__code__ is not f.__code__
    assert f2.__dict__ == f.__dict__
    assert f2.__dict__ is not f.__dict__
    assert f2.__defaults__ == (3, 1)
    assert f2.__kwdefaults__ == {"c": 2, "d": 2}
    assert f2.__kwdefaults__ is not f.__kwdefaults__

    assert f2.important_attr is f.important_attr

    assert f2() == (3, 1, 2, 2)
    assert f2(1, b=2, c=3) == (1, 2, 3, 2)
    assert f2(1) == (1, 1, 2, 2)

    f3 = copy_func(f, "f3", defaults=dict(), signature=signature(f))
    assert f3.__code__ != f.__code__
    assert f3.__dict__ == f.__dict__
    assert f3.__dict__ is not f.__dict__
    assert f3.__name__ == "f3"
    assert f3.__qualname__.split(".")[-1] == "f3"
    assert f2.__defaults__ == (3, 1)
    assert f3.__kwdefaults__ == f.__kwdefaults__
    assert f3.__kwdefaults__ is not f.__kwdefaults__
    assert f3.important_attr is f.important_attr

    assert f3(1, b=2, c=3, d=4) == (1, 2, 3, 4)
    assert f3(1) == (1, 1, 2, 5)

    assert f.__kwdefaults__ == {"c": 2, "d": 5}
