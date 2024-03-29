import math
import os
from concurrent.futures import as_completed, Executor, ThreadPoolExecutor
from concurrent.futures.process import ProcessPoolExecutor
from typing import Optional, Callable, List, Any, Iterable


def run_on_process_pool(func: Callable, items: List[Any], *args: Any, chunk_size: Optional[int] = None, workers_count: Optional[int] = None):
    if len(items) == 0:
        return

    if workers_count is None:
        workers_count = os.cpu_count() or 1

    if chunk_size is None:
        chunk_size = math.ceil(len(items) / workers_count)

    executor = ProcessPoolExecutor(max_workers=workers_count)
    run_on_pool(executor, func, items, *args, chunk_size=chunk_size)


def run_on_thread_pool(func: Callable, items: List[Any], *args: Any, chunk_size: Optional[int] = None, workers_count: Optional[int] = None):
    if len(items) == 0:
        return

    executor = ThreadPoolExecutor(max_workers=workers_count)
    run_on_pool(executor, func, items, *args, chunk_size=chunk_size)


def run_on_pool(executor: Executor, func: Callable, items: List[Any], *args: Any, chunk_size: Optional[int] = None):
    if len(items) == 0:
        return

    if chunk_size is None:
        chunk_size = 1

    chunks: Iterable[List[Any]] = _split_to_chunks(list(items), chunk_size)

    exceptions = []
    with executor:
        futures = [executor.submit(func, chunk, *args) for chunk in chunks]
        for future in as_completed(futures):
            if future.exception() is not None:
                exceptions.append(future.exception())
    if len(exceptions) > 0:
        raise exceptions[0]


# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def _split_to_chunks(items: List[Any], chunk_size: int) -> Iterable[List[Any]]:
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]
