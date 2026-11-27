"""Generate contracts from application schemas; --check fails on drift."""

import argparse
import json
from pathlib import Path

import yaml
from app.main import create_app
from app.schemas.api import CampaignStatus, CampaignType, PaymentStatus

ROOT = Path(__file__).resolve().parents[1]


def typescript_type(schema):
    """Translate the JSON-schema subset emitted by our Pydantic models; fail on unknown types."""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[1]
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])
    for union in ["anyOf", "oneOf"]:
        if union in schema:
            return (
                "(" + " | ".join(typescript_type(item) for item in schema[union]) + ")"
            )
    kind = schema.get("type")
    if kind == "array":
        return "Array<" + typescript_type(schema["items"]) + ">"
    if kind == "object":
        if "properties" in schema:
            required = set(schema.get("required", []))
            fields = [
                json.dumps(key)
                + ("" if key in required else "?")
                + ": "
                + typescript_type(value)
                + ";"
                for key, value in schema["properties"].items()
            ]
            return "{ " + " ".join(fields) + " }"
        additional = schema.get("additionalProperties", True)
        value_type = (
            typescript_type(additional) if isinstance(additional, dict) else "unknown"
        )
        return "Record<string, " + value_type + ">"
    primitives = {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }
    if kind in primitives:
        return primitives[kind]
    if not schema or kind is None:
        return "unknown"
    raise ValueError(f"Unsupported schema kind: {kind}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schema = create_app().openapi()
    outputs = {
        ROOT / "apps/web/src/lib/generated/backend.ts": (
            "// Generated from FastAPI OpenAPI by scripts/export_contracts.py. Do not edit.\n"
            + "\n".join(
                "export type " + name + " = " + typescript_type(value) + ";"
                for name, value in sorted(schema["components"]["schemas"].items())
            )
            + "\n"
        ),
        ROOT / "contracts/openapi.yaml": yaml.safe_dump(schema, sort_keys=True),
        ROOT / "contracts/enums.json": json.dumps(
            {
                "payment_status": list(PaymentStatus),
                "campaign_type": list(CampaignType),
                "campaign_status": list(CampaignStatus),
            },
            indent=2,
        )
        + "\n",
        ROOT / "contracts/schemas/api.json": json.dumps(
            schema["components"]["schemas"], indent=2, sort_keys=True
        )
        + "\n",
    }
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Contract drift: regenerate {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


if __name__ == "__main__":
    main()
