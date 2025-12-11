# scripts/validate_product_page.py
import json
from pathlib import Path
import sys
from jsonschema import validate, ValidationError
from logging import getLogger

logger = getLogger(__name__)

SCHEMA_PATH = Path("schemas/product_page_schema.json")
PRODUCT_PATH = Path("outputs/product_page.json")

def main():
    if not SCHEMA_PATH.exists():
        logger.info("Schema not found:", SCHEMA_PATH)
        return 2
    if not PRODUCT_PATH.exists():
        logger.info("Product output not found:", PRODUCT_PATH)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf8"))
    product = json.loads(PRODUCT_PATH.read_text(encoding="utf8"))

    try:
        validate(instance=product, schema=schema)
    except ValidationError as e:
        logger.info("Validation failed:")
        logger.info(e)
        return 1

    logger.info("Validation passed ✅")
    return 0

if __name__ == "__main__":
    sys.exit(main())
