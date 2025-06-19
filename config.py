import os

# Sets the target for the parser; can be a DDB collection name as str, e.g. 'cpr', a TM number as int, e.g. 5015, a
# list of TM numbers as list[int], e.g. [5015, 5016, 5017], or a list of DDB collection names as list[str].
papyrus_target: str | int | list[int] | list[str] = 37203

# Set debug_mode to True to receive detailed debug information in log.txt. WARNING: This disables multiprocessing.
debug_mode: bool = False

# Normally, parser results containing invalid characters or character sequences are not written to a file.
# ignore_formatting_issues can be set to True to write files despite such issues. False is recommended.
ignore_formatting_issues: bool = False

# Write output to json
write_to_json: bool = True

# Write output to txt
write_to_txt: bool = True

# Keep downloaded GitHub data up to date. False is recommended for faster results.
always_update_github: bool = False

# It is recommended not to change the following three default paths. If necessary, main_path may be changed.
main_path: str = os.path.dirname(__file__)
papyri_data_path: str = os.path.join(main_path, 'papyri_data')
tm_index_path: str = os.path.join(papyri_data_path, 'tm_index.json')

# If you already have a copy of https://github.com/papyri/idp.data on your device, you can set a custom idp_data_path
# (e.g. idp_data_path: str = "C:\\Users\\User\\Papyri\\idp.data") to the directory as str.
# Default: idp_data_path: str = os.path.join(papyri_data_path, 'idp.data-master')
idp_data_path: str = os.path.join(papyri_data_path, 'idp.data-master')

# Set always_do_indexing to True to always start the indexing process when running the script.
# This is recommended, when your custom idp_data_path is regularly updated or synchronized with GitHub.
always_do_indexing: bool = False
