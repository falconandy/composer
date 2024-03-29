import click
from composer.efile.update import UpdateEfileState
import logging

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

@click.group()
def cli():
    """Polytropos ETL5 Composer. Copyright (c) 2019 Applied Nonprofit Research. All rights reserved."""
    pass

@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--temp_path', type=click.Path(exists=True), default="/tmp")
@click.option('--no_cleanup', is_flag=True)
def efile(data_path: str, temp_path: str, no_cleanup: bool):
    """Update local efile composites, or create them if they do not exist. Results in a set of e-file composites for all
    organizations that have e-filed, along with a SQLite database of latest and duplicate filings."""
    update: UpdateEfileState = UpdateEfileState.build(data_path, temp_path, no_cleanup)
    update()
