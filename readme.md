## Drop-in `@pytest.mark.parametrize` replacement working with `unittest.TestCase`

```python
import unittest
from parametrize import parametrize

class TestSomething(unittest.TestCase):

    @parametrize('test_input,expected', [("3+5", 8), ("2+4", 6)])
    def test_eval(self, test_input, expected):
        self.assertEqual(expected, eval(test_input))
```
No need to use additional decorators, custom base classes or metaclasses.

Stacking parametrize decorators is also supported:
```python
import unittest
from parametrize import parametrize

class TestSomething(unittest.TestCase):
    
    @parametrize("x", [0, 1])
    @parametrize("y", [2, 3])
    def test_foo(self, x, y):
        pass
```
`test_foo` will be called with: `(x=0, y=2)`, `(x=1, y=2)`, `(x=0, y=3)`, and `(x=1, y=3)`
