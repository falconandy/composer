import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from sqlite3 import Connection, connect

from composer.aws.efile.bucket import efile_bucket
from composer.aws.efile.indices import EfileIndices
from composer.aws.s3 import Bucket
from composer.efile.structures.mdindex import EfileMetadataIndex
from composer.efile.compose import ComposeEfiles
from composer.efile.structures.sqlite import init_sqlite_db
from composer.timer import TimeLogger

@dataclass
class UpdateEfileState(Callable):
    basepath: str
    indices: EfileIndices
    compose: ComposeEfiles

    @classmethod
    def build(cls, basepath: str, temp_path: str, no_cleanup: bool) -> "UpdateEfileState":
        bucket: Bucket = efile_bucket()
        indices: EfileIndices = EfileIndices(bucket)
        compose: ComposeEfiles = ComposeEfiles.build(basepath, bucket, temp_path, no_cleanup)
        return cls(basepath, indices, compose)

    def _connect(self) -> Connection:
        sqlite_path: str = os.path.join(self.basepath, "state.sqlite")
        if os.path.exists(sqlite_path):
            logging.info("Connecting to SQLite e-File state database.")
            return connect(sqlite_path)
        else:
            logging.info("e-File state database does not exist; initializing.")
            return init_sqlite_db(sqlite_path)

    def _index_changes(self) -> EfileMetadataIndex:
        conn: Connection = self._connect()
        md_index: EfileMetadataIndex = EfileMetadataIndex.build(conn)
        t_log: TimeLogger = TimeLogger("Considered {:,} e-File index entries")
        for filing_md in self.indices:
            fn: Callable = lambda: md_index.add(filing_md)
            t_log.measure(fn)
        t_log.finish()
        n_eins_changed: int = len(md_index.staged_changes.keys())
        n_amended: int = len(md_index.staged_dupes.keys())
        logging.info("{:,} EINs have new e-Files; {:,} filings were amended.".format(n_eins_changed, n_amended))
        return md_index

    def __call__(self):
        md_index: EfileMetadataIndex = self._index_changes()
        self.compose(md_index.changes)
        md_index.commit()
