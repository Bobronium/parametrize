[![CI](https://github.com/MrMrRobat/parametrize/workflows/CI/badge.svg?event=push)](https://github.com/MrMrRobat/parametrize/actions?query=event%3Apush+branch%3Amaster+workflow%3ACI)
[![PyPi](https://img.shields.io/pypi/v/parametrize.svg)](https://pypi.python.org/pypi/parametrize)
[![Python Versions](https://img.shields.io/pypi/pyversions/parametrize.svg)](https://github.com/MrMrRobat/parametrize)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Drop-in `@pytest.mark.parametrize` replacement working with `unittest.TestCase`

### Why?
You want to start using `@pytest.mark.parametrize`, but can't simply drop `unittest.TestCase` because you have tons of `self.assert`'s, `setUp`'s `tearDown`'s to rewrite?

With `@parametrize` you can start parameterizing your tests now, and get rid of `unittest.TestCase` later if needed.

## Usage
### Simple example from [pytest docs](https://docs.pytest.org/en/6.2.x/parametrize.html) adapted to unittest
```python
import unittest
from parametrize import parametrize

class TestSomething(unittest.TestCase):

    @parametrize('test_input,expected', [("3+5", 8), ("2+4", 6)])
    def test_eval(self, test_input, expected):
        self.assertEqual(expected, eval(test_input))
```
```py
$ python -m unittest test.py -v
test_eval[2+4-6] (test.TestSomething) ... ok
test_eval[3+5-8] (test.TestSomething) ... ok
test_eval[6*9-42] (test.TestSomething) ... FAIL

======================================================================
FAIL: test_eval[6*9-42] (test.TestSomething)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "parametrize/parametrize.py", line 261, in parametrized_method
    return parametrized_func(*args, **kwargs)
  File "test.py", line 8, in test_eval
    self.assertEqual(expected, eval(test_input))
AssertionError: 42 != 54

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=1)
```
##### You don't need to use additional decorators, custom base classes or metaclasses.

### Stacking parametrize decorators:
```python
import unittest
from parametrize import parametrize

class TestSomething(unittest.TestCase):
    
    @parametrize("x", [0, 1])
    @parametrize("y", [2, 3])
    def test_foo(self, x, y):
        pass
```
`test_foo` will be called with: `(x=0, y=2)`, `(x=1, y=2)`, `(x=0, y=3)`, and `(x=1, y=3)`:
```python
$ python -m unittest test.py -v
test_foo[2-0] (test.TestSomething) ... ok
test_foo[2-1] (test.TestSomething) ... ok
test_foo[3-0] (test.TestSomething) ... ok
test_foo[3-1] (test.TestSomething) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
```
##### Note: even though the tests are always generated in the same order, the execution order is not guaranteed


## Compatibility 
Any `@parametrize` decorator can be converted to `@pytest.mark.parametrize` just by changing its name. 
`@pytest.mark.parametrize` decorator can be converted to `@parametrize` as long as `pytest.param`, `indirect`, `ids` and `scope` are not used.

`@parametrize` works with both `unittest` and `pytest`. However, `pytest` is recommended due to [limitations when using unittest in cli](#parametrized-method-can-be-ran-from-command-line-only-via-pytest). 

Parametrized tests are properly detected and handled by PyCharm. They are displayed as if they were parametrized with `@pytest.mark.parametrize`.


## Limitations
Since `@parametrize` does some kind of magic under the hood, there are some limitations you need to consider.
It's likely you will never face most of them, but if you will, `@parametrize` will let you know with an error:

- ### All parametrization must be done via decorators
    :white_check_mark: OK
    ```python
    @parametrize('a', (1, 2))
    def f(a):
        ...
    ```   
    :x: Won't work:
    ```python
    def f(a):
        ...
  
    parametrize('a', (1, 2))(func)
    ```
    ```py
    RuntimeError: Unable to find any parametrizes in decorators, please rewrite decorator name to match any of detected names @{'parametrize'}
    ```
    
- ### All other decorators must be defined before parametrize decorators
    :white_check_mark: OK:
    ```py
    @parametrize("a", (1, 2))
    @parametrize("b", (2, 3))
    @mock.patch(f"{__name__}.bar", "foo")
    def f(a, b):
        return a, b
    ```
    :x: Won't work:
    ```python
    @mock.patch(f"{__name__}.bar", "foo")
    @parametrize("a", (1, 2))
    @parametrize("b", (2, 3))
    def f(a, b):
        return a, b
    ```
    ```py
    TypeError: @mock.patch(f"{__name__}.bar", "foo") must be defined before any of @{'parametrize'} decorators
    ```

- ### If you assign parametrized decorator to variable, it must be accessible from `locals()` or `globals()` namespaces:
    :white_check_mark: OK:
    ```py
    a_parameters = parametrize("a", (4, 5))  # defined in module
    def func():  
        class TestSomething:
            b_parameters = parametrize("b", (1, 2, 3))
  
            @b_parameters  # b_parameters found in locals()
            @a_parameters  # a_parameters found in globals()
            def test_method(self, a, b):
                ...
    ```
    :x: Won't work:
    ```py
    def func():
        # defined in function scope
        a_parameters = parametrize("a", (4, 5))
    
        class TestSomething:
            print('a_parameters' in {**globals(), **locals()})  # False
    
            @a_parameters  # accessed in class body scope
            def test_method(self, a, b):
                ...
    ```
    ```py
    RuntimeError: Unable to find any parametrizes in decorators, please rewrite decorator name to match any of detected names @{'parametrize'}  
    ```

- ### Parametrized method can be ran from command line only via pytest:
    `$ cat test.py`
    ```py
    import unittest
    from parametrize import parametrize
    
    class TestSomething(unittest.TestCase):
        @parametrize('a', (1, 2))
        def test_something(self, a):
            self.assertIsInstance(a, int)
    ```
    :white_check_mark: OK:
    
    `$ pytest test.py::TestSomething::test_something -v`
    ```py
     ...    
     test.py::TestSomething.test_something[1] ✓                                       50% █████     
     test.py::TestSomething.test_something[2] ✓                                      100% ██████████
    
    Results (0.07s):
           2 passed
    ```
    :x: Won't work:
    
    `$ python -m unittest test.TestSomething.test_something`
    ```py
    Traceback (most recent call last):
      ...
    TypeError: don't know how to make test from: test_something[...]
    ```
- ### `@parametrize` cannot be used in interactive environments like REPL (It works in IPython though)
- ### `@parametrize` cannot be used in cythonized code  
