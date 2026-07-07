from tortoise.contrib.mysql.fields import GeometryField


def test_geometry_field_type() -> None:
    """GeometryField must declare a concrete ``field_type``.

    A single-base ``Field`` subclass does not get ``field_type`` assigned by the
    ``_FieldMeta`` metaclass (that only fires for multiple bases), so an explicit
    attribute is required. When it is missing, ``field_type`` is ``None`` and the
    base value converters raise ``TypeError`` from ``isinstance(value, None)``.
    """
    assert GeometryField().field_type is str


def test_geometry_field_to_python_value() -> None:
    field = GeometryField()
    # ``None`` must pass through untouched.
    assert field.to_python_value(None) is None
    # A concrete DB value must be converted without raising.
    assert field.to_python_value("POINT(1 1)") == "POINT(1 1)"


def test_geometry_field_to_db_value() -> None:
    field = GeometryField()
    assert field.to_db_value(None, None) is None
    assert field.to_db_value("POINT(1 1)", None) == "POINT(1 1)"
