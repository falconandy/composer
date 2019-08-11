from collections.abc import Callable
import itertools
import json
from sqlite3 import connect, Cursor
from typing import Dict, Set, Iterator, Tuple

import pytest
import os
import shutil

from composer.aws.efile.filings import EfileFilings
from composer.aws.efile.indices import EfileIndices
from composer.aws.s3 import Bucket, file_backed_bucket, List
from composer.efile.compose import ComposeEfiles
from composer.efile.update import UpdateEfileState
from composer.fileio.paths import EINPathManager

tables: List = ["duplicates", "latest_filings"]
timepoints: List = ["first_timepoint", "second_timepoint"]

"""Set up test environment"""
BASEPATH: str = os.path.dirname(os.path.abspath(__file__))
fixture_path: str = os.path.join(BASEPATH, "..", "..", "fixtures")
working_path: str = "/tmp/test_composer/efile"
tp1_path = os.path.join(working_path, "first_timepoint")
tp2_path = os.path.join(working_path, "second_timepoint")
shutil.rmtree(working_path, ignore_errors=True)

def make_indices(timepoint: str) -> EfileIndices:
    efile_index_path: str = os.path.join(fixture_path, "efile_indices", "%s_timepoint" % timepoint)
    index_bucket: Bucket = file_backed_bucket(efile_index_path)
    indices: EfileIndices = EfileIndices(index_bucket)
    return indices

def make_compose(tp_path: str) -> ComposeEfiles:
    efile_xml_path: str = os.path.join(fixture_path, "efile_xml")
    xml_bucket: Bucket = file_backed_bucket(efile_xml_path)
    s3_filings: EfileFilings = EfileFilings(xml_bucket)
    path_mgr: EINPathManager = EINPathManager(tp_path)
    compose: ComposeEfiles = ComposeEfiles(s3_filings, path_mgr)
    return compose

def do_update(timepoint: str, tp_path: str):
    indices: EfileIndices = make_indices(timepoint)
    compose: ComposeEfiles = make_compose(tp_path)
    update: UpdateEfileState = UpdateEfileState(tp_path, indices, compose)
    update()

"""Run the initial update -- no data exists"""
os.makedirs(tp1_path)
do_update("first", tp1_path)

"""Run the second update"""
shutil.copytree(tp1_path, tp2_path)
do_update("second", tp2_path)

@pytest.fixture()
def do_composite_test() -> Callable:
    def _ret(timepoint: str, tp_path: str, ein: str):
        first, second = ein[0:3], ein[3:6]
        rel_path: str = os.path.join(first, second, '%s.json' % ein)
        actual_fp: str = os.path.join(tp_path, rel_path)
        expected_fp: str = os.path.join(fixture_path, "efile_composites", "%s_timepoint" % timepoint, rel_path)

        with open(actual_fp) as a_fh, open(expected_fp) as e_fh:
            actual: Dict = json.load(a_fh)
            expected: Dict = json.load(e_fh)
            assert actual == expected
    return _ret

@pytest.mark.parametrize("ein", ["208419458", "260687839", "364201074", "943041314"])
def test_first_timepoint_composites(ein, do_composite_test):
    do_composite_test("first", tp1_path, ein)


@pytest.mark.parametrize("table, timepoint", itertools.product(tables, timepoints))
def test_sqlite_tables(table: str, timepoint: str):
    actual_path: str = os.path.join(working_path, timepoint, "state.sqlite")
    expected_path: str = os.path.join(fixture_path, "efile_sqlite", "%s.sqlite" % timepoint)
    query: str = """SELECT
        record_id,
        irs_efile_id,
        irs_dln,
        ein,
        period,
        name_org,
        form_type,
        date_submitted,
        date_uploaded,
        url 
    FROM %s""" % table  # Exclude date downloaded; these won't match
    with connect(actual_path) as a_conn, connect(expected_path) as e_conn:
        a_cursor: Cursor = a_conn.cursor()
        e_cursor: Cursor = e_conn.cursor()
        actual: Set = {row for row in a_cursor.execute(query)}
        expected: Set = {row for row in e_cursor.execute(query)}
        assert actual == expected

@pytest.mark.parametrize("ein", ["208419458", "260687839", "364201074", "581347976", "943041314"])
def test_second_timepoint_composites(ein, do_composite_test):
    do_composite_test("second", tp2_path, ein)
