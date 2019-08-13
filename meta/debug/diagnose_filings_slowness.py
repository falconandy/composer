from pathlib import Path
import json
import logging
import os
from typing import Dict, Iterator
from composer.efile.xmlio import JsonTranslator
from concurrent.futures import ProcessPoolExecutor

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

root_dir: str = "/Volumes/Bulk/efile"
xml_dir: str = os.path.join(root_dir, "xml")
json_dir: str = os.path.join(root_dir, "json")

translate: JsonTranslator = JsonTranslator()

# This works fast. Why does filings.py work slow?
def convert(xml_path: Path):
    xml_fn: str = str(xml_path)
    json_relpath: str = "/".join(xml_fn.split("/")[-3:]).split(".")[0] + ".json"
    json_fn: str = os.path.join(json_dir, json_relpath)
    json_dirpath: str = "/".join(json_fn.split("/")[:-1])
    os.makedirs(json_dirpath, exist_ok=True)
    with open(xml_fn) as xml_fh:
        raw_xml = xml_fh.read()
        if raw_xml.strip() == "":
            logging.error("%s is empty. Skipping." % xml_fn)
            return
    with open(json_fn, "w") as json_fh:
        as_json: Dict = translate(raw_xml)
        json.dump(as_json, json_fh)

xml_paths: Iterator[Path] = Path(xml_dir).glob("**/*.xml")

with ProcessPoolExecutor() as executor:
    executor.map(convert, xml_paths)
