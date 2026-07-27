import re

from models.expression import Expression


class ExpressionParser:

    def parse(self, expression):

        print("\nRaw Expression")
        print(expression)

        # ----------------------------
        # Function
        # ----------------------------

        function = ""

        m = re.match(r"([a-zA-Z]+)\(", expression)

        if m:
            function = m.group(1)

        # ----------------------------
        # Host
        # ----------------------------

        host = ""

        m = re.search(r"/([^/]+)/", expression)

        if m:
            host = m.group(1)

        # ----------------------------
        # Item Key
        # ----------------------------

        item_key = ""

        m = re.search(
            r"/[^/]+/([a-zA-Z0-9._]+)",
            expression
        )

        if m:
            item_key = m.group(1)

        # ----------------------------
        # Parameters
        # ----------------------------

        parameters = ""

        m = re.search(r"\[(.*?)\]", expression)

        if m:
            parameters = m.group(1)

        if host == "" or item_key == "":

            return None

        return Expression(

            function,

            host,

            item_key,

            parameters,

            expression

        )