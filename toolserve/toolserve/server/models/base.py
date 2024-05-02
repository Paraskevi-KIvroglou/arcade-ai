#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Annotated

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)

from toolserve.server.utils.timezone import timezone

# Common Mapped type primary key, manual addition required, refer to the following usage
# MappedBase -> id: Mapped[id_key]
# DataClassBase && Base -> id: Mapped[id_key] = mapped_column(init=False)
id_key = Annotated[
    int,
    mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-999,
        comment="Primary key id",
    ),
]


# Mixin: An object-oriented programming concept, makes the structure clearer, `Wiki <https://en.wikipedia.org/wiki/Mixin/>`__
class UserMixin(MappedAsDataclass):
    """User Mixin data class"""

    create_user: Mapped[int] = mapped_column(sort_order=998, comment="Creator")
    update_user: Mapped[int | None] = mapped_column(
        init=False, default=None, sort_order=998, comment="Modifier"
    )


class DateTimeMixin(MappedAsDataclass):
    """Datetime Mixin data class"""

    created_time: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=timezone.now,
        sort_order=999,
        comment="Creation time",
    )
    updated_time: Mapped[datetime | None] = mapped_column(
        init=False, onupdate=timezone.now, sort_order=999, comment="Update time"
    )


class MappedBase(DeclarativeBase):
    """
    Declarative base class, the original DeclarativeBase class, serves as the parent class for all base or data model classes

    `DeclarativeBase <https://docs.sqlalchemy.org/en/20/orm/declarative_config.html>`__
    `mapped_column() <https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.mapped_column>`__
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class DataClassBase(MappedAsDataclass, MappedBase):
    """
    Declarative data class base class, integrates with data classes, allows for advanced configurations, but you must be aware of its characteristics, especially when used with DeclarativeBase

    `MappedAsDataclass <https://docs.sqlalchemy.org/en/20/orm/dataclasses.html#orm-declarative-native-dataclasses>`__
    """  # noqa: E501

    __abstract__ = True


class Base(DataClassBase, DateTimeMixin):
    """
    Declarative Mixin data class base class, integrates data classes, includes the Mixin data class basic table structure, you can simply understand it as a data class base class with basic table structure
    """  # noqa: E501

    __abstract__ = True