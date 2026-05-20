import sys
import time
from utils import get_logger

logger = get_logger("main")


def run_pipeline():
    """Execute the full ETL pipeline."""
    logger.info("=" * 60)
    logger.info("  MovieLens ETL Pipeline - Starting")
    logger.info("=" * 60)

    start = time.perf_counter()

    # --- Extract ---
    logger.info("STEP 1/3 ► Extract")
    from extract import run_extract
    raw = run_extract()

    # --- Transform ---
    logger.info("STEP 2/3 ► Transform")
    from transform import run_transform
    transformed = run_transform(raw)

    # --- Load ---
    logger.info("STEP 3/3 ► Load")
    from load import run_load
    run_load(transformed)

    elapsed = time.perf_counter() - start
    logger.info("=" * 60)
    logger.info("  Pipeline completed successfully in %.1f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)
