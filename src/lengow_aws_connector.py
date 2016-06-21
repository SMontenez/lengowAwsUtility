from datetime import date, timedelta
import json
import os
import requests

from mws import mws

from utils import enumerate_data

BASE_URL = "http://api.lengow.com/V2"

ACCOUNT_ID = 7217
GROUP_ID = 15909
FLUX_ID = "orders"

# MWS Credentials
MWS_ACCESS_KEY = os.environ.get("MWS_ACCESS_KEY")
MWS_MERCHANT_ID = os.environ.get("MWS_MERCHANT_ID")
MWS_SECRET_KEY = os.environ.get("MWS_SECRET_KEY")

# AWS Credentials
AWS_REGION = os.environ.get("AWS_REGION")
AWS_APP_ID = os.environ.get("AWS_APP_ID")
AWS_APP_SECRET = os.environ.get("AWS_APP_SECRET")
AWS_BUCKET = os.environ.get("AWS_BUCKET")

not_allowed_marketplaces = ["amazon"]

order_comment = """ Merci pour votre commande. Pour les retours, veuillez prendre contact avec nous
                    et retourner le produit dans son emballage d'origine"""

fulfilled_orders_filename = "data/fulfilled_orders.json"


def get_orders_from_lengow(
        start_date, end_date, account_id=ACCOUNT_ID, group_id=GROUP_ID, flux_id=FLUX_ID,
        order_status="all", response_format="json"):
    """
    Return from Lengow api all the orders made between start_date and end_date.
    """
    date_range = "{start_date:{df}}/{end_date:{df}}".format(
            start_date=start_date, end_date=end_date, df="%Y-%m-%d")
    flux_filter = "{account_id:d}/{group_id:d}/{flux_id}".format(
            account_id=account_id, group_id=group_id, flux_id=flux_id)
    suffix = "commands/{order_status}/{response_format}".format(
            order_status=order_status, response_format=response_format)
    url = "{base_url}/{date_range}/{flux_filter}/{suffix}/".format(
            base_url=BASE_URL, date_range=date_range, flux_filter=flux_filter, suffix=suffix)

    return requests.get(url).json()


def preview_aws_shipment(order):
    """
    Process the data returned by Lengow API, and adapt it
    for the AWS GetFulfillmentPreview endpoint
    """

    # Data that will be sent to AWS GetFulfillmentPreview method
    aws_order_data = {}

    # The destination address for the fulfillment order.
    address = order["delivery_address"]
    country_iso = address["delivery_country_iso"]
    aws_order_data["Address"] = {
        "Name": u"{firstname} {lastname}".format(
            firstname=address["delivery_firstname"],
            lastname=address["delivery_lastname"]).title(),
        "Line1": address["delivery_address"].title(),
        "Line2": address["delivery_address_2"].title(),
        "Line3": address["delivery_address_complement"].title(),
        "City": address["delivery_city"].title(),
        "StateOrProvinceCode": address["delivery_zipcode"],
        "PostalCode": address["delivery_zipcode"],
        "CountryCode": country_iso,
        "PhoneNumber": address["delivery_phone_mobile"]
    }
    # As specified in AWS documentation, don"t include city if country is JP.
    if country_iso == "JP":
        aws_order_data["Address"].pop("City")

    aws_order_data["Items"] = []
    for product in order["cart"]["products"]:
        item = {
            "SellerSKU": product["sku"],
            "SellerFulfillmentOrderItemId": product["sku"],
            "Quantity": product["quantity"]
        }
        aws_order_data["Items"].append(item)

    mws_shipments = mws.OutboundShipments(
        access_key=MWS_ACCESS_KEY, secret_key=MWS_SECRET_KEY,
        account_id=MWS_MERCHANT_ID, region="FR")

    data = dict(Action="GetFulfillmentPreview")
    data.update(enumerate_data(aws_order_data))
    return mws_shipments.make_request(data, "POST")


