import glob
import json
import logging
import os
import re
import zipfile
from multiprocessing import Pool, Manager

import requests
from lxml import etree
from tqdm import tqdm

from config import papyri_data_path, idp_data_path, tm_index_path, main_path, debug_mode


greek_input = "ΌΏΎΊΉᾲᾀᾁᾂᾃᾅᾇέάΐήώίόύϝϛϋϊᾄᾆᾳᾴᾷαβγδεζηθικλμνξοπρστυφχψωἀἄἂἆἁἅἃἇάὰᾶἐἔἒἑἕἓὲέἠἤἢἦἡἥἣἧὴήᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἰἴἲἶἱἵἳἷὶίῐῑῒΐῖῗὀὄὂὁὅὃὸόὐὑὒὓὔὕὖὗὺῦύῠῡῢΰῧὠὤὢὦὡὥὣὧώὼᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷῤῥἈἌἊἎἉἍἋἏᾺΆᾼᾈᾉᾊᾋᾌᾍᾎᾏἘἜἚἙἝἛῈΈἨἬἪἮἩἭἫἯῊΉῌᾘᾙᾚᾛᾜᾝᾞᾟἸἼἺἾἹἽἻἿΊῚῘῙὈὌὊὉὍὋΌῸὙὝὛὟΎῪῨῩὨὬὪὮὩὭὫὯΏῺῼᾨᾩᾪᾫᾬᾭᾮᾯῬςϲϹ"
greek_output = "ΟΩΥΙΗΑΑΑΑΑΑΑΕΑΙΗΩΙΟΥϜϚΥΙΑΑΑΑΑΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΑΑΑΑΑΑΑΑΑΑΑΕΕΕΕΕΕΕΕΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΙΙΙΙΙΙΙΙΙΙΙΙΙΙΙΙΟΟΟΟΟΟΟΟΥΥΥΥΥΥΥΥΥΥΥΥΥΥΥΥΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΡΡΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΕΕΕΕΕΕΕΕΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΙΙΙΙΙΙΙΙΙΙΙΙΟΟΟΟΟΟΟΟΥΥΥΥΥΥΥΥΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΡΣΣΣ"


def before_running():
    """Execute before running the script routine."""
    not_yet_impl_path = 'dev/not_yet_implemented.txt'
    if os.path.exists(not_yet_impl_path):
        os.remove(not_yet_impl_path)


