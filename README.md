## About PAPYRSER
PAPYRSER is a fast and accurate Python-based parser for digitally edited TEI-XML transcriptions of monolingual Greek 
papyri as found on https://papyri.info/. TEI-XML input is parsed to standardized output according to 
[the D5 Standard](#the-d5-standard). PAPYRSER is designed to be user-friendly and can easily be set up and run by users 
with no previous Python experience. 

Developed by [Oliver Donath](https://github.com/oli-do).

## Running PAPYRSER
### Requirements
- Valid installation of **Python 3** (Python 3.9 or newer is recommended)
- Installation of packages listed in **requirements.txt** (install via "pip install -r requirements.txt" if necessary)

### Configuration
- Open **config.py** to configure PAPYRSER.
- PAPYRSER supports [TM numbers](https://www.trismegistos.org/) as well as 
[DBB collection names](https://github.com/papyri/idp.data/tree/master/DDB_EpiDoc_XML), e.g. "cpr".
- Make sure to enter a *papyrus_target* as described in **config.py**.
- The settings *debug_mode*, *ignore_formatting_issues*, *write_to_json*, *write_to_txt* can be set to *True* or *False*
as needed for the current use case.
- If you do not have a copy of https://github.com/papyri/idp.data on your device, you may consider setting 
*always_update_github* to *True* to keep the data up to date; however, be aware that this will significantly slow down
the script, as all data will be downloaded after every start.
- If you already have a copy of the files, you can set *idp_data_path* to your custom directory. In that case, make sure
that *always_update_github* is set to *False*.
- If your custom directory is regularly updated or synchronized with GitHub, set *always_do_indexing* to *True* 
- PAPYRSER will never write or change any files in a custom directory specified by *idp_data_path*

### Execution
- Run **main.py** to start PAPYRSER with the settings configured in **config.py**.
- Depending on your configuration, the data from https://github.com/papyri/idp.data will be downloaded and extracted to
`{main_path}/papyri_data/idp.data-master`. 
- An index of TM numbers with the path to their respective XML file will be written to 
`{main_path}/papyri_data/tm_index.json`.
- Parser results will be written to 
`{main_path}/export/{export_id}/txt` and/or `{main_path}/export/{export_id}/json`.

## The D5 Standard
The **D5** standard represents an advancement of the **D4** standard previously established by Dr. Holger Essler 
(https://github.com/HolgerEssler). It follows these basic conversion rules:

- **\<lb>** → new line
- **\<gap>** or **\<supplied>** (in text) → e.g. **[---]**, where each minus represents one character
- **\<gap>** or **\<supplied>** (line beginning) → ]
- **\<gap>** or **\<supplied>** (end of line) → [
- **\<gap extent="unknown">** → [?]
- **\<gap reason="illegible">** → e.g. **-----** where each minus represents one character
- **\<unclear>** → character + combining dot below (0x0323)
- **\<milestone>** → new line + matching character
- **\<ex>** → matching symbol (if **\<expan>** does not contain text as direct child)
- **\<g type>** → matching symbol
- **\<hi rend>** → text + special character(s)
- **\<add>** → arrows indicating where text has been added, text itself is moved to the previous or next line
- Greek character with diacriticals → Greek majuscule without diacriticals

### Input > Output Example
    <lb n="380"/>
    <supplied reason="lost">Ἀρ</supplied>
    <unclear>κά</unclear>
        δι τὸν γεγρα
    <supplied reason="lost">μμένο</supplied>
        ν χρόν
    <unclear>ον</unclear>
    <gap reason="lost" quantity="1" unit="character"/>
    <gap reason="illegible" quantity="4" unit="character"/>`

Source: https://papyri.info/ddbdp/cpr;18;18/source (accessed 06/14/2025)

>`]Κ̣Α̣ΔΙΤΟΝΓΕΓΡΑ[-----]ΝΧΡΟΝΟ̣Ν̣[-]----`*

<p>* Combining dots below may seem misplaced due to rendering, but are correctly 
combined with Greek majuscule characters<br>Source: PAPYRSER v1.0</p>

## For Python Developers
### Structure
- **config.py**: Settings and configuration
- **main.py**: Initiates the workflow of the script
- **parser.py**: Contains the class **TEIParser**, which starts the parsing processes by calling *process_tei()*
- **format.py**: Contains the class **Formatter**, which provides functions for formatting and syntax validation
- **util.py**: Contains classes **IOHandler** and **PapyriDownloader** as well as utility functions

### Debug Mode
Enabling *debug_mode* in **config.py** will keep track of all conversion, formatting and validating steps in detail,
allowing you to identify potential issues. Debug messages are written to **log.txt**.

### Modifying PAPYRSER to support multilingual papyri
You can achieve support of multilingual papyri by modifying the *greek_input* and *greek_output* strings of **util.py**.
Add new input characters to *greek_input* and their corresponding output characters to *greek_output*. Corresponding 
characters must be at the same index of each string.

### Adding new entries to TEIParser.ex(), .gtype(), or .milestone()
<p>While PAPYRSER supports the most important symbols and special characters occurring on papyri.info, some cases are
not yet supported. If you want to add additional symbols, please follow these steps: </p>

1. Add a dictionary entry to *unicode_map* of **TEIParser**.ex(), .gtype(), or .milestone()
2. Add the new character to *ex_chars*, *gtype_chars* or *milestone_chars* of **Formatter**.validate_line()

#### List of known \<g type> strings not (yet) supported
"boundary-mark"<br>
"charakteres"<br>
"chi"<br>
"decussis"<br>
"deletion-mark"<br>
"eisthesis"<br>
"guide-dot"<br>
"large-parens"<br>
"line-filler"<br>
"line-filler-dot"<br>
"longum"<br>
"magical-symbol"<br>
"marginal-mark"<br>
"modern-question-mark"<br>
"monogram"<br>
"ornament"<br>
"paraphe"<br>
"sigla"<br>
"sign"<br>
"signs"<br>
"small-circle"<br>
"space-filler"<br>
"stacking-line"<br>
"stichos"<br>
"symbol"<br>
"tachygraphic-marks"<br>
"tachygraphic-marks-milne-81"<br>
"tachygraphic-marks-milne-82"<br>
"tachygraphic-marks-milne-83"<br>
"tachygraphic-marks-milne-84"<br>
"tachygraphic-marks-milne-85"<br>
"tachygraphic-marks-milne-88"<br>
"tachygraphic-marks-milne-89"<br>
"tachygraphic-marks-milne-90"<br>
"tachygraphic-marks-milne-91"<br>
"tachygraphic-marks-milne-92"<br>
"tachygraphic-marks-milne-95"<br>
"tachygraphic-marks-milne-96"<br>
"word-sep-apostrophe"<br>
"word-sep-comma"