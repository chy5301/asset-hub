from enum import StrEnum


class FieldType(StrEnum):
    STRING = "string"
    TEXT = "text"
    URL = "url"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    MULTI_ENUM = "multi-enum"
    DATE = "date"
