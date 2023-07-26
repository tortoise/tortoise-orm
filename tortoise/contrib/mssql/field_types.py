class NVARCHAR:
    def __init__(self,value):
        self._value = value
    def __str__(self):
        return f"N'{self._value}'"