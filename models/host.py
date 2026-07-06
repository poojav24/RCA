class Host:
    def __init__(
        self,
        hostid,
        host,
        name,
        status=None,
        description=None
    ):
        self.hostid = hostid
        self.host = host
        self.name = name
        self.status = status
        self.description = description

    def __str__(self):
        return (
            f"""
Host ID     : {self.hostid}
Host Name   : {self.host}
Display Name: {self.name}
Status      : {self.status}
Description : {self.description}
"""
        )