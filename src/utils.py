def enumerate_data(data, parent_key=""):
    """
    Recursively transform a multi-leveled dictionnary into a one-leveled dictionnary so all its
    elements can be use in an AWS api call.

    >>> enumerate_data({"A": val1, "B": {"AA": val2, "BB": val3}, "C": [val4, val5]})
    {"A": val1, "B.AA": val2, "B.BB": val3, "C.member.1": val4, "C.member.2": val5}
    """

    params = {}

    if isinstance(data, dict):
        for child_key, value in data.items():
            # Initialize for the first round, then combine if in further rounds of iteration
            comb_key = child_key if not parent_key else "{}.{}".format(parent_key, child_key)
            params.update(enumerate_data(value, comb_key))
    elif isinstance(data, list):
        for i, elt in enumerate(data):
            # Initialize for the first round, then combine if in further rounds of iteration
            comb_key = "{}{}.{:d}".format(
                    parent_key, '.member' if isinstance(elt, dict) else '', i+1)
            params.update(enumerate_data(elt, comb_key))
    elif isinstance(data, basestring) or isinstance(data, (int, float)):
        params[parent_key] = data

    return params
