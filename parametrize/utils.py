import sys
from inspect import Signature
from types import CodeType, FunctionType
from typing import Any, Tuple


if sys.version_info >= (3, 8):
    copy_code = CodeType.replace
else:
    PY_36_37_CODE_ARGS: Tuple[str, ...] = (
        "co_argcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_stacksize",
        "co_flags",
        "co_code",
        "co_consts",
        "co_names",
        "co_varnames",
        "co_filename",
        "co_name",
        "co_firstlineno",
        "co_lnotab",
        "co_freevars",
        "co_cellvars",
    )

    def copy_code(code: CodeType, **update: Any) -> CodeType:
        """
        Create a copy of code object with changed attributes
        """
        new_args = [update.pop(arg, getattr(code, arg)) for arg in PY_36_37_CODE_ARGS]
        if update:
            raise TypeError(f"Unexpected code attribute(s): {update}")
        return CodeType(*new_args)


def copy_func(f: FunctionType, name, defaults, signature: Signature):
    """
    Makes exact copy of a function object with given name and defaults
    """
    new_defaults = []
    kw_only_defaults = f.__kwdefaults__.copy() if f.__kwdefaults__ else {}

    for key, param in signature.parameters.items():
        if param.kind is param.KEYWORD_ONLY:
            if key in defaults:
                kw_only_defaults[key] = defaults.pop(key)
        elif key in defaults:
            new_defaults.append(defaults.pop(key))
        elif param.default is not param.empty:
            new_defaults.append(param.default)

    new_func = FunctionType(
        code=copy_code(f.__code__, co_name=name),
        globals=f.__globals__,
        name=name,
        argdefs=tuple(new_defaults),
        closure=f.__closure__,
    )
    new_func.__kwdefaults__ = kw_only_defaults
    new_func.__dict__.update(f.__dict__)
    return new_func
