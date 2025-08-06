import unittest

from bs4 import BeautifulSoup

from papyrser_core.format import Formatter
from papyrser_core.parser import TEIParser
from papyrser_io.handler import IOHandler


class TestFormatter(unittest.TestCase):

    def test_format_line(self):
        formatter = Formatter()
        # Remove \u2069
        test_2069 = formatter.format_line('\u2069')
        self.assertEqual('', test_2069)
        # space at line beginning and end
        test_space = formatter.format_line(' ? Α ? ')
        self.assertEqual('Α', test_space)
        # Remove lonely brackets
        test_lonely = formatter.format_line('[------]')
        self.assertEqual('', test_lonely)
        # Remove empty square brackets
        test_empty = formatter.format_line('[]')
        self.assertEqual('', test_empty)
        # Replace gap and supplied at line beginning and end
        test_gap = formatter.format_line('[?][----]Α[?][--]')
        self.assertEqual(']Α[', test_gap)
        # Find and combine gaps and supplied in the text
        test_combine = formatter.format_line('Α[---][----]Β')
        self.assertEqual('Α[-------]Β', test_combine)
        # combine [?] preceded or followed by gap in text
        test_combine = formatter.format_line('Α[---][--][?]Β')
        self.assertEqual('Α[?]Β', test_combine)
        # Replace multiple [?] with single [?]
        test_multiple = formatter.format_line('Α[?][?]Β')
        self.assertEqual('Α[?]Β', test_multiple)
        # handle multiple ℅
        test_char = formatter.format_line('Α℅℅')
        self.assertEqual('Α℅', test_char)
        # convert to capital letter
        test_capital = formatter.format_line('αβ')
        self.assertEqual('ΑΒ', test_capital)

    def test_get_languages(self):
        formatter = Formatter()
        xml = ('<body><head xml:lang="en"/><div xml:lang="grc" type="edition" xml:space="preserve">'
               '<lb n="1"/>ΑΒΓΔΕΦ<lb n="2"/><foreign xml:lang="la">comes</foreign>"'
               '</div></head></body>')
        soup = BeautifulSoup(xml, 'lxml-xml')
        formatter.get_languages(soup)
        self.assertTrue('la' in formatter.langs)
        self.assertTrue('grc' in formatter.langs)

    def test_validate_line(self):
        formatter = Formatter()
        formatter.langs = ['grc']
        typos = formatter.validate_line('ABEHIKMOPTXYZ')
        self.assertEqual('ΑΒΕΗΙΚΜΟΡΤΧΥΖ', typos)
        formatter.validate_line('ΑΒΓΔΕΦ093[]')
        self.assertTrue(len(formatter.error_log) == 2)


