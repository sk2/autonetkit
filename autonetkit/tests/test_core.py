import unittest

from autonetkit.entry import main


class MyTestCase(unittest.TestCase):
    @staticmethod
    def test_something():
        filename = "../example/small_internet.graphml"
        main(filename)


if __name__ == '__main__':
    unittest.main()
