import json
import logging
import os
import urllib.parse
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

s3_client = boto3.client("s3")


def parse_single_line(line: str) -> dict[str, Any]:
    """Parse one line from an S3 object.

    Supported formats:
      1. JSON object: {"account_id":"123","amount":12.45}
      2. key=value CSV: account_id=123,amount=12.45,status=NEW
      3. Plain text: any other one-line payload
    """
    cleaned = line.strip()
    if not cleaned:
        raise ValueError("Line is empty or contains only whitespace.")

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return {"format": "json", "data": parsed}
        return {"format": "json_value", "data": parsed}
    except json.JSONDecodeError:
        pass

    if "=" in cleaned:
        pairs: dict[str, str] = {}
        for part in cleaned.split(","):
            if "=" not in part:
                raise ValueError(f"Invalid key=value segment: {part}")
            key, value = part.split("=", 1)
            pairs[key.strip()] = value.strip()
        return {"format": "key_value", "data": pairs}

    return {"format": "plain_text", "data": cleaned}


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    records = event.get("Records", [])
    processed: list[dict[str, Any]] = []

    if not records:
        logger.warning("No S3 records found in event")
        return {"processed_count": 0, "items": []}

    for record in records:
        bucket = key = "<unknown>"
        try:
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

            logger.info("Processing S3 object", extra={"bucket": bucket, "key": key})

            response = s3_client.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read().decode("utf-8")
            lines = body.splitlines()

            if len(lines) != 1:
                raise ValueError(f"Expected a single-line file, found {len(lines)} lines.")

            parsed = parse_single_line(lines[0])
            item = {"bucket": bucket, "key": key, "parsed": parsed}
            processed.append(item)

            logger.info("Successfully parsed S3 object", extra=item)

        except (ClientError, UnicodeDecodeError, ValueError, KeyError) as exc:
            logger.exception(
                "Failed to process S3 object",
                extra={"bucket": bucket, "key": key, "error": str(exc)},
            )
            raise

    return {"processed_count": len(processed), "items": processed}
