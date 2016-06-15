from datetime import date, timedelta
import unittest

import lengow_aws_connector


class LengowAwsConnector(unittest.TestCase):

    def test_get_orders_from_lengow(self):
        """
        get_orders_from_lengow() should return orders in a dict.
        """
        start_date = date.today() - timedelta(days=1)
        end_date = date.today()

        orders_data = lengow_aws_connector.get_orders_from_lengow(start_date, end_date)

        # Data should be returned as a dict
        self.assertTrue(isinstance(orders_data, dict))
        self.assertEqual(set(orders_data.keys()), set(['orders', 'orders_count']))

if __name__ == "__main__":
    unittest.main()
