from functools import cached_property, cache
from math import ceil
from typing import TYPE_CHECKING

from common import format_timestamp_date_time
from common.papi_web_config import PapiWebConfig
from data.screen import Screen
from data.tournament import Tournament
from data.util import ScreenType
from database.store import StoredFamily

if TYPE_CHECKING:
    from data.event import Event


class Family:
    """A data wrapper around a StoredFamily."""
    def __init__(
            self,
            event: 'Event',
            stored_family: StoredFamily,
    ):
        self.event: 'Event' = event
        self.stored_family: StoredFamily = stored_family
        self._calculated_first: int | None = None
        self._calculated_last: int | None = None
        self._calculated_number: int | None = None
        self._calculated_parts: int | None = None

    @property
    def id(self) -> int:
        return self.stored_family.id

    @property
    def type(self) -> ScreenType:
        return ScreenType.from_str(self.stored_family.type)

    @property
    def public(self) -> bool:
        return self.stored_family.public

    @property
    def uniq_id(self) -> str:
        return self.stored_family.uniq_id

    @property
    def name(self) -> str:
        name: str = self.stored_family.name if self.stored_family.name else '%t (%f à %l)'
        return name.replace('%t', self.tournament.name)

    @property
    def tournament_id(self) -> int:
        return self.stored_family.tournament_id

    @property
    def tournament(self) -> Tournament:
        return self.event.tournaments_by_id[self.tournament_id]

    @property
    def columns(self) -> int:
        if self.stored_family.columns:
            return self.stored_family.columns
        return 1

    @property
    def menu_link(self) -> bool:
        return self.stored_family.menu_link

    @property
    def menu_text(self) -> str:
        return self.stored_family.menu_text

    @cached_property
    def menu_label(self) -> str | None:
        if not self.menu_link:
            return None
        if self.menu_text:
            return self.menu_text
        single_tournament: bool = len(self.event.tournaments_by_id) == 1
        text: str
        if self.type == ScreenType.Players or not self.tournament.current_round:
            text = PapiWebConfig().default_players_screen_menu_text(
                single_tournament=single_tournament, first_last=True)
        else:
            text = PapiWebConfig().default_boards_screen_menu_text(
                single_tournament=single_tournament, first_last=True)
        return text.replace('%t', self.tournament.name)

    @property
    def menu(self) -> str:
        return self.stored_family.menu

    @property
    def timer_id(self) -> int | None:
        return self.stored_family.timer_id

    @property
    def timer(self) -> Tournament | None:
        return self.event.timers_by_id[self.timer_id] if self.timer_id else None

    @property
    def input_exit_button(self) -> bool:
        if self.stored_family.input_exit_button is None:
            return PapiWebConfig.default_input_exit_button
        return self.stored_family.input_exit_button

    @property
    def players_show_unpaired(self) -> bool:
        if self.stored_family.players_show_unpaired is None:
            return PapiWebConfig.default_players_show_unpaired
        return self.stored_family.players_show_unpaired

    @property
    def icon_str(self) -> str:
        return self.type.icon_str

    @property
    def type_str(self) -> str:
        return str(self.type)

    @property
    def first(self) -> int | None:
        return self.stored_family.first

    @property
    def last(self) -> int | None:
        return self.stored_family.last

    @property
    def parts(self) -> int | None:
        return self.stored_family.parts

    @property
    def number(self) -> int | None:
        return self.stored_family.number

    @property
    def last_update(self) -> float | None:
        return self.stored_family.last_update

    @property
    def last_update_str(self) -> str | None:
        return format_timestamp_date_time(self.last_update)

    @cache
    def _calculate_screens(self) -> bool:
        if not self.tournament.rounds:
            self.error = f'Le tournoi [{self.tournament.uniq_id}] ne peut être lu, famille ignorée.'
            self.event.add_warning(self.error, family=self)
            return False
        players_instead_of_boards: bool
        match ScreenType.from_str(self.type):
            case ScreenType.Boards | ScreenType.Input:
                if self.tournament.current_round:
                    players_instead_of_boards = False
                    total_items_number: int = len(self.tournament.boards)
                    if self.first:
                        if self.first > total_items_number:
                            self.error = f'Le tournoi ne comporte que [{total_items_number}] échiquiers, ' \
                                         f'famille ignorée.'
                            self.event.add_warning(self.error, family=self)
                            return False
                        self._calculated_first = self.first
                    else:
                        self._calculated_first = 1
                    if self.last:
                        self._calculated_last = min(self.last, total_items_number)
                    else:
                        self._calculated_last = total_items_number
                    cut_items_number = self._calculated_last - self._calculated_first + 1
                else:
                    players_instead_of_boards = True
                    cut_items_number = len(self.tournament.players_by_name_with_unpaired)
                    self._calculated_first = 1
                    self._calculated_last = cut_items_number
            case ScreenType.Players:
                players_instead_of_boards = False
                if self.tournament.current_round:
                    if self.players_show_unpaired:
                        total_items_number = len(self.tournament.players_by_name_with_unpaired)
                    else:
                        total_items_number = len(self.tournament.players_by_name_without_unpaired)
                else:
                    total_items_number = len(self.tournament.players_by_name_with_unpaired)
                if self.first:
                    if self.first > total_items_number:
                        self.error = f'Le tournoi ne comporte que [{total_items_number}] joueur·euses, famille ignorée.'
                        self.event.add_warning(self.error, family=self)
                        return False
                    self._calculated_first = self.first
                else:
                    self._calculated_first = 1
                if self.last:
                    self._calculated_last = min(self.last, total_items_number)
                else:
                    self._calculated_last = total_items_number
                cut_items_number = self._calculated_last - self._calculated_first + 1
            case _:
                raise ValueError(f'type={self.type}')
        if not cut_items_number:
            self.error = \
                f'Il n\'y a aucun élément à afficher pour le tournoi [{self.tournament.uniq_id}], famille ignorée.'
            self.event.add_warning(self.error, family=self)
            return False
        # OK now we know the number of items and the number of the first item to take
        # Let's go for the number of items by part and the number of parts
        if self.number:
            if players_instead_of_boards:
                self._calculated_number = self.number * 2
            else:
                self._calculated_number = self.number
        elif self.parts:
            self._calculated_number = ceil(cut_items_number / self.parts)
        else:
            self._calculated_number = cut_items_number
        divisor: int = self.columns * 2 if players_instead_of_boards else self.columns
        # ensure that the number of items is divisible by the number of columns
        if self._calculated_number % divisor != 0:
            self._calculated_number = min(
                (self._calculated_number // divisor + 1) * divisor,
                cut_items_number)
        # recalculate the number of parts
        # (because the number of items by part may increase to fit the number of columns)
        self._calculated_parts = ceil(cut_items_number / self._calculated_number)
        return True

    @cached_property
    def screens_by_uniq_id(self) -> dict[str, Screen]:
        screens_by_uniq_id: dict[str, Screen] = {}
        if self._calculate_screens():
            for family_index in range(1, self.calculated_parts + 1):
                screen: Screen = Screen(self.event, family=self, family_part=family_index)
                screens_by_uniq_id[screen.uniq_id] = screen
        return screens_by_uniq_id

    @cached_property
    def calculated_first(self) -> int | None:
        self._calculate_screens()
        return self._calculated_first

    @cached_property
    def calculated_last(self) -> int | None:
        self._calculate_screens()
        return self._calculated_last

    @cached_property
    def calculated_number(self) -> int | None:
        self._calculate_screens()
        return self._calculated_number

    @cached_property
    def calculated_parts(self) -> int | None:
        self._calculate_screens()
        return self._calculated_parts

    @property
    def numbers_str(self):
        name: str = 'échiquiers' if self.type in [ScreenType.Boards, ScreenType.Input, ] else 'joueur·euses'
        match (self.first, self.last, self.number, self.parts):
            case (None, None, None, None):
                return 'tous les échiquiers' \
                    if self.type in [ScreenType.Boards, ScreenType.Input, ] \
                    else 'tou·tes les joueur·euses'
            case (first, None, None, None) if first is not None:
                return f'{name} à partir du n°{first}'
            case (None, last, None, None) if last is not None:
                return f"{name} jusqu'à n°{last}"
            case (first, last, None, None) if first is not None and last is not None:
                return f'{name} du n°{first} au n°{last}'
            case (None, None, number, None) if number is not None:
                return f'écrans de {number} {name}'
            case (first, None, number, None) if first is not None and number is not None:
                return f'écrans de {number} {name} à partir du n°{first}'
            case (None, last, number, None) if last is not None and number is not None:
                return f'écrans de {number} {name} jusqu\'au n°{last}'
            case (first, last, number, None) if first is not None and last is not None and number is not None:
                return f'écrans de {number} {name} du n°{first} au n°{last}'
            case (None, None, None, parts) if parts is not None:
                return f'{name} sur {parts} écrans'
            case (first, None, None, parts) if first is not None and parts is not None:
                return f'{name} à partir de n°{first}, sur {parts} écrans'
            case (None, last, None, parts) if last is not None and parts is not None:
                return f'{name} jusqu\'au n°{last}, sur {parts} écrans'
            case (first, last, None, parts) if first is not None and last is not None and parts is not None:
                return f'{name} du n°{first} au n°{last}, sur {parts} écrans'
            case _:
                raise ValueError(
                    f'first={self.first}, last={self.last}, parts={self.parts}, number={self.number}')

    def __str__(self):
        return f'Tournoi {self.tournament.uniq_id} ({self.numbers_str})'
