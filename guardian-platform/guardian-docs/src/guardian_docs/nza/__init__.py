"""NZA document register. The meaning of "NZA" was not given; treated as a generic register."""

from ..register import Document, Register  # noqa: F401


def new_register():
    return Register("NZA")
