import unittest

from autonetkit.network_model.tests.generics import test_generic_workflow


class MyTestCase(unittest.TestCase):
    def test_something(self):
        # TODO: add asserts for workflow
        test_generic_workflow()


if __name__ == '__main__':
    unittest.main()
