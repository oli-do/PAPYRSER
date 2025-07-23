import logging
import os
import re

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString, PageElement

from config import debug_mode, ignore_formatting_issues, write_to_json, write_to_txt
from format import Formatter
from util import get_paths_to_tm, convert_to_standardized_majuscule, IOHandler


class TEIParser:

    def __init__(self, io_handler: IOHandler):
        """
        Initialize an object of the TEIParser class.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.io_handler = io_handler
        self.write_to_json = write_to_json
        self.write_to_txt = write_to_txt
        self.formatter = Formatter()

    def process_tei(self, tm) -> str:
        """
        Starts the conversion process.
        :return: Error message in case of formatting errors
        """
        files = get_paths_to_tm(tm)
        if not files:
            msg = f'Could not find any XML file(s) associated with TM number {tm}.'
            if debug_mode:
                self.logger.error(msg)
            return msg
        for i in range(len(files)):
            file = files[i]
            filename = file.split(os.sep)[-1].replace('.xml', '')
            if debug_mode:
                self.logger.info(f'\n\n### Processing {file} (TM {tm}) ###')
            try:
                output_data = self.convert_to_d5(str(file))
            except ValueError as e:
                if debug_mode:
                    self.logger.error(str(e))
                return str(e)
            if not output_data:
                if debug_mode:
                    self.logger.info('convert_to_d5 returned no data.')
                continue
            if not self.formatter.error_log or ignore_formatting_issues:
                if debug_mode:
                    self.logger.info(f'Output ready to write: {output_data}')
                if self.write_to_json:
                    path = self.io_handler.write_to_json(tm, filename, output_data)
                    if debug_mode:
                        self.logger.info(f'self.io_handler wrote {path}')
                if self.write_to_txt:
                    path = self.io_handler.write_to_txt(tm, filename, output_data)
                    if debug_mode:
                        self.logger.info(f'self.io_handler wrote {path}')
            else:
                msg = f'TM {tm} skipped due to formatting errors'
                if debug_mode:
                    self.logger.warning(msg)
                msg_include_formatter = f'{msg}: {self.formatter.error_log}'
                self.formatter.error_log = []
                return msg_include_formatter

    def convert_to_d5(self, file_path: str, test: bool = False) -> (list[list[str]], list[str]):
        """
        Converts XML TEI to the D4 standard.
        :param file_path: Path to the XML file whose content is to be converted.
        :param test: for unittest
        :return: A list of lists. Each list of string represents a text part, i.e. every line as string contained in TEI
        <ab> tags; list of errors.
        """
        if not test:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file = f.read()
            except FileNotFoundError as e:
                return [], [str(e)]
        else:
            file = file_path
        soup = BeautifulSoup(file, 'lxml-xml')
        self.formatter.get_languages(soup)
        text_parts = soup.find_all('ab')
        output = []
        for ab in text_parts:
            ab_soup = BeautifulSoup(str(ab), 'lxml-xml')
            try:
                line = ab_soup.find_all('lb')[0]
            except IndexError:
                continue
            # Uses the sibling by sibling approach to parse the contents of <ab>
            sibling = line.next_sibling
            text: str = ''
            while sibling:
                if sibling is None:
                    break
                elif str(sibling).strip() == '':
                    sibling = sibling.next_sibling
                    continue
                if debug_mode:
                    self.logger.debug(f'XML sibling: {str(sibling).strip()}')
                if isinstance(sibling, Tag):
                    parser_results = self.parse_contents(sibling)
                    text += parser_results
                    if debug_mode:
                        self.logger.debug(f'Parsed: {repr(parser_results)}')
                elif isinstance(sibling, NavigableString):
                    converted_text = convert_to_standardized_majuscule(sibling.strip())
                    text += converted_text
                    if debug_mode:
                        self.logger.debug(f'Converted NavigableString: {repr(converted_text)}')
                sibling = sibling.next_sibling
            # handle insertions caused by <add>, cf. add()
            line_text: list[str] = list(filter(None, text.split('\n')))
            line_text = self.insert_lines(line_text)
            # Making sure lines are formatted correctly; Validating format
            for i in range(len(line_text)):
                line_text[i] = self.formatter.format_line(line_text[i])
                if line_text[i] == '':
                    continue
                line_text[i] = self.formatter.validate_line(line_text[i])
            output.append(list(filter(None, line_text)))
        return list(filter(None, output))

    def parse_contents(self, sibling: Tag | PageElement, parsed='', parent_name='') -> str:
        """
        Parses contents of a tag; uses recursion if necessary.
        :param sibling: XML sibling
        :param parsed: Parsed contents as string
        :param parent_name: Parent name of the processed tag
        :return: Parsed contents as string
        """
        sibling_name: str = sibling.name
        # in case of reg return empty string
        if sibling_name == 'reg' or parent_name == 'reg':
            return ''
        # return parser results if the following conditions are true
        if sibling_name == 'rdg' or (sibling_name == 'del' and parent_name == ''):
            return parsed.replace(' ', '')
        contents = sibling.contents
        # expan, supplied, subst and add are handled by transform(), tags without children (= no contents) are equally
        # handled; else: in case of children, transform() if a NavigableString is found, else call parse_contents
        if not contents or sibling_name in ['expan', 'supplied', 'subst', 'add', 'gap', 'hi']:
            parsed += self.transform(sibling_name, sibling.attrs, sibling.text.strip(), sibling, parent_name)
            if sibling_name == 'space':
                return parsed
            else:
                return parsed.replace(' ', '')
        else:
            for child in contents:
                if isinstance(child, NavigableString):
                    parsed += self.transform(sibling_name, sibling.attrs, child.text.strip(), sibling, parent_name)
                else:
                    parsed += self.parse_contents(child, parent_name=sibling.name)
        return parsed.replace(' ', '')

    def transform(self, tag: str, attrs: dict, text: str, node: PageElement | Tag, parent_name: str) -> str:
        """
        Transforms XML elements according to the D4 standard.
        :param tag: Name of the tag
        :param attrs: List of attributes produced by PageElement.attrs
        :param text: Complete text which the tag contains
        :param node: PageElement representation of the target XML node
        :param parent_name: Name of the parent tag
        :return: Empty string or parsed text
        """
        text = convert_to_standardized_majuscule(text)
        if tag == 'lb':
            return '\n'
        elif tag == 'gap':
            return self.gap(attrs)
        elif tag == 'space':
            return self.space(attrs)
        elif tag == 'supplied':
            supplied_text = ''
            for child in node.children:
                if isinstance(child, Tag):
                    if child.name:
                        supplied_text += self.parse_contents(child)
                elif isinstance(child, NavigableString):
                    supplied_text += convert_to_standardized_majuscule(child.text.strip())
            return self.supplied(supplied_text, attrs)
        elif tag == 'unclear':
            return self.add_char_to_each_letter(text, '\u0323')
        elif tag == 'milestone':
            return self.milestone(attrs)
        elif tag == 'expan':
            parent_text = ''
            ex_text = ''
            for c in node.contents:
                if isinstance(c, NavigableString):
                    parent_text += convert_to_standardized_majuscule(c)
                elif isinstance(c, Tag):
                    if c.name == 'ex':
                        ex_text += self.ex(convert_to_standardized_majuscule(c.text.strip()))
                    else:
                        parent_text += self.parse_contents(c)
            if parent_text:
                return parent_text
            else:
                return ex_text
        elif tag == 'ex':
            return ''
        elif tag == 'add':
            text = ''
            for c in node.contents:
                if isinstance(c, NavigableString):
                    text += convert_to_standardized_majuscule(c.strip())
                elif isinstance(c, Tag):
                    text += self.parse_contents(c)
            return self.add(text, attrs)
        elif tag == 'num':
            if 'tick' in attrs:
                return f"{text}'"
            else:
                return text
        elif tag == 'lem':
            return text
        elif tag == 'orig':
            return text
        elif tag == 'sic':
            return text
        elif tag == 'subst':
            subst_text = ''
            for child in node.children:
                if isinstance(child, Tag):
                    if child.name == 'add':
                        if isinstance(child, Tag):
                            if child.attrs['place'] == 'inline':
                                subst_text = convert_to_standardized_majuscule(child.text)
                                break
                    if child.name == 'del':
                        for c in child.contents:
                            if isinstance(c, NavigableString):
                                subst_text += convert_to_standardized_majuscule(c.strip())
                            elif isinstance(c, Tag):
                                subst_text += self.parse_contents(c, parent_name='subst')
            subst_text = re.sub(r'\[-+]', '', subst_text)
            return subst_text
        elif tag == 'del':
            if parent_name == 'subst':
                return text
            else:
                return ''
        elif tag == 'g':
            return self.gtype(attrs)
        elif tag == 'surplus':
            return text
        elif tag == 'abbr':
            return text
        elif tag == 'hi':
            children = node.children
            child_hi = ''
            for child in children:
                if isinstance(child, Tag):
                    if child.name == 'hi':
                        child_hi = self.hi(child.attrs, '')
                        current_hi = self.hi(attrs, '')
                        for content in child.contents:
                            if isinstance(content, NavigableString):
                                return (convert_to_standardized_majuscule(child.text)) + current_hi + child_hi
                            elif isinstance(content, Tag):
                                return self.transform(content.name, content.attrs, content.text, content, content.parent.name) + current_hi + child_hi
                    elif child.name == 'gap':
                        text = self.gap(child.attrs)
                        return self.hi(attrs, text)
            if not child_hi:
                return self.hi(attrs, text)
        elif tag == 'q':
            return text
        else:
            return ''

    def insert_lines(self, line_text: list[str]):
        """
        Inserts lines as prepared by add().
        :param line_text: A list containing every line of text
        :return: The processed list
        """
        insertions = []
        for i in range(len(line_text)):
            left_find = re.findall(r'<(.*?)<', line_text[i])
            left_find.reverse()
            right_find = re.findall(r'>(.*?)>', line_text[i])
            for string in left_find:
                line_text[i] = line_text[i].replace('<' + string + '<', '')
                insertions.append((i, string))
            for string in right_find:
                line_text[i] = line_text[i].replace('>' + string + '>', '')
                insertions.append((i + 1, string))
        insertion_count = 0
        for tpl in insertions:
            index = tpl[0] + insertion_count
            text = tpl[1]
            try:
                line_text.insert(index, text)
            except IndexError:
                line_text.append(text)
            line_text[index] = self.formatter.format_line(line_text[index])
            insertion_count += 1
        return line_text

    @staticmethod
    def add_char_to_each_letter(input_string, char_to_add):
        """
        Adds a specified character to each char in a string.
        :param input_string: Target string
        :param char_to_add: Char which is added to every char in input_string
        :return: Processed string
        """
        result = ""
        for letter in input_string:
            result += letter + char_to_add
        return result

    @staticmethod
    def gap(attr: dict):
        """
        Handles <gap>.
        :param attr: Attributes of <gap>
        :return: String representation of <gap>
        """
        try:
            if attr['unit'] == 'line':
                return ''
            elif attr['reason'] == 'illegible':
                if 'quantity' in attr:
                    quantity = int(attr['quantity'])
                    return ''.join(["-" for _ in range(quantity)])
                else:
                    try:
                        return ''.join(["-" for _ in range(round((int(attr['atLeast']) + int(attr['atMost'])) / 2))])
                    except KeyError:
                        return '[?]'
            elif 'quantity' in attr:
                quantity = int(attr['quantity'])
                return '[' + ''.join(["-" for _ in range(quantity)]) + ']'
            elif 'extent' in attr:
                if attr['extent'] == 'unknown':
                    return '[?]'
                else:
                    return ''
            elif 'atLeast' in attr:
                return ('[' + ''.join(["-" for _ in range(round((int(attr['atLeast']) + int(attr['atMost'])) / 2))])
                        + ']')
            else:
                return '[?]'
        except KeyError:
            return '[?]'

    @staticmethod
    def space(attr: dict):
        """
        Handles <space>.
        :param attr: Attributes of <space>
        :return: String representation of <space>
        """
        try:
            if attr['unit'] == 'line':
                return ''
            elif 'quantity' in attr:
                quantity = int(attr['quantity'])
                return ''.join([" " for _ in range(quantity)])
            elif 'atLeast' in attr:
                return ''.join([" " for _ in range(round((int(attr['atLeast']) + int(attr['atMost'])) / 2))])
            elif 'extent' in attr:
                return ' ? '
            else:
                return ''
        except KeyError:
            return ' ? '

    @staticmethod
    def supplied(text: str, attrs: dict):
        """
        Handles <supplied>.
        :param text: Text of <supplied>
        :param attrs: Attributes of <supplied>
        :return: String representation of <supplied>
        """
        text = text.replace(' ', '')
        if 'reason' in attrs:
            if attrs['reason'] == 'omitted':
                return ''
            else:
                filler = ''.join(["-" for _ in range(len(text))])
                if len(filler) >= 1:
                    return f'[{filler}]'
                else:
                    return ''
        else:
            filler = ''.join(["-" for _ in range(len(text))])
            if len(filler) >= 1:
                return f'[{filler}]'
            else:
                return ''

    def milestone(self, attrs: dict):
        """
        Handles <milestone>.
        :param attrs: Attributes of <milestone>
        :return: String representation of <milestone>
        """
        if 'rend' in attrs:
            unicode_map = {
                "paragraphos": '\n\u2e0f',
                "horizontal-rule": '\n\u2015',
                "diple-obelismene": '\n\u2E10',
                "wavy-line": '\n\u223C',
                "coronis": '\n\u2E0E'
            }
            try:
                return unicode_map[attrs['rend']]
            except KeyError:
                if debug_mode:
                    self.io_handler.create_folder('dev')
                    self.io_handler.write_text_to_file('not_yet_implemented.txt', f'milestone rend="{attrs['rend']}"\n',
                                                       mode='a')
                return ''
        else:
            return ''

    @staticmethod
    def ex(text: str):
        """
        Handles <ex>.
        :param text: Text of <ex>
        :return: Unicode representation of parsed <ex>
        """
        text = text[0:5]
        unicode_map = {
            # year
            "ΕΤΟΥΣ": "\U00010179",
            "ΕΤΟΣ": "\U00010179",
            "ΕΤΩΝ": "\U00010179",
            "ΕΤΕΣΙ": "\U00010179",
            # measures
            "ΑΡΟΥΡ": "\U00010187",
            "ΑΡΤΑΒ": "\U00010186",
            "ΧΟΙΝΙ": "\uE674",
            "ΞΕΣΤΗ": "\U00010185",
            "ΞΕΣΤΟ": "\U00010185",
            "ΞΕΣΤΩ": "\U00010185",
            "ΛΙΤΡΑ": "\U00010183",
            "ΛΙΤΡΩ": "\U00010183",
            "ΟΥΓΚΙ": "\U00010184",
            "ΜΕΤΡΕ": "\uE63D",
            "ΜΕΤΡΟ": "\uE63D",
            # numbers and fractions
            "ΤΡΙΤΟ": "\u2C85",
            "ΤΕΤΑΡ": "\uE606",
            # money
            "ΔΡΑΧΜ": "\U0001017B",
            "ΟΒΟΛΟ": "\U0001017C",
            "ΔΙΩΒΟ": "\U0001017D",
            "ΤΡΙΩΒ": "\U0001017E",
            "ΤΕΤΡΩ": "\U0001017F",
            "ΠΕΝΤΩ": "\U00010180",
            "ΗΜΙΩΒ": "\uE675",
            "ΗΜΙΟΒ": "\uE675",
            "ΧΑΛΚΟ": "\u2CAC",
            "ΔΙΧΑΛ": "\u2CAD",
            "ΚΕΡΑΤ": "\uE67D",
            "ΤΑΛΑΝ": "\U0001017A",
            "ΔΗΝΑΡ": "\uE6A3",
            "ΝΟΜΙΣ": "\uE696",
            "ΜΥΡΙΑ": "\uE616",
            # wheat
            "ΠΥΡΟΥ": "\uE63E",
            "ΠΥΡΩ": "\uE63E",
            "ΠΥΡΩΙ": "\uE63E",
            "ΠΥΡΟΝ": "\uE63E",
            "ΠΥΡΟΣ": "\uE63E",
            # operators
            "ΓΙΝΟΝ": "\uE691",
            "ΓΙΝΕΤ": "\uE691",
            "ΓΙΓΝΟ": "\uE691",
            "ΓΙΓΝΕ": "\uE691",
            "ΛΟΙΠΩ": "\uE613",
            "ΛΟΙΠΟ": "\uE613",
            # fractions
            "ΗΜΙΣΥ": "\U00010175",
            # monograms
            "ΠΡΟΣ": "\U0000E688",
            "ΓΡΑΜΜ": "\U0000E689",
            "ΖΜΥΡΝ": "\U0000E68A",
            "ΩΡΑ": "\U0000E68B",
            "ΩΡΑΣ": "\U0000E68B",
            "ΜΕΡΙΣ": "\U0000E68C",
            "ΜΕΡΙΔ": "\U0000E68C",
            "ΧΕΙΡΙ": "\U0000E68E",
            "ΧΡΩ": "\U00002CE9",
            # other symbols
            "ΑΥΤΟΣ": "\U0000E632",
            "ΑΥΤΟΥ": "\U0000E632",
            "ΑΥΤΩ": "\U0000E632",
            "ΑΥΤΩΙ": "\U0000E632",
            "ΑΥΤΟΝ": "\U0000E632",
            "ΑΥΤΟΙ": "\U0000E632",
            "ΑΥΤΩΝ": "\U0000E632",
            "ΑΥΤΗ": "\U0000E632",
            "ΑΥΤΗΣ": "\U0000E632",
            "ΑΥΤΗΙ": "\U0000E632",
            "ΑΥΤΗΝ": "\U0000E632",
            "ΑΥΤΑΙ": "\U0000E632",
            "ΑΥΤΑΣ": "\U0000E632",
            "ΧΑΙΡΕ": "\U0000E687",
            "ΥΠΕΡ": "\U0000E67A",
            "ΟΜΟΥ": "\U0000E670",
            "ΙΝΔΙΚ": "\U0000E698",
            # additional symbols
            "ΔΙΜΟΙ": "\U0000E698",
        }
        if text in unicode_map:
            return unicode_map[text]
        else:
            return '\u2105'

    @staticmethod
    def add(text: str, attrs: dict):
        """
        Prepares the handling of <add> by inserting arrow symbols and text in less-than or greater-than brackets. Text in
        less-than brackets will later be inserted as single line before the current line, text in greater-than brackets
        after the current line, cf. insert_lines().
        :param text: Text of <add>
        :param attrs: Attributes of <add>
        :return: String representation of parsed <add>
        """
        if "place" in attrs:
            place = attrs['place']
            if place == "above":
                if len(text) > 1:
                    return f"\u2191<{text}<"
                elif len(text) == 1:
                    return text
                else:
                    return ''
            elif place == "below":
                return f"\u2193>{text}>"
            elif place == "left":
                return f"\u2190<{text}<"
            elif place == "right":
                return f"\u2192>{text}>"
            elif place == "margin":
                return "\u2194"
            elif place == "bottom":
                return "\u21A1"
            elif place == "top":
                return "\u219F"
            elif place == 'interlinear':
                return f'<{text}<'
            else:
                return text

    @staticmethod
    def gtype(attrs: dict):
        """
        Handles the unicode representation of <g> with type attribute.
        :param attrs: Attributes of <g>
        :return: String representation of parsed <g>
        """
        if 'type' in attrs:
            unicode_map = {
                "anti-sigma": "\u037B",
                "antisigma": "\u037B",
                "antisigma-periestigmene": "\u037D",
                "apostrophe": "\u0027",
                "asteriskos": "\u002A",
                "backslash": "\uFE68",
                "backtick": "\u2E0C",
                "brevis": "\u02D8",
                "center-brace-closing": "\u23AC",
                "check": "\u2044",
                "chi-periestigmenon": "\u00B7\u03A7\u00B7",
                "chirho": "\u2627",
                "coronis": "\u2E0E",
                "coronis-lower-half": "\U000F0224",
                "cross": "\u271D",
                "dagger": "\u2020",
                "dash": "\u2012",
                "dicolon": "\u003A",
                "di-punctus": "\u205A",
                "diastole": "\u02BC",
                "diple": "\uFE65",
                "diple-obelismene": "\u291A",
                "diple-periestigmene": "\u2E16",
                "dipunct": "\u205A",
                "dot": "\u2E31",
                "dotted-obelos": "\u2E13",
                "double-horizontal-bar": "\u0305" + "\u0332",
                "double-slanting-stroke": "\u002F" + "\u002F",
                "double-vertical-bar": "\u2016",
                "downwards-ancora": "\u2E15",
                "filled-circle": "\u29BF",
                "filler": "\u07DF",
                "hedera": "\u2766",
                "high-puctus": "\u0387",
                "high-punctus": "\u0387",
                "high-puncuts": "\u0387",
                "hight-punctus": "\u0387",
                "hyphen": "\u2010",
                "hypodiastole": "\u2E12",
                "long-vertical-bar": "\u007C",
                "low-punctus": "\uFE52",
                "lower-brace-closing": "\u23AD",
                "lower-brace-opening": "\u23A9",
                "middot": "\u00B7",
                "middod": "\u00B7",
                "obelos": "\u2015",
                "obelos-periestigmenos": "\u2E13",
                "parens-deletion-closing": "\u23AC",
                "parens-deletion-opening": "\u23A8",
                "parens-lower-closing": "\u23A0",
                "parens-lower-opening": "\u239D",
                "parens-middle-closing": "\u239F",
                "parens-middle-opening": "\u239C",
                "parens-upper-closing": "\u239E",
                "parens-upper-opening": "\u239B",
                "parens-punctuation-closing": "\u23AC",
                "parens-punctuation-opening": "\u23A8",
                "parent-punctuation-opening": "\u23A8",
                "percent": "\u0025",
                "reverse-dotted-obelos": "\u00B7\u005C\u00B7",
                "rho-cross": "\u2CE8",
                "s-etous": "\U00010179",
                "short-vertical-bar": "\uE197",
                "sinusoid-stroke": "\uE0E7",
                "slanting-stroke": "\u002F",
                "slashed-N": "\u203E",
                "stauros": "\u2020",
                "swungdash": "\u007E",
                "tetrapunct": "\u2058",
                "tilde": "\u007E",
                "tripunct": "\u22EE",
                "upper-brace-closing": "\u23AB",
                "upper-brace-opening": "\u23A7",
                "upward-pointing-arrowhead": "\u2197",
                "upwards-ancora": "\u2E15",
                "x": "\u004E",
                "xs": "\u004E\u004E\u004E"
            }
            try:
                return unicode_map[attrs['type']]
            except KeyError:
                return ''
        else:
            return ''

    def hi(self, attrs: dict, text: str) -> str:
        """
        Handles the unicode representation of symbols specified in <hi>.
        :param attrs: Attributes of <hi>
        :param text: Text of <hi>
        :return: String representation of parsed <hi>
        """
        rend = attrs['rend']
        if rend == "diaeresis":
            return f'{text}\u0308'
        elif rend == "asper":
            return f'{text}\u0314'
        elif rend == "acute":
            return f'{text}\u0301'
        elif rend == "circumflex":
            return f'{text}\u0342'
        elif rend == "grave":
            return f'{text}\u0300'
        elif rend == "lenis":
            return f'{text}\u0313'
        elif rend == "overdot":
            return f'{text}\u0307'
        elif rend == "underlined" or rend == "underline":
            return self.add_char_to_each_letter(text, '\u0332')
        elif rend == "supraline":
            return self.add_char_to_each_letter(text, '\u0305')
        elif rend == "supraline-underline":
            return self.add_char_to_each_letter(text, '\u0305\u0332')
        else:
            return text
