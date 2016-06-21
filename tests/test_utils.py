import unittest

from src import utils


class UtilsTestCase(unittest.TestCase):

    def test_decompose_dict(self):
        multi_leveled_dict = {
            "pk1": "v1",
            "pk2": {"ck1": "v2", "ck2": "v3"},
            "pk3": [{"ck3": "v4", "ck4": "v5"}, {"ck3": "v6", "ck4": "v7"}],
            "pk4": ["v8", "v9"]
        }

        expected_dict = {
            "pk1": "v1", "pk2.ck1": "v2", "pk2.ck2": "v3", "pk3.member.1.ck3": "v4",
            "pk3.member.1.ck4": "v5", "pk3.member.2.ck3": "v6", "pk3.member.2.ck4": "v7",
            "pk4.1": "v8", "pk4.2": "v9"
        }

        self.assertEqual(utils.enumerate_data(multi_leveled_dict), expected_dict)


if __name__ == "__main__":
    unittest.main()
