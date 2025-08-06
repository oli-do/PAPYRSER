import glob
import logging
import os
from multiprocessing import Pool
from typing import cast

from tqdm import tqdm

from config import (idp_data_path, tm_index_path, papyri_data_path, debug_mode, papyrus_target, always_update_github,
                    always_do_indexing, main_path)
from papyrser_core.parser import TEIParser
from papyrser_io.downloader import PapyriDownloader
from papyrser_io.handler import IOHandler
from papyrser_io.pap_filter import PapyrusFilter
from papyrser_utils.utils import get_tm_from_paths, setup_logging, before_running

logger = logging.getLogger(f"{__name__}")

def run(target: int | list[int] | str | list[str] | PapyrusFilter):
    """
    Initialization method for GitHub sync and conversion processes. Automatically switches to multiprocessing if the CPU
    count is greater or equal the number of texts which are to be processed and if debug_mode is set to False.
    :param target: TM number, list of TM numbers, a string with a DDB collection name or a list of DDB collection names
    """
    io_handler = IOHandler()
    io_handler.create_folder(os.path.join(main_path, 'export'))
    io_handler.create_folder(papyri_data_path)
    downloader = PapyriDownloader()
    parser = TEIParser(io_handler)
    if (idp_data_path == os.path.join(main_path, 'papyri_data', 'idp.data-master') and not os.path.exists(idp_data_path)
            or always_update_github):
        downloader.download_github_data()
    if not os.path.exists(tm_index_path) or always_do_indexing:
        downloader.index_tm_numbers()
    if isinstance(target, PapyrusFilter):
        io_handler.set_export_directory(target.name)
        target = target.filter()
    if isinstance(target, int):
        io_handler.set_export_directory(str(target))
        target = [target]
    elif isinstance(target, list):
        types = list(set(type(x) for x in target))
        if len(types) == 1 and types[0] == int:
            target.sort()
            if not io_handler.export_directory:
                io_handler.set_export_directory(f'{target[0]}-{target[-1]}')
        elif len(types) == 1 and types[0] == str:
            collections = os.listdir(os.path.join(idp_data_path, 'DDB_EpiDoc_XML'))
            files = []
            for collection in target:
                collection = cast(str, collection)
                if collection.lower() in collections:
                    files += glob.glob(os.path.join(idp_data_path, f'DDB_EpiDoc_XML/{collection.lower()}/**/*.xml'))
                else:
                    logger.critical(f'Collection {collection}] not found. Please enter a valid collection name in '
                                    f'config.papyrus_target.')
            data = get_tm_from_paths(files)
            target = [d.get('tm') for d in data]
        else:
            msg = f'Invalid papyrus_target set in config: A list must either contain only str or int values.'
            logger.critical(msg)
            print(msg)
            exit(1)
    elif isinstance(target, str):
        io_handler.set_export_directory(target)
        collections = os.listdir(os.path.join(idp_data_path, 'DDB_EpiDoc_XML'))
        if target.lower() in collections:
            files = glob.glob(os.path.join(idp_data_path, f'DDB_EpiDoc_XML/{target.lower()}/**/*.xml'))
            data = get_tm_from_paths(files)
            target = [d.get('tm') for d in data]
        else:
            msg = 'Collection not found. Please enter a valid collection name in config.papyrus_target.'
            print(msg)
            logger.critical(msg)
            exit(1)
    else:
        msg = f'Invalid papyrus_target set in config: {type(target)} is not allowed.'
        logger.critical(msg)
        print(msg)
        exit(1)
    if len(target) > 1:
        target = list(set(target))
    if len(target) > os.cpu_count() and not debug_mode:
        pool = Pool(os.cpu_count() + 1)
        bar = tqdm(total=len(target), desc='Parsing')
        for skipped in pool.imap_unordered(parser.process_tei, target):
            if skipped:
                logger.warning(skipped)
            bar.update()
    else:
        for t in tqdm(target, total=len(target), desc='Parsing'):
            skipped = parser.process_tei(t)
            if skipped and not debug_mode:
                logger.warning(skipped)

def initialize(target=None):
    if target is None:
        target = papyrus_target
    setup_logging()
    before_running()
    run(target)


if __name__ == '__main__':
    initialize()