class TestTEIParser(unittest.TestCase):
    @staticmethod
    def convert(xml_input: str):
        xml = f'<div n="test" subtype="unittest"><ab><lb n="1"/>Α{xml_input}Β</ab></div>'
        io_handler = IOHandler()
        parser = TEIParser(io_handler)
        results = parser.convert_to_d5(xml, True)
        lines = [data['lines'] for data in results]
        return lines

    def test_convert_to_d5_gap(self):
        test = self.convert('<gap reason="lost" atLeast="11" atMost="15" unit="character"/>')
        self.assertEqual([['Α[-------------]Β']], test)
        test = self.convert('<gap reason="lost" quantity="7" unit="line"/>')
        self.assertEqual([['ΑΒ']], test)
        test = self.convert('<gap reason="illegible" quantity="5" unit="line"/>')
        self.assertEqual([['ΑΒ']], test)
        test = self.convert('<gap reason="illegible" quantity="3" unit="character"/>')
        self.assertEqual([['Α---Β']], test)
        test = self.convert('<gap reason="illegible" extent="unknown" unit="character"/>')
        self.assertEqual([['Α[?]Β']], test)
        test = self.convert('<gap reason="illegible" atLeast="9" atMost="10" unit="character"/>')
        self.assertEqual([['Α----------Β']], test)
        test = self.convert('<gap reason="illegible" extent="unknown" unit="character"><desc>vestiges</desc></gap>')
        self.assertEqual([['Α[?]Β']], test)

    def test_convert_to_d5_space(self):
        test = self.convert('<space extent="unknown" unit="character"/>')
        self.assertEqual([['Α ? Β']], test)
        test = self.convert('<space quantity="3" unit="character"/>')
        self.assertEqual([['Α   Β']], test)
        test = self.convert('<space atLeast="2" atMost="5" unit="character"/>')
        self.assertEqual([['Α    Β']], test)
        test = self.convert('<space extent="unknown" unit="line"/>')
        self.assertEqual([['ΑΒ']], test)

    def test_convert_to_d5_add(self):
        test = self.convert('<add place="above">Γ</add>')
        self.assertEqual([['ΑΓΒ']], test)
        test = self.convert('<add place="above">ΓΔ</add>')
        self.assertEqual([['ΓΔ', 'Α↑Β']], test)
        test = self.convert('<add place="below">Γ</add>')
        self.assertEqual([['Α↓Β', 'Γ']], test)
        test = self.convert('<add place="left">Γ</add>')
        self.assertEqual([['Γ', 'Α←Β']], test)
        test = self.convert('<add place="right">Γ</add>')
        self.assertEqual([['Α→Β', 'Γ']], test)
        test = self.convert('<add place="interlinear">Γ</add>')
        self.assertEqual([['Γ', 'ΑΒ']], test)
        test = self.convert('<add rend="sling" place="margin">Γ</add>')
        self.assertEqual([['Α↔Β']], test)

    def test_convert_to_d5_hi(self):
        test = self.convert('<hi rend="tall">Γ</hi>')
        self.assertEqual([['ΑΓΒ']], test)
        test = self.convert('<hi rend="supraline">Γ</hi>')
        self.assertEqual([['ΑΓ̅Β']], test)
        test = self.convert('<hi rend="supraline-underline">Γ</hi>')
        self.assertEqual([['ΑΓ\u0305\u0332Β']], test)
        test = self.convert('υ<hi rend="diaeresis">ἱ</hi>οῦ')
        self.assertEqual([['ΑΥΪΟΥΒ']], test)
        test = self.convert('<hi rend="asper">ὧ</hi>')
        self.assertEqual([['ΑὩΒ']], test)
        test = self.convert('<hi rend="acute">ὃ</hi>')
        self.assertEqual([['ΑΌΒ']], test)
        test = self.convert('<hi rend="circumflex">ὑ</hi>')
        self.assertEqual([['ΑΥ͂Β']], test)
        test = self.convert('<hi rend="lenis">Ἀ</hi>')
        self.assertEqual([['ΑἈΒ']], test)
        test = self.convert('<hi rend="asper"><hi rend="acute">ἵ</hi></hi>')
        self.assertEqual([['ΑἽΒ']], test)
        test = self.convert('<hi rend="diaeresis"><gap reason="illegible" quantity="1" unit="character"/></hi>')
        self.assertEqual([['Α-̈Β']], test)
        test = self.convert('<hi rend="acute"><gap reason="lost" quantity="1" unit="character"/></hi>')
        self.assertEqual([['Α[-]́Β']], test)
        test = self.convert(
            '<hi rend="asper"><hi rend="acute"><gap reason="illegible" quantity="1" unit="character"/></hi></hi>')
        self.assertEqual([['Α-̔́Β']], test)
        test = self.convert(
            '<hi rend="asper"><hi rend="acute"><gap reason="lost" quantity="1" unit="character"/></hi></hi>')
        self.assertEqual([['Α[-]̔́Β']], test)

    def test_convert_to_d5_supplied(self):
        test = self.convert('<supplied reason="omitted">γ</supplied>')
        self.assertEqual([['ΑΒ']], test)
        test = self.convert('<supplied reason="lost">γ</supplied>')
        self.assertEqual([['Α[-]Β']], test)
        test = self.convert('<supplied evidence="parallel" reason="undefined">Πόσεις</supplied>')
        self.assertEqual([['Α[------]Β']], test)

    def test_convert_to_d5_surplus(self):
        test = self.convert('<surplus>γ</surplus>')
        self.assertEqual([['ΑΓΒ']], test)

    def test_convert_to_d5_del(self):
        test = self.convert('<del rend="erasure">γ</del>')
        self.assertEqual([['ΑΒ']], test)

    def test_convert_to_d5_expan(self):
        test = self.convert('<expan>Γ<ex cert="low">ανίδι</ex></expan>')
        self.assertEqual([['ΑΓΒ']], test)
        test = self.convert('<expan><ex>ἔτους</ex></expan>')
        self.assertEqual([['Α\U00010179Β']], test)

    def test_convert_to_d5_abbr(self):
        test = self.convert('<abbr>γ</abbr>')
        self.assertEqual([['ΑΓΒ']], test)

    def test_convert_to_d5_other_editorial_conventions(self):
        test = self.convert('<handShift new="m4"/>')
        self.assertEqual([['ΑΒ']], test)
        test = self.convert('<note xml:lang="en">BGU 1,108,r reprinted in WChr 227 </note>')
        self.assertEqual([['ΑΒ']], test)
        test = self.convert('<q>γ</q>')
        self.assertEqual([['ΑΓΒ']], test)

    def test_convert_to_d5_apparatus(self):
        test = self.convert('<choice><reg>φρόντι<supplied reason="lost">σ</supplied>ον</reg><orig>φρόνδει'
                            '<supplied reason="lost">σ</supplied><unclear>ο</unclear>ν</orig></choice>')
        self.assertEqual([['ΑΦΡΟΝΔΕΙ[-]Ο̣ΝΒ']], test)
        test = self.convert('<choice><reg cert="low">ἀνοίγεται </reg><reg cert="low">ἀνοίεται </reg>'
                            '<orig><unclear>ἀ</unclear>νύεται</orig></choice>')
        self.assertEqual([['ΑΑ̣ΝΥΕΤΑΙΒ']], test)
        test = self.convert('<app type="alternative"><lem>Ὀχυρυγχίτου</lem><rdg>Ὀξυρυγχίτου νομοῦ</rdg></app>')
        self.assertEqual([['ΑΟΧΥΡΥΓΧΙΤΟΥΒ']], test)
        test = self.convert('<app type="alternative">'
                            '<lem>'
                            '<gap reason="lost" extent="unknown" unit="character"/>'
                            '<gap reason="illegible" quantity="1" unit="character"/>'
                            'αμεν'
                            '<gap reason="illegible" quantity="1" unit="character"/><unclear>ν</unclear>'
                            '</lem>'
                            '<rdg>'
                            '<supplied reason="lost">ἀπογρα</supplied>ψ<unclear>α</unclear>μένη<unclear>ν</unclear>'
                            '</rdg>'
                            '<rdg><gap reason="lost">θρε</gap>ψ<unclear>α</unclear>μένη<unclear>ν</unclear>'
                            '</rdg>'
                            '</app>')
        self.assertEqual([['Α[?]-ΑΜΕΝ-Ν̣Β']], test)

    def test_convert_to_d5_correction(self):
        test = self.convert('<subst><add place="inline">τοῦ</add><del rend="corrected">της</del></subst>')
        self.assertEqual([['ΑΤΟΥΒ']], test)
        test = self.convert('<choice><corr>τιμὴν</corr><sic>τμμὴν</sic></choice>')
        self.assertEqual([['ΑΤΜΜΗΝΒ']], test)
        test = self.convert('<app type="editorial"><lem resp="BGU 1 p.357"><num value="23">κγ</num></lem>'
                            '<rdg><num value="26">κϛ</num></rdg></app>')
        self.assertEqual([['ΑΚΓΒ']], test)

    def test_convert_to_d5_milestone(self):
        test = self.convert('<milestone rend="paragraphos" unit="undefined"/><lb n="2"/>')
        self.assertEqual([['Α', '⸏', 'Β']], test)
        test = self.convert('<milestone rend="horizontal-rule" unit="undefined"/><lb n="2"/>')
        self.assertEqual([['Α', '―', 'Β']], test)
        test = self.convert('<milestone rend="wavy-line" unit="undefined"/><lb n="2"/>')
        self.assertEqual([['Α', '∼', 'Β']], test)
        test = self.convert('<milestone rend="diple-obelismene" unit="undefined"/><lb n="2"/>')
        self.assertEqual([['Α', '⸐', 'Β']], test)
        test = self.convert('<milestone rend="coronis" unit="undefined"/><lb n="2"/>')
        self.assertEqual([['Α', '⸎', 'Β']], test)

    def test_convert_to_d5_gtype(self):
        test = self.convert('<unclear><g type="check"/></unclear>')
        self.assertEqual([['Α⁄Β']], test)
        test = self.convert('<g type="chirho"/>')
        self.assertEqual([['Α☧Β']], test)
        test = self.convert('<g type="parens-punctuation-opening"/> <g type="parens-punctuation-closing"/>')
        self.assertEqual([['Α⎨⎬Β']], test)
