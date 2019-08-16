import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Iterator, Tuple, Dict, List
import json

from composer.aws.efile.filings import RetrieveEfiles
from composer.aws.s3 import Bucket
from composer.efile.structures.metadata import FilingMetadata
from composer.fileio.paths import EINPathManager
from composer.futures import run_on_process_pool

TEMPLATE = "%s.json"


@dataclass
class ComposeEfiles(Callable):
    retrieve: RetrieveEfiles
    path_mgr: EINPathManager

    @classmethod
    def build(cls, basepath: str, bucket: Bucket, temp_path: str, no_cleanup: bool) -> "ComposeEfiles":
        retrieve: RetrieveEfiles = RetrieveEfiles(bucket, temp_path, no_cleanup)
        path_mgr: EINPathManager = EINPathManager(basepath)
        return cls(retrieve, path_mgr)

    def process_all(self, json_changes: List[Tuple[str, Dict[str, str]]]):
        updater = ComposeEfilesUpdater(self.path_mgr)
        run_on_process_pool(updater.create_or_update, json_changes)

    def __call__(self, changes: Iterator[Tuple[str, Dict[str, FilingMetadata]]]):
        """Iterate over EINs flagged as having one or more new e-files since the last update. For each one, create or
        update its composite with the new data.

        :param changes: Iterator of (EIN, dictionary of (filing period -> Filing)).
        """
        change_list: List = list(changes)
        json_changes: List[Tuple[str, Dict[str, str]]] = list(self.retrieve(change_list))
        logging.info("Updating e-file composites.")

        self.process_all(json_changes)


@dataclass
class ComposeEfilesUpdater:
    path_mgr: EINPathManager

    def _get_existing(self, ein: str) -> Dict:
        try:
            with self.path_mgr.open_for_reading(ein, TEMPLATE) as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {}

    def create_or_update(self, changes: List[Tuple[str, Dict[str, str]]]):
        for change in changes:
            ein, updates = change
            composite: Dict = self._get_existing(ein)
            for period, json_path in updates.items():
                with open(json_path) as fh:
                    content: Dict = json.load(fh)
                composite[period] = content
            with self.path_mgr.open_for_writing(ein, TEMPLATE) as fh:
                json.dump(composite, fh, indent=2)
