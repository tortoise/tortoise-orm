import warnings

from tortoise.functions import Avg, Count, Function, Max, Min, Sum  # noqa

warnings.warn(
    "Please import from tortoise.functions instead of tortoise.aggregation", DeprecationWarning
)
