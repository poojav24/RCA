class Metric:

    def __init__(
        self,
        itemid,
        name,
        key,
        value_type=None,
        units=None,
        lastvalue=None
    ):

        self.itemid = itemid
        self.name = name
        self.key = key
        self.value_type = value_type
        self.units = units
        self.lastvalue = lastvalue

    def __str__(self):

        return (
            f"""
Item ID    : {self.itemid}
Metric     : {self.name}
Key        : {self.key}
Value      : {self.lastvalue}
Units      : {self.units}
"""
        )