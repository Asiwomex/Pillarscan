"""Bucket listing shared by the S3 checks."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def bucket_names(s3: Any) -> Iterator[str]:
    for page in s3.get_paginator("list_buckets").paginate():
        for bucket in page.get("Buckets", []):
            yield bucket["Name"]


def bucket_arn(name: str) -> str:
    return f"arn:aws:s3:::{name}"


def bucket_region(s3: Any, name: str) -> str:
    location: str | None = s3.get_bucket_location(Bucket=name)["LocationConstraint"]
    # S3 reports us-east-1 as null and the oldest eu-west-1 buckets as "EU".
    if location is None:
        return "us-east-1"
    return "eu-west-1" if location == "EU" else location
