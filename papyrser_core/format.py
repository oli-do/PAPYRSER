import logging
import re

from bs4 import BeautifulSoup

from config import debug_mode
from papyrser_utils.utils import greek_output


class Formatter:

    def __init__(self):
        """
        Initialize an object of the Formatter class providing functions for formatting, validating, and xml:lang
        extraction.
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.error_log = []
        self.changes = []
        self.langs = []

    def format_line(self, line_text: str) -> str:
        """
        Replaces gaps and supplied text at the beginning and end of a line. Adds up the number of supplied characters in
        the line text.
        :param line_text: Text of a transcription line
        :return: Processed line text
        """
        if debug_mode:
            self.logger.debug(f'format_line: Received line text {line_text}')
        # Remove \u2069
        line_text = line_text.replace('\u2069', '')
        # Remove <space> / vacat at the beginning and end of a line
        line_text = line_text.strip()
        line_text = re.sub(r'^(?:\? )+', '', line_text)
        line_text = re.sub(r'(?: \?)+$', '', line_text)
        # Remove lonely brackets
        if re.match(r'^[\[\]\-?]+$', line_text):
            only_gap_illegible_chars = re.sub(r'\[-+]', '', line_text)
            if '-' not in only_gap_illegible_chars:
                self.logger.debug(f"format_line: Returns '' (line deleted)")
                return ''
        # Remove empty square brackets
        line_text = line_text.replace('[]', '')
        # Replace gap and supplied at line beginning
        line_text = re.sub(r'^(?:\[-+]|\[\?])+', ']', line_text)
        # Replace gap and supplied at line end
        line_text = re.sub(r'(?:\[-+]|\[\?])+$', '[', line_text)
        # Find and combine gaps and supplied in the text
        to_combine = re.findall(r'(?:\[-+]){2,}', line_text)
        for string in to_combine:
            minus_count = str(string).count('-')
            filler = ''.join(["-" for _ in range(0, minus_count)])
            line_text = line_text.replace(string, f'[{filler}]')
        # combine [?] preceded or followed by gap in text
        line_text = re.sub(r'(\[-+])*\[\?](\[-+])*', '[?]', line_text)
        # Replace multiple [?] with single [?]
        line_text = re.sub(r'(?:\[\?]){2,}', '[?]', line_text)
        # handle multiple ℅
        line_text = re.sub('℅+', '℅', line_text)
        # make sure only capital letters exist (specifically in case of forbidden characters)
        line_text = line_text.upper()
        if debug_mode:
            self.logger.debug(f'format_line: Returns line text {line_text}')
        return line_text

    def get_languages(self, soup: BeautifulSoup):
        """
        Searches all xml:lang attributes in a BeautifulSoup (important for typo correction in validate_line) and saves
        the results to self.langs.
        :param soup: BeautifulSoup of a complete xml document
        """
        for tag in soup.find_all():
            if 'xml:lang' in tag.attrs:
                if not tag.attrs['xml:lang'] == 'en':
                    self.langs.append(tag.attrs['xml:lang'])
        self.langs = list(set(self.langs))
        if debug_mode:
            self.logger.debug(f'Found languages {self.langs}')

    def validate_line(self, line_text: str) -> str:
        """
        Validates line format.
        :param line_text: Text of a line
        :return: List of errors
        """
        if debug_mode:
            self.logger.debug(f'validate_line: Received line text "{line_text}')
        milestone_chars = '\u2e0f\u2015\u1F92\u223C'
        ex_chars = (
            '\u2C85\u2CAC\u2CAD\uE606\uE613\uE616\uE632\uE63D\uE63E\uE670\uE674\uE675\uE67A\uE67D\uE687\uE688\uE689'
            '\uE68A\uE68B\uE68C\uE68E\uE691\uE696\uE698\uE6A3\U00002CE9\U00010175\U00010179\U0001017A\U0001017B'
            '\U0001017C\U0001017D\U0001017E\U0001017F\U00010180\U00010183\U00010184\U00010185\U00010186\U00010187')
        add_chars = '\u2191\u2193\u2190\u2192\u2194\u21A1\u219F\u2105'
        gtype_chars = (
            '\u037B\u0027\u002A\uFE68\u2E0C\u2044\u00B7\u03A7\u2627\u2E0E\u271D\u2020\u2012\u205A\u02BC\uFE65'
            '\u291A\u2E31\u2E13\u2E15\u29BF\u07DF\u0387\u2010\u2E12\u007C\uFE52\u2015\u23AC\u23A8\u23A0\u239D'
            '\u239F\u239C\u239E\u239B\u0025\u005C\u2CE8\U00010179\uE197\uE0E7\u002F\u203E\u2058\u007E\u22EE'
            '\u2197\u004E\u037B\u02D8\u23AC\U000F0224\u003A\u0305\u0332\u002F\u002F\u2016\u2766\u0387\u23AD\u23A9'
            '\u00B7\u2E13\u007E\u23AB\u23A7\u037D\u2E16')
        hi_chars = '\u0308\u0314\u0301\u0342\u0300\u0313\u0307\u0332\u0305'
        unclear_char = '\u0323'
        other_valid_chars = '\u2CE8\U00010177 '
        special_chars = (milestone_chars + ex_chars + add_chars + gtype_chars + hi_chars + unclear_char
                         + other_valid_chars)
        pattern_allowed_chars = r'[' + special_chars + greek_output + r'\[\]\-\?' + r']'
        range_without_brackets = r'[\-' + greek_output + special_chars + r']+'
        range_with_brackets = r'[\-\[\]\?' + greek_output + special_chars + r']*'
        valid_pattern1 = r'^\]?' + range_without_brackets + r'\[?$'
        valid_pattern2 = r'^\]?' + range_without_brackets + range_with_brackets + range_without_brackets + r'\[?$'
        changes = []
        if not (re.match(valid_pattern1, line_text) or re.match(valid_pattern2, line_text)):
            # Invalid characters or gap handling --> check for invalid characters
            forbidden_chars = []
            for c in line_text:
                if not re.match(pattern_allowed_chars, c):
                    forbidden_chars.append(c)
            if not forbidden_chars:
                msg = f'validate_line: Invalid gap handling: {line_text}'
                if debug_mode:
                    self.logger.warning(msg)
                self.error_log.append(msg)
            else:
                self.error_log.append(f'Forbidden character(s) {forbidden_chars} found in "{line_text}"')
                if debug_mode:
                    self.logger.warning(
                        f'validate_line: Forbidden character(s) {forbidden_chars} found in "{line_text}')
                # Automatically correct typos (wrong Latin characters in Greek text)
                if len(self.langs) == 1 and self.langs[0] == 'grc':
                    for c in forbidden_chars:
                        if re.match(r'[A-Z]', c):
                            latin_chars = 'ABEHIKMNOPTXYZ'
                            greek_chars = 'ΑΒΕΗΙΚΜΝΟΡΤΧΥΖ'
                            translation = str.maketrans(latin_chars, greek_chars)
                            if c in latin_chars:
                                self.error_log = []
                                target = c.translate(translation)
                                line_text = line_text.replace(c, target)
                                msg = f'Changed "{c}" to "{target}" in {line_text}'
                                if debug_mode:
                                    self.logger.info(msg)
                                changes.append(msg)
        if changes:
            self.changes.append(changes)
            return self.validate_line(line_text)
        if line_text.__contains__('[]'):
            msg = 'Contains "[]"'
            if debug_mode:
                self.logger.warning(msg)
            self.error_log.append(msg)
        if debug_mode:
            self.logger.debug(f'validate_line: returns line text "{line_text}"')
        return line_text
