import json
import logging
import os
import re
from multiprocessing import Pool

from lxml import etree
from tqdm import tqdm

from config import tm_index_path

greek_input = "ΌΏΎΊΉᾲᾀᾁᾂᾃᾅᾇέάΐήώίόύϝϛϋϊᾄᾆᾳᾴᾷαβγδεζηθικλμνξοπρστυφχψωἀἄἂἆἁἅἃἇάὰᾶἐἔἒἑἕἓὲέἠἤἢἦἡἥἣἧὴήᾐᾑᾒᾓᾔᾕᾖᾗῂῃῄῆῇἰἴἲἶἱἵἳἷὶίῐῑῒΐῖῗὀὄὂὁὅὃὸόὐὑὒὓὔὕὖὗὺῦύῠῡῢΰῧὠὤὢὦὡὥὣὧώὼᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷῤῥἈἌἊἎἉἍἋἏᾺΆᾼᾈᾉᾊᾋᾌᾍᾎᾏἘἜἚἙἝἛῈΈἨἬἪἮἩἭἫἯῊΉῌᾘᾙᾚᾛᾜᾝᾞᾟἸἼἺἾἹἽἻἿΊῚῘῙὈὌὊὉὍὋΌῸὙὝὛὟΎῪῨῩὨὬὪὮὩὭὫὯΏῺῼᾨᾩᾪᾫᾬᾭᾮᾯῬςϲϹ"
greek_output = "ΟΩΥΙΗΑΑΑΑΑΑΑΕΑΙΗΩΙΟΥϜϚΥΙΑΑΑΑΑΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩΑΑΑΑΑΑΑΑΑΑΑΕΕΕΕΕΕΕΕΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΙΙΙΙΙΙΙΙΙΙΙΙΙΙΙΙΟΟΟΟΟΟΟΟΥΥΥΥΥΥΥΥΥΥΥΥΥΥΥΥΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΡΡΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΑΕΕΕΕΕΕΕΕΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΗΙΙΙΙΙΙΙΙΙΙΙΙΟΟΟΟΟΟΟΟΥΥΥΥΥΥΥΥΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΩΡΣΣΣ"
ns = {'tei': 'http://www.tei-c.org/ns/1.0'}


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


def get_paths_to_tm(tm: int) -> list[str]:
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


def handle_multiple_tms(unique_list: list, xml_file_path: str) -> list:
    data = []
    unique = [s for s in unique_list if s]
    if len(unique) > 1:
        for u in unique:
            data.append({'tm': int(u), 'path': str(xml_file_path)})
    elif len(unique) == 1:
        data.append({'tm': int(unique[0]), 'path': str(xml_file_path)})
    return data


def get_tm_from_path(xml_file_path: str) -> list[dict]:
    """
    Searches an XML file for tm numbers and returns an index of the TM number with its correlating path for quick
    access.
    :param xml_file_path: Path to xml file
    :return: List of Dictionaries with keys tm: int and path: str
    """
    data = []
    file_tree = etree.parse(xml_file_path)
    tm = file_tree.xpath('//tei:idno[@type="TM"]/text()', namespaces=ns)
    if len(tm) > 1:
        for num in tm:
            unique = list(set(num.split()))
            data = handle_multiple_tms(unique, xml_file_path)
    elif len(tm) == 1:
        unique = list(set(tm[0].split()))
        data = handle_multiple_tms(unique, xml_file_path)
    return data


def get_tm_from_paths(xml_file_paths: list[str], desc='Preparing') -> list[dict]:
    """
    Searches multiple XML files for tm numbers and returns an index of TM numbers with their correlating paths for quick
    access.
    :param xml_file_paths: Paths to xml files
    :param desc: tqdm description
    :return: List of dictionaries with keys tm: int and path: str
    """
    pool = Pool(os.cpu_count() + 1)
    cache_data = []
    for result in tqdm(pool.imap_unordered(get_tm_from_path, xml_file_paths), total=len(xml_file_paths), desc=desc):
        if result:
            for element in result:
                cache_data.append(element)
    return cache_data
