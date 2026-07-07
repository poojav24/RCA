class Metric:

    def __init__(
        self,
        itemid,
        name,
        key,
        value_type=None,
        units="",
        lastvalue=""
    ):

        self.itemid = itemid
        self.name = name
        self.key = key
        self.value_type = value_type
        self.units = units
        self.lastvalue = lastvalue

    def __str__(self):

        return f"""
Metric
-------------------------
Name  : {self.name}
Key   : {self.key}
Value : {self.lastvalue} {self.units}
"""