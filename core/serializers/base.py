"""Shared DRF serializer base classes.

Most of our ``ModelSerializer`` subclasses repeat the same Meta declaration::

    read_only_fields = ["id", "created_at", "updated_at"]

…and frequently forget at least one of them. :class:`TimestampedModelSerializer`
treats every field exposed by ``TimestampMixin`` as read-only by default so
subclasses only need to list real, mutable fields. Override
``extra_read_only_fields`` to add domain-specific read-only columns without
re-listing the timestamp ones.
"""

from __future__ import annotations

from rest_framework import serializers

#: Fields that should always be read-only when present on a model.
TIMESTAMP_READ_ONLY_FIELDS = ("id", "created_at", "updated_at")


class TimestampedModelSerializer(serializers.ModelSerializer):
    """``ModelSerializer`` that auto-marks id + timestamp fields read-only.

    Subclasses can still set ``Meta.read_only_fields`` for any extra fields;
    the timestamp set is merged in automatically. This means a typical
    serializer shrinks from::

        class FooSerializer(serializers.ModelSerializer):
            class Meta:
                model = Foo
                fields = ["id", "name", "created_at", "updated_at"]
                read_only_fields = ["id", "created_at", "updated_at"]

    to::

        class FooSerializer(TimestampedModelSerializer):
            class Meta:
                model = Foo
                fields = ["id", "name", "created_at", "updated_at"]
    """

    def get_extra_kwargs(self):
        extra = super().get_extra_kwargs()
        meta = getattr(self, "Meta", None)
        declared_fields = set(getattr(meta, "fields", []) or [])
        for field in TIMESTAMP_READ_ONLY_FIELDS:
            if declared_fields and field not in declared_fields:
                continue
            field_kwargs = dict(extra.get(field, {}))
            field_kwargs.setdefault("read_only", True)
            extra[field] = field_kwargs
        return extra