def setup_logging(log_file='log.txt'):
    """Load default settings for a logger shared between modules.
    :param log_file: Name of the log file
    """
    logging.basicConfig(
        filename=log_file,
        filemode='w',
        encoding='utf-8',
        level=logging.NOTSET,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def convert_to_standardized_majuscule(input_str):
    """
    Converts Greek text to standardized majuscule characters.
    :param input_str: Greek text
    :return: Converted string
    """
    translation_table = str.maketrans(greek_input, greek_output)
    input_str = input_str.translate(translation_table)
    return re.sub(r"[ʼ†∙·•{}()',;:.\-⏑̆͂᾽᾿῎῞῾`΄“”’̓ʽ‘⌊⌋\n ]", '', input_str)


def get_paths_to_tm(tm: int) -> list:
    """
    Gets the path to every idp.data-master XML file matching the TM Number specified by tm.
    :param tm: TM number
    :return: The paths to XML files matching the TM number
    """
    paths = []
    with open(tm_index_path, 'r') as f:
        data = json.loads(f.read())
    for d in range(len(data)):
        if data[d]['tm'] == tm:
            paths.append(data[d]['path'])
    return list(set(paths))


def get_tm_from_path(xml_file_path: str) -> list[dict]:
    """
    Searches an XML file for tm numbers and returns an index of the TM number with its correlating path for quick
    access.
    :param xml_file_path: Path to xml file
    :return: List of Dictionaries with keys tm: int and path: str
    """
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    data = []
    file_tree = etree.parse(xml_file_path)
    tm = file_tree.xpath('//tei:idno[@type="TM"]/text()', namespaces=ns)
    if len(tm) > 1:
        for num in tm:
            unique = list(set(num.split()))
            unique = [s for s in unique if s]
            if len(unique) > 1:
                for u in unique:
                    data.append({'tm': int(u), 'path': str(xml_file_path)})
            elif len(unique) == 1:
                data.append({'tm': int(unique[0]), 'path': str(xml_file_path)})
    elif len(tm) == 1:
        unique = list(set(tm[0].split()))
        unique = [s for s in unique if s]
        if len(unique) > 1:
            for u in unique:
                data.append({'tm': int(u), 'path': str(xml_file_path)})
        elif len(unique) == 1:
            data.append({'tm': int(unique[0]), 'path': str(xml_file_path)})
        return data


def get_tm_from_paths(xml_file_paths: list[str], desc='Preparing') -> list[dict]:
    """
    Searches multiple XML files for tm numbers and returns an index of TM numbers with their correlating paths for quick
    access.
    :param xml_file_paths: Paths to xml files
    :param desc: tqdm description
    :return: List of dictionaries with keys tm: int and path: str
    """
    pool = Pool(os.cpu_count())
    cache_data = []
    for result in tqdm(pool.imap_unordered(get_tm_from_path, xml_file_paths), total=len(xml_file_paths), desc=desc):
        if result:
            for element in result:
                cache_data.append(element)
    return cache_data


class IOHandler:

    def __init__(self):
        """
        Initialize an object of the IOHandler class handling IO based functions like creating a folder, writing files
        and setting the export directory.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.export_directory = ''

    def set_export_directory(self, export_directory: str):
        """
        Sets IOHandler.export_directory.
        :param export_directory: Name of the export directory
        """
        self.export_directory = export_directory
        if debug_mode:
            self.logger.info(f'Set export directory to {export_directory}')

    def create_folder(self, path: str):
        """
        Creates a directory matching the specified path if it does not exist yet.
        :param path: Path to the new directory
        """
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except IOError as e:
                print(f'[!] Unable to create folder: {e}')
                if debug_mode:
                    self.logger.error(f'Unable to create folder: {e}')
                exit(1)

    def write_text_to_file(self, filename: str, text: str, encoding: str = 'utf-8', mode='w'):
        """
        Writes the provided text to a file.
        :param filename: Name of the file to write to
        :param text: Text to write to the file
        :param encoding: Encoding, default utf-8
        :param mode: Writing mode, cf. open
        """
        try:
            with open(filename, mode, encoding=encoding) as file:
                file.write(text)
        except IOError as e:
            msg = f'An error occurred while writing to the file: {e}'
            if debug_mode:
                self.logger.critical(msg)
            print(msg)
            exit(1)

    def write_to_json(self, tm: int, content: list[list[str]]) -> str:
        """
        Writes parsed data to a json file with metadata in head, text parts in body. See documentation for detailed info
        on the json structure.
        :param tm: TM number
        :param content: parser results returned by convert_to_d4
        :return: Path to the written file
        """
        target_path = os.path.join(main_path, 'export')
        target_path = os.path.join(target_path, self.export_directory)
        self.create_folder(target_path)
        target_path = os.path.join(target_path, 'json')
        self.create_folder(target_path)
        path = os.path.join(target_path, f'{str(tm)}.json')
        total_len = len(sum(content, []))
        head = {'tm': tm, 'textparts': len(content), 'lines': total_len, 'version': 'D4'}
        body = []
        for text_part in content:
            body.append({'textpart': [{'textpartLines': len(text_part), 'text': text_part}]})
        content = {'head': head, 'body': body}
        self.write_text_to_file(path, json.dumps(content, ensure_ascii=False))
        return path

    def write_to_txt(self, tm: int, content: list[list[str]]) -> str:
        """
        Writes parsed data to a txt file.
        :param tm: TM number
        :param content: parser results returned by convert_to_d4
        :return: Path to the written file
        """
        target_path = os.path.join(main_path, 'export')
        target_path = os.path.join(target_path, self.export_directory)
        self.create_folder(target_path)
        target_path = os.path.join(target_path, 'txt')
        self.create_folder(target_path)
        path = os.path.join(target_path, f'{str(tm)}.txt')
        if os.path.exists(path):
            os.remove(path)
        for i in range(len(content)):
            text_part = content[i]
            for line_index in range(len(text_part)):
                text = text_part[line_index]
                # print without \n if last line of text part and last text part of content is reached
                if line_index == len(text_part) - 1 and i == len(content) - 1:
                    self.write_text_to_file(path, text, mode='a')
                else:
                    self.write_text_to_file(path, text + '\n', mode='a')
        return path


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
