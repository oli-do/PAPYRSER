import glob
import json
import logging
import os
import zipfile

import requests
from tqdm import tqdm

from config import papyri_data_path, debug_mode, tm_index_path, idp_data_path
from papyrser_io.handler import IOHandler
from papyrser_utils.utils import get_tm_from_paths


class PapyriDownloader:
    def __init__(self):
        """
        Initialize an object of the PapyriDownloader class, which can download GitHub data and index TM numbers.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.io_handler = IOHandler()
        self.github_url = 'https://github.com/papyri/idp.data/archive/refs/heads/master.zip'

    def download_github_data(self):
        """
        Downloads and extracts papyri.info data from GitHub.
        """
        session = requests.Session()
        self.io_handler.create_folder(papyri_data_path)
        if debug_mode:
            self.logger.info('Downloading compressed papyri.info data')
        request = session.get(self.github_url, stream=True)
        temp_zip_path = os.path.join(papyri_data_path, 'temp.zip')
        with (open(temp_zip_path, 'wb') as f,
              tqdm(unit='B', unit_scale=True, unit_divisor=1024, desc='Downloading') as bar):
            for chunk in request.iter_content(chunk_size=1024):
                f.write(chunk)
                bar.update(len(chunk))
        if request.status_code == 200:
            session.close()
            if debug_mode:
                self.logger.info('Extracting files')
            with zipfile.ZipFile(temp_zip_path, 'r') as z:
                names = z.namelist()
                for i in tqdm(range(len(z.namelist())), total=len(z.namelist()), desc='Extracting'):
                    if "DCLP" in names[i] or "DDB_EpiDoc_XML" in names[i]:
                        z.extract(names[i], papyri_data_path)
            os.remove(temp_zip_path)
            if os.path.exists(tm_index_path):
                os.remove(tm_index_path)
        else:
            session.close()
            os.remove(temp_zip_path)
            msg = f'Download failed. Status code: {request.status_code}'
            print(msg)
            if debug_mode:
                self.logger.critical(msg)
            exit(1)

    def index_tm_numbers(self):
        """
        Searches /DCLP and /DDB_EpiDoc_XML for tm numbers and creates an index of TM numbers with their correlating
        paths for quick file access.
        """
        if debug_mode:
            self.logger.info('Caching TM numbers')
        sep = os.path.sep
        dclp_path = os.path.normpath(os.path.join(idp_data_path, 'DCLP'))
        ddb_path = os.path.normpath(os.path.join(idp_data_path, 'DDB_EpiDoc_XML'))
        xml_files = []
        if os.path.exists(dclp_path):
            xml_files = glob.glob(dclp_path + f'{sep}**{sep}*.xml', recursive=True)
        else:
            self.logger.error(f'Could not find {dclp_path}')
        if os.path.exists(ddb_path):
            xml_files += glob.glob(ddb_path + f'{sep}**{sep}*.xml', recursive=True)
        else:
            self.logger.error(f'Could not find {ddb_path}')
        if not xml_files:
            msg = (f'Indexing failed: No XML files found; config.idp_data_path must lead to a directory containing '
                   f'a valid copy of DCLP and DDB_EpiDoc_XML from <https://github.com/papyri/idp.data>.')
            self.logger.critical(msg)
            print(msg)
            exit(1)
        data = get_tm_from_paths(xml_files, desc='Indexing')
        self.io_handler.write_text_to_file(tm_index_path, json.dumps(data))
