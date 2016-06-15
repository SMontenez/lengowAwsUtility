import requests

BASE_URL = "http://api.lengow.com/V2"

ACCOUNT_ID = 7217
GROUP_ID = 15909
FLUX_ID = "orders"


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
