import inspect
import itertools
import sys
from contextlib import suppress
from functools import partial, wraps
from types import FrameType, FunctionType, ModuleType
from typing import Any, Dict, Iterable, List, Set, Tuple, Union, cast

from parametrize.utils import copy_func


Parameter = Tuple[str, Any]
Parameters = Tuple[Parameter, ...]
ParametersList = List[Parameters]


class UnparametrizedMethod:
    __slots__ = ("func",)

    def __init__(self, func: FunctionType):
        self.func = func

    def __getattribute__(self, item):
        """
        Forbid any usage of unparametrized object
        """
        if item in {"func", "__repr__", "__name__"}:
            return object.__getattribute__(self, item)

        raise AttributeError("UnparametrizedMethod should not be used anywhere")

    def __repr__(self):
        return f"{self.func.__name__}[...]"


class ParametrizeContext:
    __slots__ = (
        "func",
        "parametrizes_left",
        "all_parameters",
        "seen_argnames",
        "signature",
        "decoration_frame",
    )

    def __init__(self, func: FunctionType, decoration_frame: FrameType):
        self.func = func
        self.signature = inspect.signature(func)
        self.parametrizes_left = _count_parametrize_decorators(func, decoration_frame)
        self.all_parameters: List[ParametersList] = []
        self.seen_argnames: Set[str] = set()
        self.decoration_frame = decoration_frame

    def add(self, parameters: ParametersList, argnames_set: Set[str]):
        reused_names = argnames_set & self.seen_argnames
        if reused_names:
            raise TypeError(f"Arguments names reused: {reused_names}")

        if argnames_set - self.signature.parameters.keys():
            raise TypeError(
                f"Unexpected argument(s) {argnames_set} "
                f"for function {self.func.__name__}{self.signature}"
            )

        self.all_parameters.append(parameters)
        self.seen_argnames.update(argnames_set)
        self.parametrizes_left -= 1

    @property
    def combined_parameters(self):
        for case in itertools.product(*self.all_parameters):
            yield {k: v for params in case for k, v in params}

    def __call__(self, *args, **kwargs):
        """
        We should never end up here.
        This method is necessary just to ensure in case something goes wrong, it won't be unnoticed
        """
        raise RuntimeError(
            f"Attempt to execute {self.func.__qualname__} before it was parametrized"
        )


def parametrize(argnames: Union[str, Iterable[str]], argvalues: Iterable[Any]):
    """
    class TestSomething(unittest.TestCase):

        @parametrize('a,b', [(1, 2), (3, 4)])
        def test_a_and_b(self, a, b):
            self.assertGreater(b, a)

    Trick to use pytest.mark.parametrize with unittest.TestCase

    It generates parametrized test cases and injects them into class namespace
    """

    parameters, argnames_set = _collect_parameters(argnames, argvalues)

    def decorator(
        func_or_context: Union[FunctionType, ParametrizeContext]
    ) -> Union[ParametrizeContext, UnparametrizedMethod]:
        if isinstance(func_or_context, UnparametrizedMethod):  # we should never end up here
            raise RuntimeError(
                "Failed to complete parametrization. "
                "Please make sure all parametrization done with decorators grouped in once place"
            )

        if isinstance(func_or_context, ParametrizeContext):
            context = func_or_context
        else:
            decoration_frame = cast(FrameType, inspect.currentframe().f_back)  # type: ignore
            context = ParametrizeContext(func_or_context, decoration_frame)

        context.add(parameters, argnames_set)

        if context.parametrizes_left:
            return context  # pass context to the next parametrize decorator
        else:
            # set parametrized functions in place of given one
            _set_test_cases(context)
            return UnparametrizedMethod(context.func)

    decorator.__parametrize_decorator__ = parametrize  # type: ignore

    return decorator


