import json
import logging
import os

from config import debug_mode, main_path


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
        try:
            os.makedirs(path, exist_ok=True)
        except (OSError, IOError) as e:
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

    def write_to_json(self, tm: int, original_filename: str, content: list[list[str]], div_data: list[dict]) -> str:
        """
        Writes parsed data to a json file with metadata in head, text parts in body. See documentation for detailed info
        on the json structure.
        :param tm: TM number
        :param original_filename: Name of the XML file the parser results are based on
        :param content: parser results returned by convert_to_d4
        :return: Path to the written file
        """
        target_path = os.path.join(main_path, 'export')
        target_path = os.path.join(target_path, self.export_directory)
        self.create_folder(target_path)
        target_path = os.path.join(target_path, 'json')
        self.create_folder(target_path)
        path = os.path.join(target_path, f'{tm}_{original_filename}.json')
        text_blocks = []
        for i in range(len(content)):
            data = div_data[i]
            data['text'] = content[i]
            text_blocks.append(data)
        content = {'text_blocks': text_blocks}
        self.write_text_to_file(path, json.dumps(content, ensure_ascii=False))
        return path

    def write_to_txt(self, tm: int, original_filename: str, content: list[list[str]]) -> str:
        """
        Writes parsed data to a txt file.
        :param tm: TM number
        :param original_filename: Name of the XML file the parser results are based on
        :param content: parser results returned by convert_to_d4
        :return: Path to the written file
        """
        target_path = os.path.join(main_path, 'export')
        target_path = os.path.join(target_path, self.export_directory)
        self.create_folder(target_path)
        target_path = os.path.join(target_path, 'txt')
        self.create_folder(target_path)
        path = os.path.join(target_path, f'{tm}_{original_filename}.txt')
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
