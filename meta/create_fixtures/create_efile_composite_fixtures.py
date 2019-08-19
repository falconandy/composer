import os
from collections import OrderedDict
from sqlite3 import Connection, connect
from typing import Iterator, Tuple, Dict

from composer.aws.efile.filings import RetrieveEfiles
from mock import MagicMock

from composer.aws.s3 import file_backed_bucket
from composer.efile.compose import ComposeEfiles
from composer.efile.structures.mdindex import EfileMetadataIndex
from composer.efile.structures.metadata import FilingMetadata
from composer.fileio.paths import EINPathManager

BASEPATH = "/dmz/github/analysis/composer"

def get_composite_items(idx: EfileMetadataIndex) -> Iterator[Tuple[str, Dict[str, FilingMetadata]]]:
    for ein in idx.latest_filings.eins:
        observations: Dict = {o.period : o for o in idx.latest_filings.filings_for_ein(ein)}
        o_sorted: OrderedDict = OrderedDict()
        for period, filing in sorted(zip(observations.keys(), observations.values())):
            o_sorted[period] = filing
        yield ein, o_sorted

def get_bucket():
    efile_xml_path: str = os.path.join(BASEPATH, "fixtures", "efile_xml")
    return file_backed_bucket(efile_xml_path)

for timepoint in ["first", "second"]:
    cpath: str = "%s/fixtures/efile_sqlite/%s_timepoint.sqlite" % (BASEPATH, timepoint)
    conn: Connection = connect(cpath)
    index: EfileMetadataIndex = EfileMetadataIndex.build(conn)

    RetrieveEfiles.get_bucket = get_bucket
    retrieve: RetrieveEfiles = RetrieveEfiles()
    path_mgr: EINPathManager = EINPathManager("%s/fixtures/efile_composites/%s_timepoint" % (BASEPATH, timepoint))

    compose: ComposeEfiles = ComposeEfiles(retrieve, path_mgr)
    to_record: Iterator = get_composite_items(index)
    compose(to_record)