def _collect_parameters(argnames, argvalues) -> Tuple[ParametersList, Set[str]]:
    if isinstance(argnames, str):
        argnames = list(map(str.strip, argnames.split(",")))

    argnames_set = set(argnames)

    if len(argnames) != len(argnames_set):
        raise TypeError("Arguments must not repeat")

    parameters = []
    for i, values in enumerate(argvalues):
        if len(argnames) == 1 and isinstance(values, str) or not isinstance(values, Iterable):
            values = (values,)

        if len(values) != len(argnames):
            raise ValueError(
                f"Wrong number of values at index {i}, expected "
                f"{len(argnames)}, got {len(values)}: {values}"
            )

        parameters.append(tuple(zip(argnames, values)))

    return parameters, argnames_set


def _find_possible_decorators(
    namespace: Dict[str, Any], search_in_modules: bool = True
) -> Set[str]:
    possible_definitions: Set[str] = set()

    if not search_in_modules and namespace.get("__name__") in sys.builtin_module_names:
        # don't search in builtin modules
        return possible_definitions

    for key, value in namespace.items():
        with suppress(ValueError):  # inspect.unwrap() may raise ValueError
            if (
                value is parametrize
                or getattr(value, "__parametrize_decorator__", False) is parametrize
                or (
                    hasattr(value, "__dict__")
                    and "__wrapped__" in value.__dict__
                    and inspect.unwrap(value) is parametrize
                )
            ):
                possible_definitions.add(key)
            elif search_in_modules and isinstance(value, ModuleType):
                # allow usages like @my_module.my_predefined_params
                possible_definitions.update(
                    _find_possible_decorators(value.__dict__, search_in_modules=False)
                )

    return possible_definitions


def _count_parametrize_decorators(function, decoration_frame):
    possible_definitions = _find_possible_decorators(
        {**decoration_frame.f_globals, **decoration_frame.f_locals}
    )
    lines, _ = inspect.getsourcelines(function)

    # maybe it would be safer/better to use ast.parse for that
    # but for now this method works pretty well
    parametrized_count = 0
    parametrize_decorators_should_end = False
    decorator_out_of_order = False
    for line in map(str.strip, lines):
        if line.startswith("def "):
            break
        for definition in possible_definitions:
            if line.startswith(f"@{definition}"):
                if parametrize_decorators_should_end:
                    raise TypeError(
                        f"Parametrize decorator {line} must be grouped "
                        f"together with other parametrize decorators"
                    )
                parametrized_count += 1
                break
        else:
            is_another_decorator = line.startswith("@")
            if is_another_decorator and parametrized_count:
                parametrize_decorators_should_end = True
            elif is_another_decorator:
                decorator_out_of_order = line

    if not parametrized_count:
        raise RuntimeError(
            f"Unable to find any parametrizes in decorators, "
            f"please rewrite decorator name to match any of detected names @{possible_definitions}"
        )

    if decorator_out_of_order:
        raise TypeError(
            f"{decorator_out_of_order} must be defined before any of "
            f"@{possible_definitions} decorators"
        )

    return parametrized_count


def _set_test_cases(context):
    func = context.func
    used_names: Set[str] = set()
    namespace = context.decoration_frame.f_locals

    for params in context.combined_parameters:
        parameters_str = "-".join(str(v).replace(".", "-") for v in params.values())

        methods_with_same_name = 1
        final_parameters_str = parameters_str

        while final_parameters_str in used_names:
            final_parameters_str = f"{parameters_str}:{methods_with_same_name}"
            methods_with_same_name += 1

        func_name = func.__name__
        used_names.add(final_parameters_str)
        parametrized_name = f"{func_name}[{final_parameters_str}]"
        if parametrized_name in namespace:
            raise NameError(
                f"{func_name!r} parametrized with [{final_parameters_str}] is already defined above"
            )

        # creating a wrapper function.
        # functools.partial alone will not bound to class
        # functools.partialmethod and other descriptors won't be detected as tests
        def get_parametrized_method(f, name, parameters):
            parametrized_func = partial(f, **parameters)

            # copying func with new default parameters and name is necessary for introspection
            # without it, pytest, for example would think that parametrized values are fixtures
            @wraps(copy_func(f, name, parameters, context.signature))
            def parametrized_method(*args, **kwargs):
                return parametrized_func(*args, **kwargs)

            return parametrized_method

        namespace[parametrized_name] = get_parametrized_method(func, parametrized_name, params)
