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
