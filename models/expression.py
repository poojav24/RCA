class Expression:

    def __init__(
        self,
        function,
        host,
        item_key,
        parameters,
        raw_expression
    ):

        self.function = function
        self.host = host
        self.item_key = item_key
        self.parameters = parameters
        self.raw_expression = raw_expression

    def __str__(self):

        return f"""
Expression
----------------------------------------
Function    : {self.function}
Host        : {self.host}
Item Key    : {self.item_key}
Parameters  : {self.parameters}
"""