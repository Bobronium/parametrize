import inspect
import itertools
from types import FrameType, FunctionType, ModuleType
from typing import Any, Iterable, Set, Union

from parametrize.utils import copy_func


class UnparametrizedMethod:
    __slots__ = ("func",)

    def __init__(self, func: FunctionType):
        self.func = func

    def __repr__(self):
        return f"{self.func.__name__}[...]"


class ParametrizeContext:
    __slots__ = ("func", "parametrizes_left", "all_parameters", "seen_argnames", "signature")

    def __init__(self, func: FunctionType, decoration_frame: FrameType):
        self.func = func
        self.signature = inspect.signature(func)
        self.parametrizes_left = _count_parametrize_decorators(func, decoration_frame)
        self.all_parameters = []
        self.seen_argnames = set()

    def add(self, parameters, argnames_set):
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
        raise RuntimeError(
            f"Attempt to execute {self.func.__qualname__} before it was parametrized"
        )


def parametrize(argnames: Union[str, Iterable[str],], argvalues: Iterable[Any]):
    """
    class TestSomething(unittest.TestCase):

        @parametrize('a,b', [(1, 2), (3, 4)])
        def test_a_and_b(self, a, b):
            self.assertGreater(b, a)

    Trick to use pytest.mark.parametrize with unittest.TestCase

    It generates parametrized test cases and injects them into class namespace
    """

    parametrization_frame = inspect.currentframe().f_back
    parameters, argnames_set = _collect_parameters(argnames, argvalues)

    def decorator(
        func_or_context: Union[FunctionType, ParametrizeContext,]
    ) -> Union[ParametrizeContext, UnparametrizedMethod,]:
        decoration_frame = inspect.currentframe().f_back
        if parametrization_frame is not decoration_frame:
            _assert_decorator_counted(decoration_frame)

        if isinstance(func_or_context, UnparametrizedMethod):  # we should never end up here
            raise TypeError("Failed to complete parametrization")

        if isinstance(func_or_context, ParametrizeContext):
            context = func_or_context
        else:
            context = ParametrizeContext(func_or_context, decoration_frame)

        context.add(parameters, argnames_set)

        if context.parametrizes_left:
            return context  # pass context to the next parametrize decorator
        else:
            # set parametrized functions in place of given one
            _set_test_cases(decoration_frame.f_locals, context)
            return UnparametrizedMethod(context.func)

    decorator.__parametrize_decorator__ = True

    return decorator


def _collect_parameters(argnames, argvalues):
    if isinstance(argnames, str):
        argnames = list(map(str.strip, argnames.split(",")))

    argnames_set = set(argnames)

    if len(argnames) != len(argnames_set):
        raise TypeError("Arguments must not repeat")

    parameters = []
    for (i, values) in enumerate(argvalues):
        if len(argnames) == 1 and isinstance(values, str) or not isinstance(values, Iterable):
            values = (values,)

        if len(values) != len(argnames):
            raise ValueError(
                f"Wrong number of values at index {i}, expected "
                f"{len(argnames)}, got {len(values)}: {values}"
            )

        parameters.append(tuple(zip(argnames, values)))

    return parameters, argnames_set


def _find_possible_decorators(namespace, search_in_modules=True):
    possible_decorators = set()
    for (key, value) in namespace.items():
        if (
            value is parametrize
            or hasattr(value, "__parametrize_decorator__")
            or hasattr(value, "__wrapped__")
            and inspect.unwrap(value) is parametrize
        ):
            possible_decorators.add(key)
        elif search_in_modules and isinstance(value, ModuleType):
            # allow usages like @my_module.my_predefined_params
            possible_decorators.update(
                _find_possible_decorators(value.__dict__, search_in_modules=False)
            )

    return possible_decorators


def _count_parametrize_decorators(function, decoration_frame):
    possible_definitions = _find_possible_decorators(
        {**decoration_frame.f_globals, **decoration_frame.f_locals}
    )
    lines, _ = inspect.getsourcelines(function)

    # maybe it would be safer/better to use ast.parse for that
    # but for now this method works pretty well
    parametrized_count = 0
    for line in map(str.strip, lines):
        if line.startswith("def "):
            break
        for definition in possible_definitions:
            if line.startswith(f"@{definition}"):
                parametrized_count += 1

    if not parametrized_count:
        raise RuntimeError(
            f"Unable to find any parametrizes in decorators, "
            f"please rewrite decorator name to match any of detected names {possible_definitions}"
        )
    return parametrized_count


def _assert_decorator_counted(decoration_frame):
    (lines, defined_on_line) = inspect.getsourcelines(decoration_frame)
    expected_definition = f"@{parametrize.__name__}"

    for line in lines:
        if line.strip().startswith(expected_definition):
            break
    else:
        raise RuntimeError(
            f"Unable to find {expected_definition} in decorators, "
            f"please rewrite decorator name to match {expected_definition}(...)"
        )


def _set_test_cases(namespace, context):
    func = context.func
    used_names: Set[str] = set()

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
            raise NameError(f"{parametrized_name} is already defined in {namespace}")

        # copying function with new default values. The reasons I didn't stick to simpler options:"
        # functools.partial will not bound to class
        # functools.partialmethod and other descriptors won't be detected as tests
        # wrapper function will add a new frame to traceback
        namespace[parametrized_name] = copy_func(func, parametrized_name, params, context.signature)
