import json
import logging
import os
import random
import shutil
import string
from typing import Iterator, List, Optional

from botocore.exceptions import ClientError

from composer.aws.efile.bucket import efile_bucket
from composer.aws.s3 import Tuple, Dict, Iterable, Bucket
from composer.efile.structures.metadata import FilingMetadata
from functools import lru_cache

from composer.efile.xmlio import JsonTranslator
from composer.futures import run_on_process_pool, run_on_thread_pool


@lru_cache(maxsize=4194304)
def _ein_path(basepath: str, ein: str) -> str:
    first, second = ein[0:3], ein[3:6]
    ein_path: str = os.path.join(basepath, first, second)
    os.makedirs(ein_path, exist_ok=True)
    return ein_path

def _get_download_targets(changes: Iterable[Tuple[str, Dict[str, FilingMetadata]]], target_path: str) \
        -> Iterator[Tuple[str, str]]:
    for ein, updates in changes:
        ein_path = _ein_path(target_path, ein)
        for filing_md in updates.values():
            irs_efile_id: str = filing_md.irs_efile_id
            yield ein_path, irs_efile_id


# TODO Add lots of timing to this once it's working

def _tmpdir(tmp_base) -> str:
    while True:
        rand_str = ''.join([random.choice(string.ascii_letters) for _ in range(10)])
        dirname: str = os.path.join(tmp_base, rand_str)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
            return dirname

class RetrieveEfiles:
    """Download any new e-files as XML from S3 and store them in a temporary directory. Convert them to JSON files, also
    stored in a temporary directory. Yield a map of EIN -> (map of period -> JSON file path)."""

    def __init__(self, tmp_base: str = "/tmp", no_cleanup: bool = False):
        self.xml_cache_dir: str = _tmpdir(tmp_base)  # Official temp directory package makes things too hard
        self.json_cache_dir: str = _tmpdir(tmp_base)
        self.no_cleanup: bool = no_cleanup

    def _get_json_tuples(self, changes: Iterable[Tuple[str, Dict[str, FilingMetadata]]]) \
            -> Iterator[Tuple[str, Dict[str, str]]]:
        for ein, updates in changes:
            ein_path = _ein_path(self.json_cache_dir, ein)
            json_paths: Dict[str, str] = {}
            for period, filing_md in updates.items():
                irs_efile_id: str = filing_md.irs_efile_id
                json_paths[period] = os.path.join(ein_path, "%s.json" % irs_efile_id)
            yield ein, json_paths

    def _convert_all(self, changes: Iterable[Tuple[str, Dict[str, FilingMetadata]]]):
        """Convert all XML files into JSON files. CPU-bound, so process pool."""
        logging.info("Converting XML to JSON.")
        run_on_process_pool(_xml_to_json, list(changes), self.xml_cache_dir, self.json_cache_dir)

    def _download_all(self, changes: Iterable[Tuple[str, Dict[str, FilingMetadata]]]):
        """Download all XML files to local storage. I/O-bound, so thread pool."""
        logging.info("Downloading new XML files.")
        targets: List[Tuple[str, str]] = list(_get_download_targets(changes, self.xml_cache_dir))
        run_on_process_pool(_download_xml_on_process, targets)
        # run_on_thread_pool(_download_xml_on_thread, targets, self.bucket, workers_count=os.cpu_count()*10)

    def __call__(self, changes: Iterable[Tuple[str, Dict[str, FilingMetadata]]]) \
            -> Iterator[Tuple[str, Dict[str, str]]]:
        self._download_all(changes)
        self._convert_all(changes)
        yield from self._get_json_tuples(changes)

    def __del__(self):
        if not self.no_cleanup:
            shutil.rmtree(self.xml_cache_dir, ignore_errors=True)
            shutil.rmtree(self.json_cache_dir, ignore_errors=True)

    @staticmethod
    def get_bucket() -> Bucket:
        return efile_bucket()

def _download_xml_on_process(targets: List[Tuple[str, str]]):
    bucket = RetrieveEfiles.get_bucket()
    run_on_thread_pool(_download_xml_on_thread, targets, bucket, workers_count=os.cpu_count()*5)


def _download_xml_on_thread(targets: List[Tuple[str, str]], bucket: Optional[Bucket]):
    for target in targets:
        ein_path, irs_efile_id = target  # types: str, str
        s3_key: str = "%s_public.xml" % irs_efile_id
        try:
            raw_xml: str = bucket.get_obj_body(s3_key)
        except ClientError as e:
            logging.warning("can't get object by key '%s': %s", s3_key, e)
            continue
        destination: str = os.path.join(ein_path, s3_key)
        with open(destination, "w") as fh:
            fh.write(raw_xml)


def _xml_to_json(changes: List[Tuple[str, Dict[str, FilingMetadata]]], xml_cache_dir: str, json_cache_dir: str) -> None:
    translate = JsonTranslator()
    for change in changes:
        (ein, updates) = change
        for filing_md in updates.values():
            irs_efile_id: str = filing_md.irs_efile_id
            xml_path: str = os.path.join(_ein_path(xml_cache_dir, ein), "%s_public.xml" % irs_efile_id)
            json_path: str = os.path.join(_ein_path(json_cache_dir, ein), "%s.json" % irs_efile_id)
            try:
                with open(xml_path) as xml_fh, open(json_path, "w") as json_fh:
                    raw_xml: str = xml_fh.read()
                    as_json: Dict = translate(raw_xml)
                    json.dump(as_json, json_fh)
            except FileNotFoundError as e:
                logging.warning(e)
