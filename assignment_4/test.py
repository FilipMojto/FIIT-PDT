import logging

logger = logging.getLogger("import_logger")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("import.log")
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

name = "test_file.jsonl.gz"
success = 1000
failed = 10
logger.info(f"{name}: success={success}, failed={failed}")
for handler in logger.handlers:
    handler.flush()