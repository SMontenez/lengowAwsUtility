from datetime import date, datetime, timedelta
import random
import time
import unittest

from mws import mws

from src import lengow_aws_connector


class LengowAwsConnectorTestCase(unittest.TestCase):

    def setUp(self, *args, **kwargs):
        super(LengowAwsConnectorTestCase, self).setUp(*args, **kwargs)
        self.MWS_ACCESS_KEY = lengow_aws_connector.MWS_ACCESS_KEY
        self.MWS_SECRET_KEY = lengow_aws_connector.MWS_SECRET_KEY
        self.MWS_MERCHANT_ID = lengow_aws_connector.MWS_MERCHANT_ID
        self.orders_data = lengow_aws_connector.get_orders_from_lengow(
            date.today() - timedelta(days=1), date.today())

    def test_get_orders_from_lengow(self):
        """
        get_orders_from_lengow() should return orders in a dict.
        """
        # Data should be returned as a dict
        self.assertTrue(isinstance(self.orders_data, dict))
        self.assertEqual(set(self.orders_data.keys()), set(["orders", "orders_count"]))

    def test_create_aws_order(self):
        """
        Validate that the method correctly creates the order via the amazon API. We directly cancel
        this order as we just want to test that it works.
        """
        # Get a valid SKU to test ie one that is in inventory
        inv = mws.Inventory(
            access_key=self.MWS_ACCESS_KEY, secret_key=self.MWS_SECRET_KEY,
            account_id=self.MWS_MERCHANT_ID, region="FR")
        inv_supply = inv.list_inventory_supply(
            datetime=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))

        self.assertEqual(inv_supply.response.status_code, 200)

        # A random SKU of an article we have in our inventory
        valid_sku = random.choice(
            inv_supply.parsed["InventorySupplyList"]["member"])["SellerSKU"]["value"]

        # Orders that will pass all tests to be created by our method
        valid_orders = [
            o for o in self.orders_data["orders"] if
            o["marketplace"] not in lengow_aws_connector.not_allowed_marketplaces and
            o["order_status"]["lengow"] == "processing"]

        # Get one of these orders
        test_order = valid_orders[0]
        # Use a fake unique order id
        test_order["order_id"] = "{:{df}}".format(datetime.now(), df="%Y%m%dT%H:%M:%S")
        # Modify its SKU so that AWS doesn't reject our request
        test_order["cart"]["products"] = [test_order["cart"]["products"][0]]
        test_order["cart"]["products"][0]["sku"] = valid_sku

        # Max 40 chars
        test_order_id = "{}_{}".format(test_order["marketplace"], test_order["order_id"])[:40]

        # Save order_id so we can manually handle it if test breaks
        with open("tests/data/test_order_ids.json", "a+") as file:
            file.write("{}\n".format(test_order_id))

        # Try to create an order via our method
        try:
            req = lengow_aws_connector.create_aws_order(test_order, test_order_id)
        except mws.MWSError as e:
            print(e.response.text)
        self.assertEqual(req.response.status_code, 200)

        # Wait a little so first request is processed
        time.sleep(5)
        # Cancel the order as we don't want it to be really activated
        rep = 0
        while rep != 200:
            try:
                req = lengow_aws_connector.cancel_aws_order(test_order_id)
            except mws.MWSError as e:
                print(e.response.text)
                break
            rep = req.response.status_code


if __name__ == "__main__":
    unittest.main()
