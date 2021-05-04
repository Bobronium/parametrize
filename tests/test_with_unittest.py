from io import StringIO
from itertools import chain, product
from typing import Type
from unittest import TestCase, TextTestRunner, defaultTestLoader

from parametrize import parametrize
from parametrize.parametrize import UnparametrizedMethod


def run_unittests(case: Type[TestCase]):
    suite = defaultTestLoader.loadTestsFromTestCase(case)
    return TextTestRunner(stream=StringIO()).run(suite)


def test_simple_parametrize_class(mocker):
    test_mock = mocker.Mock("test_mock")
    values = [1, 2, 3]

    class TestSomething(TestCase):
        @parametrize("a", values)
        def test_method(self, a):
            self.assertEqual(test_mock.return_value, test_mock(a))
            self.assertIn(a, (1, 2))

    assert isinstance(TestSomething.test_method, UnparametrizedMethod)

    test_methods = [f"test_method[{v}]" for v in values]
    assert set(test_methods) & set(TestSomething.__dict__)

    result = run_unittests(TestSomething)
    assert result.testsRun == 3
    assert not result.errors
    assert not result.skipped
    assert len(result.failures) == 1

    failed_test_case, fail_message = result.failures[0]
    assert failed_test_case._testMethodName == "test_method[3]"
    assert ("self.assertIn(a, (1, 2))\n" "AssertionError: 3 not found in (1, 2)") in fail_message

    assert test_mock.mock_calls == [mocker.call(v) for v in values]


def test_multiple_arg_parametrize_class(mocker):
    test_mock = mocker.Mock("test_mock")
    values = [("1", "2"), ("3", "4"), ("5", "6")]

    class TestSomething(TestCase):
        @parametrize("a,b", values)
        def test_method(self, *, a, b):
            self.assertEqual(test_mock.return_value, test_mock(a, b))
            self.assertLess(int(a) + int(b), 11)

    assert isinstance(TestSomething.test_method, UnparametrizedMethod)

    test_methods = [f"test_method[{'-'.join(v)}]" for v in values]
    assert set(test_methods) & set(TestSomething.__dict__)

    result = run_unittests(TestSomething)
    assert result.testsRun == 3
    assert not result.errors
    assert not result.skipped
    assert len(result.failures) == 1

    failed_test_case, fail_message = result.failures[0]
    assert failed_test_case._testMethodName == "test_method[5-6]"
    assert (
        "self.assertLess(int(a) + int(b), 11)" "\nAssertionError: 11 not less than 11"
    ) in fail_message

    assert test_mock.mock_calls == [mocker.call(*v) for v in values]


def test_multiple_parametrize_class(mocker):
    test_mock = mocker.Mock("test_mock")
    ab_values = [("1", "2"), ("3", "4"), ("5", "6")]
    c_values = (1, 2, 3)

    class TestSomething(TestCase):
        @parametrize("a,b", ab_values)
        @parametrize("c", c_values)
        def test_method(self, a, b, c):
            self.assertEqual(test_mock.return_value, test_mock(c, a, b))
            self.assertLess(int(a) + int(b), 11)

    assert isinstance(TestSomething.test_method, UnparametrizedMethod)

    all_cases = list(product([(v,) for v in c_values], ab_values))
    test_methods = [f"test_method[{'-'.join(map(str, chain(*case)))}]" for case in all_cases]
    assert set(test_methods) & set(TestSomething.__dict__)

    result = run_unittests(TestSomething)
    assert result.testsRun == 9
    assert not result.errors
    assert not result.skipped
    assert len(result.failures) == 3

    for c_value, (failed_test_case, fail_message) in zip(c_values, result.failures):
        assert failed_test_case._testMethodName == f"test_method[{c_value}-5-6]"
        assert (
            "self.assertLess(int(a) + int(b), 11)" "\nAssertionError: 11 not less than 11"
        ) in fail_message

    assert test_mock.mock_calls == [mocker.call(*chain(*v)) for v in all_cases]
