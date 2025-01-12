import re
from pathlib import Path

from configparser import (
    ConfigParser, DuplicateSectionError, DuplicateOptionError,
    MissingSectionHeaderError, ParsingError, Error, SectionProxy
)
from logging import Logger
import chardet
from common.logger import get_logger

logger: Logger = get_logger()


# https://docs.python.org/3/library/configparser.html
class ConfigReader(ConfigParser):
    """The custom INI configuration parser for PapiWeb."""

    def __init__(self, ini_file: Path):
        super().__init__(interpolation=None, empty_lines_in_values=False)
        self.__ini_file: Path = ini_file
        self.__infos: list[str] = []
        self.__warnings: list[str] = []
        self.__errors: list[str] = []
        if not self.ini_file.exists():
            self.add_error('fichier non trouvé')
            return
        if not self.ini_file.is_file():
            self.add_error(f'{self.ini_file} n\'est pas un fichier')
            return
        try:
            files_read: list[str] = []
            encoding: str = 'utf-8-sig'
            try:
                logger.debug('lecture de %s en %s...', self.ini_file, encoding)
                files_read = self.read(self.__ini_file, encoding=encoding)
            except UnicodeDecodeError:
                logger.debug('la lecture de %s en %s a échoué, recherche de l\'encodage...',
                             self.ini_file, encoding)
                detected_encoding: str
                with open(self.__ini_file, "rb") as f:
                    detected_encoding: str = chardet.detect(f.read())['encoding']
                logger.debug('encodage détecté : %s', detected_encoding)
                if detected_encoding != 'utf-8':
                    logger.debug('lecture de %s en %s...', self.ini_file, detected_encoding)
                    files_read = self.read(self.__ini_file, encoding=detected_encoding)
            if str(self.__ini_file) not in files_read:
                self.add_error(f'impossible de lire {self.__ini_file}')
                return
        except DuplicateSectionError as dse:
            self.add_error(f'rubrique dupliquée à la ligne {dse.lineno}', dse.section)
            return
        except DuplicateOptionError as doe:
            self.add_error(f'option dupliquée à la ligne {doe.lineno}', doe.section, doe.option)
            return
        except MissingSectionHeaderError as mshe:
            self.add_error(f'la première rubrique manque à la ligne {mshe.lineno} : [{bytes(mshe.line, "utf-8")}]')
            return
        except ParsingError as pe:
            self.add_error(f'erreur de parsing: {pe.message}')
            return
        except Error as e:
            self.add_error(f'erreur: {e.message}')
            return

    @property
    def ini_file(self) -> Path:
        return self.__ini_file

    def __format_message(self, text: str, section_key: str | None, key: str | None):
        if section_key is None:
            return f'{self.ini_file.name}: {text}'
        elif key is None:
            return f'{self.ini_file.name}[{section_key}]: {text}'
        else:
            return f'{self.ini_file.name}[{section_key}].{key}: {text}'

    def add_debug(self, text: str, section_key: str | None = None, key: str | None = None):
        """Adds a debug-level message and logs it"""
        message = self.__format_message(text, section_key, key)
        logger.debug(message)

    @property
    def infos(self) -> list[str]:
        return self.__infos

    def add_info(self, text: str, section_key: str | None = None, key: str | None = None):
        """Adds an info-level message and logs it"""
        message = self.__format_message(text, section_key, key)
        logger.info(message)
        self.__infos.append(message)

    @property
    def warnings(self) -> list[str]:
        return self.__warnings

    def add_warning(self, text: str, section_key: str | None = None, key: str | None = None):
        """Adds a warning-level message and logs it"""
        message = self.__format_message(text, section_key, key)
        logger.warning(message)
        self.__warnings.append(message)

    @property
    def errors(self) -> list[str]:
        return self.__errors

    def add_error(self, text: str, section_key: str | None = None, key: str | None = None):
        """Adds an error-level message and logs it"""
        message = self.__format_message(text, section_key, key)
        logger.error(message)
        self.__errors.append(message)

    def getint_safe(self, section_key: str, key: str, minimum: int = None, maximum: int = None) -> int | None:
        """Tries to convert the value associated to the given key in the
        given section to an integer, returns None if it can't be converted
        properly.
        Optionally performs bounds checks and returns None if the value is out
        of the given bounds."""
        try:
            val: int = self.getint(section_key, key)
            if minimum is not None and val < minimum:
                return None
            if maximum is not None and val > maximum:
                return None
            return val
        except ValueError:
            return None

    def getboolean_safe(self, section_key: str, key: str) -> bool | None:
        """Tries to convert the value associated to the given key in the given
        section to a boolean.
        '1', 'true', 'on', 'yes' are converted to True;
        '0', 'false', 'off', 'no' are converted to False.
        All other values return None."""
        try:
            val: bool = self.getboolean(section_key, key)
            return val
        except ValueError:
            return None

    def get_subsection_keys_with_prefix(self, prefix: str, first_level_only: bool = True) -> list[str]:
        """Returns the list of all subsections with the given prefix.
        If *first_level_only* is True, only direct subsections are returned.
        """
        subsection_keys: list[str] = []
        for section_key in self.sections():
            if first_level_only:
                pattern = r'^{}\.([^.]+)$'
            else:
                pattern = r'^{}\.([^.]+(\.[^.]+)*)$'
            matches = re.match(pattern.format(prefix.replace('.', '\\.')), section_key)
            if matches:
                subsection_keys.append(matches.group(1))
        return subsection_keys

    def rename_section(self, old_section_key: str, new_section_key: str):
        """Renames the section *old_section_key* into *new_section_key*.
        IMPORTANT: This assumes we do not rename the default section"""
        # NOTE(Amaras) this can add values that are in DEFAULTSEC if any.
        # This can also cause a crash if we're trying to delete DEFAULTSEC,
        # as deleting DEFAUTLSEC causes a ValueError.
        self[new_section_key] = self[old_section_key]
        del self[old_section_key]

    def get_value_with_warning(
        self,
        section: SectionProxy,
        section_key: str,
        key: str,
        target_type: type,
        predicate,
        default_value,
        *messages,
    ):
        """Given a *section* and a *key*, tries to convert the value associated
        with them to the given *target_type*, assuming it passes the given
        *predicate*.
        If any problem arises, adds an error or a warning and returns the
        default value.
        """
        try:
            value = target_type(section[key])
            assert predicate(value)
            return value
        except TypeError:
            self.add_error(messages[0], section_key)
            return default_value
        except KeyError:
            self.add_warning(messages[1], section_key, key)
            return default_value
        except ValueError:
            self.add_warning(messages[2], section_key, key)
            return default_value
        except AssertionError:
            self.add_warning(messages[3], section_key, key)
            return default_value