def create_aws_order(lengow_order, order_id):
    """
    Process the data returned by Lengow api, to adapat it for the AWS CreateFulfillmentOrder.
    """
    if (
            lengow_order["marketplace"] in not_allowed_marketplaces or
            lengow_order["order_status"]["lengow"] != "processing"):
        return

    # Data that will be sent to AWS CreateFulfillmentOrder method
    aws_order_data = {}

    aws_order_data["SellerFulfillmentOrderId"] = order_id
    aws_order_data["DisplayableOrderId"] = order_id

    # The date of the fulfillment order. Displays as the order date in customer-facing materials
    # such as the outbound shipment packing slip.
    aws_order_data["DisplayableOrderDateTime"] = "{date}T{time}".format(
            date=lengow_order["order_purchase_date"], time=lengow_order["order_purchase_heure"])

    # Order-specific text that appears in customer-facing materials such as the outbound shipment
    # packing slip.
    aws_order_data["DisplayableOrderComment"] = order_comment

    aws_order_data["ShippingSpeedCategory"] = (
            "Expedited" if float(lengow_order["order_shipping"]) > 0 else "Standard")

    # The destination address for the fulfillment order.
    address = lengow_order["delivery_address"]
    country_iso = address["delivery_country_iso"]
    aws_order_data["DestinationAddress"] = {
            "Name": "{firstname} {lastname}".format(
                firstname=address["delivery_firstname"].title(),
                lastname=address["delivery_lastname"]).title(),
            "Line1": address["delivery_address"].title(),
            "Line2": address["delivery_address_2"].title(),
            "Line3": address["delivery_address_complement"].title(),
            "City": address["delivery_city"].title(),
            "StateOrProvinceCode": address["delivery_zipcode"],
            "PostalCode": address["delivery_zipcode"],
            "CountryCode": country_iso,
            "PhoneNumber": address["delivery_phone_mobile"]
    }
    # As specified in AWS documentation, don"t include city if country is JP.
    if country_iso == "JP":
        aws_order_data["DestinationAddress"].pop("City")

    aws_order_data["Items"] = []
    for product in lengow_order["cart"]["products"]:
        item = {
                "SellerSKU": product["sku"],
                "SellerFulfillmentOrderItemId": product["sku"],
                "Quantity": product["quantity"],
                "PerUnitDeclaredValue": {
                    "Value": product["price_unit"], "CurrencyCode": lengow_order["order_currency"]
                }
        }
        aws_order_data["Items"].append(item)

    # aws_order_data["NotificationEmailList"] = [address["delivery_email"]]

    mws_shipments = mws.OutboundShipments(
        access_key=MWS_ACCESS_KEY, secret_key=MWS_SECRET_KEY,
        account_id=MWS_MERCHANT_ID, region="FR")

    data = dict(Action="CreateFulfillmentOrder")
    data.update(enumerate_data(aws_order_data))
    return mws_shipments.make_request(data, "POST")


def cancel_aws_order(order_id):
    """
    Cancel a previously made order with its id.
    """
    mws_shipments = mws.OutboundShipments(
        access_key=MWS_ACCESS_KEY, secret_key=MWS_SECRET_KEY,
        account_id=MWS_MERCHANT_ID, region="FR")

    data = dict(Action="CancelFulfillmentOrder", SellerFulfillmentOrderId=order_id)
    return mws_shipments.make_request(data, "POST")


def fulfill_lengow_orders(start_date, end_date):
    """
    Get orders to fulfill from Lengow API, and fulfill them via AWS CreateFulfillmentOrder endpoint
    when they aren"t already fulfilled.
    """
    # Get the ids if orders already fulfilled
    with open(fulfilled_orders_filename, "r") as file:
        already_fulfilled_orders = json.load(file)

    lengow_orders = get_orders_from_lengow(start_date, end_date)["orders"]
    for order in lengow_orders:
        # Unique ID for this order
        order_id = "{marketplace}_{order_id}".format(
            marketplace=order["marketplace"], order_id=order["order_id"])
        if order_id in already_fulfilled_orders:
            continue
        else:
            already_fulfilled_orders.append(order_id)
            create_aws_order(order, order_id)

    # Write the ids of the fulfilled orders
    with open(fulfilled_orders_filename, "w") as file:
        json.dump(file, already_fulfilled_orders)


if __name__ == "__main__":

    start_date = date.today() - timedelta(days=1)
    end_date = date.today()

    fulfill_lengow_orders(start_date, end_date)
