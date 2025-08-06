import glob
import os
from dataclasses import dataclass
from multiprocessing import Pool
from typing import Literal, Callable

from lxml import etree
from tqdm import tqdm
from colorama import Fore, Style

ns = {'tei': 'http://www.tei-c.org/ns/1.0'}


@dataclass
class PapyrusFilter:
    """
    Filters files from DCLP, DDB_EpiDoc_XML or from both sources.

    Attributes:
        idp_data_path (str): Path to the directory containing DCLP XML files.
        target (str): File source
        title (str): tei:title
        place (str): tei:origPlace
        dclp_hybrid (str): tei:dclp-hybrid
        single_match_suffices (bool): A single match in one of the filter categories is enough to add it to the processing batch
    """
    idp_data_path: str
    target: Literal['dclp', 'ddb', 'all']
    title: str = None
    place: str = None
    dclp_hybrid: str = None
    single_match_suffices: bool = True
    name: str = None

    def __post_init__(self):
        self.__check_input()
        if not self.name:
            self.name = f'filter-{self.target}-{self.title}-{self.place}-{self.dclp_hybrid}-{self.single_match_suffices}'

    def __check_input(self):
        if self.target == 'ddb':
            self.dclp_hybrid = ''
        if not (self.title or self.place or self.dclp_hybrid):
            print(Fore.RED + '[PapyrusFilter] ERROR: title, place, or dclp_hybrid must be set.' + Style.RESET_ALL)
            exit(1)

    def filter_file(self, file: str, get_tm_from_path: Callable[[str], list[dict]]) -> list[int]:
        tms: list[int] = []
        root = etree.parse(file)
        title_matches = False
        dclp_hybrid_matches = False
        place_matches = False
        if self.title:
            tei_title = root.xpath('//tei:titleStmt/tei:title/text()', namespaces=ns)
            if tei_title:
                if self.title.lower() in tei_title[0].lower():
                    title_matches = True
        if self.target == 'dclp':
            if self.dclp_hybrid:
                tei_dclp_hybrid = root.xpath('//tei:publicationStmt/tei:idno[@type="dclp-hybrid"]/text()',
                                             namespaces=ns)
                if tei_dclp_hybrid:
                    if self.dclp_hybrid.lower() in tei_dclp_hybrid[0].lower():
                        dclp_hybrid_matches = True
        if self.place:
            tei_place = root.xpath('//tei:origin/tei:origPlace/text()', namespaces=ns)
            if tei_place:
                if self.place.lower() in tei_place[0].lower():
                    place_matches = True
        if self.single_match_suffices:
            if title_matches or dclp_hybrid_matches or place_matches:
                xpath_tms = get_tm_from_path(file)
                for tm in xpath_tms:
                    tms.append(tm['tm'])
        else:
            if title_matches and dclp_hybrid_matches and place_matches:
                xpath_tms = get_tm_from_path(file)
                for tm in xpath_tms:
                    tms.append(tm['tm'])
        return tms

    def wrapper(self, args):
        return self.filter_file(*args)

    def filter(self):
        from papyrser_utils.utils import get_tm_from_path
        if self.target == 'dclp':
            files = glob.glob(os.path.join(self.idp_data_path, 'DCLP/**/*.xml'), recursive=True)
        elif self.target == 'ddb':
            files = glob.glob(os.path.join(self.idp_data_path, 'DDB_EpiDoc_XML/**/*.xml'), recursive=True)
        else:
            files = glob.glob(os.path.join(self.idp_data_path, '**/*.xml'), recursive=True)
        tms: list[int] = []
        pool = Pool(os.cpu_count() + 1)
        inputs = [(file, get_tm_from_path) for file in files]
        for result in tqdm(pool.imap_unordered(self.wrapper, inputs), total=len(files), desc='Filtering'):
            if result:
                for element in result:
                    tms.append(element)
        return tms
