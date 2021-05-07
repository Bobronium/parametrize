from io import StringIO
from itertools import chain, product
from typing import List, Tuple, Type
from unittest import TestCase, TextTestRunner, defaultTestLoader, mock

from parametrize import parametrize
from parametrize.parametrize import UnparametrizedMethod


def run_unittests(case: Type[TestCase]):
    suite = defaultTestLoader.loadTestsFromTestCase(case)
    return TextTestRunner(stream=StringIO()).run(suite)


def as_tuples(sequence):
    return [(v,) for v in sequence]


def assert_parametrized(test_case, *argvalues, name="test_method"):
    all_cases = list(product(*argvalues))
    test_methods = [f"{name}[{'-'.join(map(str, chain(*case)))}]" for case in all_cases]
    assert set(test_methods) & set(test_case.__dict__)
    assert isinstance(getattr(test_case, name), UnparametrizedMethod)
    assert str(getattr(test_case, name)) == f"{name}[...]"
    return all_cases


def assert_tests_passed(test_case, tests_run, failures: List[Tuple[str, str]] = None):
    result = run_unittests(test_case)
    assert result.testsRun == tests_run
    assert result.errors == []
    assert result.skipped == []
    if failures is None:
        assert not result.failures
        return

    assert len(result.failures) == len(failures)

    for (method, message), (failed_test_case, fail_message) in zip(failures, result.failures):
        assert failed_test_case._testMethodName == method
        assert message in fail_message


def test_simple_parametrize(mocker):
    test_mock = mocker.Mock("test_mock")
    values = [1, 2, 3]

    class TestSomething(TestCase):
        @parametrize("a", values)
        def test_method(self, a):
            self.assertEqual(test_mock.return_value, test_mock(a))
            self.assertIn(a, (1, 2))

    assert_parametrized(TestSomething, as_tuples(values))
    assert_tests_passed(
        TestSomething,
        tests_run=3,
        failures=[
            ("test_method[3]", "self.assertIn(a, (1, 2))\nAssertionError: 3 not found in (1, 2)")
        ],
    )
    assert test_mock.mock_calls == [mocker.call(v) for v in values]


def test_multiple_arg_parametrize(mocker):
    test_mock = mocker.Mock("test_mock")
    values = [("1", "2"), ("3", "4"), ("5", "6")]

    class TestSomething(TestCase):
        @parametrize("a,b", values)
        def test_method(self, *, a, b):
            self.assertEqual(test_mock.return_value, test_mock(a, b))
            self.assertLess(int(a) + int(b), 11)

    assert_parametrized(TestSomething, values)
    assert_tests_passed(
        TestSomething,
        tests_run=3,
        failures=[
            (
                "test_method[5-6]",
                "self.assertLess(int(a) + int(b), 11)\nAssertionError: 11 not less than 11",
            )
        ],
    )
    assert test_mock.mock_calls == [mocker.call(*v) for v in values]


def test_multiple_parametrize(mocker):
    test_mock = mocker.Mock("test_mock")
    ab_values = [("1", "2"), ("3", "4"), ("5", "6")]
    c_values = (1, 2, 3)

    class TestSomething(TestCase):
        @parametrize("a,b", ab_values)
        @parametrize("c", c_values)
        def test_method(self, a, b, c):
            self.assertEqual(test_mock.return_value, test_mock(c, a, b))
            self.assertLess(int(a) + int(b), 11, msg=f"{c}")

    all_cases = assert_parametrized(TestSomething, as_tuples(c_values), ab_values)
    assert_tests_passed(
        TestSomething,
        tests_run=9,
        failures=[
            (
                f"test_method[{c}-5-6]",
                (
                    'self.assertLess(int(a) + int(b), 11, msg=f"{c}")\n'
                    "AssertionError: 11 not less than 11 : " + f"{c}"
                ),
            )
            for c in c_values
        ],
    )
    assert test_mock.mock_calls == [mocker.call(*chain(*v)) for v in all_cases]


bar = "bar"  # value to mock


def test_usage_with_other_decorators(mocker):
    test_mock = mocker.Mock("test_mock")
    ab_values = [("1", "2"), ("3", "4"), ("5", "6")]
    c_values = (1, 2, 3)

    class TestSomething(TestCase):
        @parametrize("a,b", ab_values)
        @parametrize("c", c_values)
        @mock.patch(f"{__name__}.bar")
        def test_method(self, bar_mock, a, b, c):
            self.assertEqual(test_mock.return_value, test_mock(c, a, b))
            self.assertLess(int(a) + int(b), 11, msg=f"{c}")
            self.assertIsInstance(bar_mock, mock.Mock)
            self.assertIs(bar_mock, bar)

    all_cases = assert_parametrized(TestSomething, as_tuples(c_values), ab_values)
    assert_tests_passed(
        TestSomething,
        tests_run=9,
        failures=[
            (
                f"test_method[{c}-5-6]",
                (
                    'self.assertLess(int(a) + int(b), 11, msg=f"{c}")\n'
                    "AssertionError: 11 not less than 11 : " + f"{c}"
                ),
            )
            for c in c_values
        ],
    )
    assert test_mock.mock_calls == [mocker.call(*chain(*v)) for v in all_cases]


def test_values_overlap(mocker):
    test_mock = mocker.Mock("test_mock")
    ab_values = ((1, "1"), ("1", 1), ("1", "1"), (1, 1))

    class TestSomething(TestCase):
        @parametrize("a,b", ab_values)
        def test_method(self, a, b):
            self.assertEqual(test_mock.return_value, test_mock(b, a))

    assert_parametrized(TestSomething, ab_values)
    assert_tests_passed(TestSomething, tests_run=4)
    # FIXME:
    # tests are generated in expected order, but for some reason executed in different one
    assert sorted(test_mock.mock_calls, key=repr) == sorted(
        (mocker.call(*v) for v in ab_values), key=repr
    )
