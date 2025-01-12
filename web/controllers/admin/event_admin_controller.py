import logging
import time
from datetime import datetime
from logging import Logger
from typing import Annotated, Any

import requests
import validators
from litestar import get, patch, delete, post
from litestar.contrib.htmx.request import HTMXRequest
from litestar.contrib.htmx.response import HTMXTemplate, ClientRedirect
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template, Redirect
from litestar.status_codes import HTTP_200_OK

from common.exception import PapiWebException
from common.logger import get_logger
from common.papi_web_config import PapiWebConfig
from data.event import Event
from data.loader import EventLoader
from database.sqlite import EventDatabase
from database.store import StoredEvent
from web.controllers.admin.index_admin_controller import AdminWebContext, AbstractIndexAdminController
from web.controllers.index_controller import WebContext, AbstractController
from web.messages import Message
from web.session import SessionHandler

logger: Logger = get_logger()


class EventAdminWebContext(AdminWebContext):
    def __init__(
            self, request: HTMXRequest,
            event_uniq_id: str | None,
            admin_event_tab: str | None,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ] | None,
    ):
        super().__init__(request, data=data, admin_tab=None)
        self.admin_event: Event | None = None
        self.admin_event_tab: str | None = admin_event_tab
        if self.error:
            return
        if event_uniq_id:
            try:
                self.admin_event = EventLoader.get(request=self.request).load_event(event_uniq_id)
            except PapiWebException as pwe:
                self._redirect_error(f'L\'évènement [{event_uniq_id}] est introuvable : {pwe}')
                return

    def check_admin_tab(self):
        pass

    @property
    def background_image(self) -> str:
        if self.admin_event:
            return self.admin_event.background_image
        else:
            return super().background_image

    @property
    def template_context(self) -> dict[str, Any]:
        return super().template_context | {
            'admin_event_tab': self.admin_event_tab,
            'admin_event': self.admin_event,
        }

    def get_tournament_options(self) -> dict[str, str]:
        options: dict[str, str] = {
        }
        for tournament in self.admin_event.tournaments_by_id.values():
            options[str(tournament.id)] = f'{tournament.name} ({tournament.filename})'
        return options


class AbstractEventAdminController(AbstractIndexAdminController):

    @classmethod
    def _get_admin_event_render_context(
            cls,
            web_context: EventAdminWebContext,
    ) -> dict[str, Any]:
        logging_levels: dict[int, dict[str, str]] = {
            logging.DEBUG: {
                'name': 'DEBUG',
                'class': 'bg-secondary-subtle text-secondary-emphasis',
                'icon_class': 'bi-search',
            },
            logging.INFO: {
                'name': 'INFO',
                'class': 'bg-info-subtle text-info-emphasis',
                'icon_class': 'bi-info-circle',
            },
            logging.WARNING: {
                'name': 'WARNING',
                'class': 'bg-warning-subtle text-warning-emphasis',
                'icon_class': 'bi-exclamation-triangle',
            },
            logging.ERROR: {
                'name': 'ERROR',
                'class': 'bg-danger-subtle text-danger-emphasis',
                'icon_class': 'bi-bug-fill',
            },
            logging.CRITICAL: {
                'name': 'CRITICAL',
                'class': 'bg-danger text-white',
                'icon_class': 'bi-sign-stop-fill',
            },
        }
        nav_tabs: dict[str, dict[str, str]] = {
            'config': {
                'title': web_context.admin_event.uniq_id,
                'template': 'admin_event_config.html',
                'icon_class': 'bi-gear-fill',
            },
            'tournaments': {
                'title': f'Tournois ({len(web_context.admin_event.tournaments_by_id) or "-"})',
                'template': 'admin_tournaments.html',
            },
            'screens': {
                'title': f'Écrans ({len(web_context.admin_event.basic_screens_by_id) or "-"})',
                'template': 'admin_screens.html',
            },
            'families': {
                'title': f'Familles ({len(web_context.admin_event.families_by_id) or  "-"})',
                'template': 'admin_families.html',
            },
            'rotators': {
                'title': f'Écrans rotatifs ({len(web_context.admin_event.rotators_by_id) or "-"})',
                'template': 'admin_rotators.html',
            },
            'timers': {
                'title': f'Chronomètres ({len(web_context.admin_event.timers_by_id) or "-"})',
                'template': 'admin_timers.html',
            },
            'chessevents': {
                'title': f'ChessEvent ({len(web_context.admin_event.chessevents_by_id) or "-"})',
                'template': 'admin_chessevents.html',
            },
            'messages': {
                'title': f'Messages ({len(web_context.admin_event.messages) or "-"})',
                'template': 'admin_messages.html',
            },
        }
        if not web_context.admin_event_tab:
            web_context.admin_event_tab = list(nav_tabs.keys())[0]
        if web_context.admin_event.criticals:
            nav_tabs['messages']['class'] = logging_levels[logging.CRITICAL]['class']
            nav_tabs['messages']['icon_class'] = logging_levels[logging.CRITICAL]['icon_class']
        elif web_context.admin_event.errors:
            nav_tabs['messages']['class'] = logging_levels[logging.ERROR]['class']
            nav_tabs['messages']['icon_class'] = logging_levels[logging.ERROR]['icon_class']
        elif web_context.admin_event.warnings:
            nav_tabs['messages']['class'] = logging_levels[logging.WARNING]['class']
            nav_tabs['messages']['icon_class'] = logging_levels[logging.WARNING]['icon_class']
        return web_context.template_context | {
            'messages': Message.messages(web_context.request),
            'logging_levels': logging_levels,
            'nav_tabs': nav_tabs,
            'admin_columns': SessionHandler.get_session_admin_columns(web_context.request),
            'show_family_screens_on_screen_list': SessionHandler.get_session_show_family_screens_on_screen_list(
                web_context.request),
            'show_details_on_screen_list': SessionHandler.get_session_show_details_on_screen_list(
                web_context.request),
            'show_details_on_family_list': SessionHandler.get_session_show_details_on_family_list(
                web_context.request),
            'show_details_on_rotator_list': SessionHandler.get_session_show_details_on_rotator_list(
                web_context.request),
            'screen_types_on_screen_list': SessionHandler.get_session_screen_types_on_screen_list(
                web_context.request),
            'min_logging_level': SessionHandler.get_session_min_logging_level(web_context.request),
        }

    @classmethod
    def _admin_event_render(
            cls,
            template_context: dict[str, Any],
    ) -> Template:
        return HTMXTemplate(
            template_name="admin_event.html",
            context=template_context)


class EventAdminController(AbstractEventAdminController):

    @staticmethod
    def _admin_validate_event_update_data(
            action: str,
            web_context: EventAdminWebContext,
            data: dict[str, str] | None = None,
    ) -> StoredEvent:
        if data is None:
            data = {}
        errors: dict[str, str] = {}
        uniq_id: str | None = WebContext.form_data_to_str(data, 'uniq_id')
        if action == 'delete':
            if not uniq_id:
                errors['uniq_id'] = 'Veuillez entrer l\'identifiant de l\'évènement.'
            elif uniq_id != web_context.admin_event.uniq_id:
                errors['uniq_id'] = f'L\'identifiant entré n\'est pas valide.'
        else:
            if not uniq_id:
                errors['uniq_id'] = 'Veuillez entrer l\'identifiant de l\'évènement.'
            elif uniq_id.find('/') != -1:
                errors['uniq_id'] = "le caractère « / » n\'est pas autorisé"
            else:
                event_uniq_ids: list[str] = EventLoader.get(request=web_context.request).event_uniq_ids
                match action:
                    case 'clone':
                        if uniq_id in event_uniq_ids:
                            errors['uniq_id'] = f'L\'évènement [{uniq_id}] existe déjà.'
                    case 'update':
                        if uniq_id != web_context.admin_event.uniq_id and uniq_id in event_uniq_ids:
                            errors['uniq_id'] = f'L\'évènement [{uniq_id}] existe déjà.'
                    case _:
                        raise ValueError(f'action=[{action}]')
        name: str | None = WebContext.form_data_to_str(data, 'name')
        start: float | None = None
        stop: float | None = None
        match action:
            case 'clone' | 'update':
                if not name:
                    errors['name'] = 'Veuillez entrer le nom de l\'évènement.'
                start_str: str | None = WebContext.form_data_to_str(data, 'start')
                if not start_str:
                    errors['start'] = 'Veuillez entrer la date de début de l\'évènement.'
                else:
                    start = time.mktime(datetime.strptime(start_str, '%Y-%m-%dT%H:%M').timetuple())
                stop_str: str | None = WebContext.form_data_to_str(data, 'stop')
                if not stop_str:
                    errors['stop'] = 'Veuillez entrer la date de fin de l\'évènement.'
                else:
                    stop = time.mktime(datetime.strptime(stop_str, '%Y-%m-%dT%H:%M').timetuple())
                if 'start' not in errors and 'stop' not in errors and start > stop:
                    errors['stop'] = 'Veuillez entrer la date postérieure à la date de début.'
            case 'delete':
                pass
            case _:
                raise ValueError(f'action=[{action}]')
        public: bool | None = WebContext.form_data_to_bool(data, 'public')
        path: str | None = None
        hide_background_image: bool | None = None
        background_image: str | None = None
        background_color: str | None = None
        update_password: str | None = None
        record_illegal_moves: int | None = None
        timer_colors: dict[int, str | None] = {i: None for i in range(1, 4)}
        timer_color_checkboxes: dict[int, bool | None] = {i: None for i in range(1, 4)}
        timer_delays: dict[int, int | None] = {i: None for i in range(1, 4)}
        match action:
            case 'update':
                path = WebContext.form_data_to_str(data, 'path')
                update_password = WebContext.form_data_to_str(data, 'update_password')
                field = 'background_image'
                hide_background_image = WebContext.form_data_to_bool(data, field + '_checkbox')
                if not hide_background_image:
                    if background_image := WebContext.form_data_to_str(data, field, ''):
                        if validators.url(background_image):
                            try:
                                response = requests.get(background_image)
                                if response.status_code != 200:
                                    errors[field] = \
                                        f'L\'URL [{background_image}] est en erreur (code [{response.status_code}]).'
                            except requests.ConnectionError as ce:
                                errors[field] = f'L\'URL [{background_image}] est en erreur ([{ce}]).'
                        else:
                            background_image = background_image.strip('/')
                            if background_image.find('..') != -1:
                                errors[field] = f'Le chemin [{background_image}] est incorrect.'
                                data[field] = ''
                            elif not (PapiWebConfig.custom_path / background_image).exists() \
                                    and not (PapiWebConfig.embedded_custom_path / background_image).exists():
                                errors[field] = f'Le fichier [{background_image}] est introuvable.'
                field: str = 'background_color'
                color_checkbox = WebContext.form_data_to_bool(data, field + '_checkbox')
                if not color_checkbox:
                    try:
                        background_color = WebContext.form_data_to_rgb(data, field)
                    except ValueError:
                        errors[field] = f'La couleur [{data[field]}] n\'est pas valide (attendu [#RRGGBB]).'
                field: str = 'record_illegal_moves'
                try:
                    record_illegal_moves = WebContext.form_data_to_int(data, field)
                    assert record_illegal_moves is None or 0 <= record_illegal_moves <= 3
                except (ValueError, AssertionError):
                    errors['record_illegal_moves'] = f'La valeur entrée [{data[field]}] n\'est pas valide.'
                for i in range(1, 4):
                    field: str = f'color_{i}'
                    timer_color_checkboxes[i] = WebContext.form_data_to_bool(data, field + '_checkbox')
                    if not timer_color_checkboxes[i]:
                        try:
                            timer_colors[i] = WebContext.form_data_to_rgb(data, field)
                        except ValueError:
                            errors[field] = f'La couleur [{data[field]}] n\'est pas valide (attendu [#HHHHHH]).'
                    field: str = f'delay_{i}'
                    try:
                        timer_delays[i] = WebContext.form_data_to_int(data, field, minimum=1)
                    except ValueError:
                        errors[field] = f'Le délai [{data[field]}] n\'est pas valide (attendu un entier positif).'
            case 'clone':
                path = web_context.admin_event.stored_event.path
                update_password = web_context.admin_event.stored_event.update_password
                hide_background_image = web_context.admin_event.stored_event.hide_background_image
                background_image = web_context.admin_event.stored_event.background_image
                background_color = web_context.admin_event.stored_event.background_color
                record_illegal_moves = web_context.admin_event.stored_event.record_illegal_moves
                timer_colors = web_context.admin_event.stored_event.timer_colors
                timer_delays = web_context.admin_event.stored_event.timer_delays
            case 'delete':
                pass
            case _:
                raise ValueError(f'action=[{action}]')
        return StoredEvent(
            uniq_id=uniq_id,
            name=name,
            start=start,
            stop=stop,
            public=public,
            path=path,
            hide_background_image=hide_background_image,
            background_image=background_image,
            background_color=background_color,
            update_password=update_password,
            record_illegal_moves=record_illegal_moves,
            timer_colors=timer_colors,
            timer_delays=timer_delays,
            errors=errors,
        )

    @staticmethod
    def background_images_jstree_data(background_image: str) -> list[dict[str, Any]]:
        dirs: list[str] = []
        files: list[str] = []
        for custom_path in [PapiWebConfig.embedded_custom_path, PapiWebConfig.custom_path, ]:
            for item in custom_path.rglob('*'):
                item_str = str(item).replace(str(custom_path), '').replace('\\', '/').lstrip('/')
                if item.is_dir():
                    if item_str not in dirs:
                        dirs.append(item_str)
                else:
                    if item_str not in files:
                        files.append(item_str)
        dir_nodes: list[dict[str, str]] = [{
            'id': d or '#',
            'parent': '/'.join(d.split('/')[:-1]) or '#',
            'text': f' {d.split("/")[-1]}',
            'state': {},
            'icon': 'bi-folder',
        } for d in dirs]
        file_nodes: list[dict[str, str]] = [{
            'id': f or '#',
            'parent': '/'.join(f.split('/')[:-1]) or '#',
            'text': f.split('/')[-1],
            'state': {
                'selected': background_image == f,
            },
            'icon': 'bi-card-image',
            'a_attr': {
                'onclick': f'$("#background-image").val("{f}"); '
                           f'$.ajax({{'
                           f'    url: "/background",'
                           f'    type: "GET",'
                           f'    data: {{ "image": "{f}", "color": $("#background-color").val() }},'
                           f'    success: function(data) {{'
                           f'        $("#background-image-test").css("background-image", data["url"]);'
                           f'    }},'
                           f'    error: function(jqXHR, exception) {{'
                           f'        console.log('
                           f'            "Changing background failed: status_code=" + jqXHR.status '
                           f'            + ", exception=" + exception + ", response=" + jqXHR.responseText'
                           f'        );'
                           f'    }},'
                           f'}});',
            }
        } for f in files]
        return file_nodes + dir_nodes

    @classmethod
    def _admin_event_config_render(
            cls,
            request: HTMXRequest,
            event_uniq_id: str,
            admin_event_tab: str | None = None,
            modal: str | None = None,
            action: str | None = None,
            data: dict[str, str] | None = None,
            errors: dict[str, str] | None = None,
    ) -> Template | ClientRedirect:
        web_context: EventAdminWebContext = EventAdminWebContext(
            request, event_uniq_id=event_uniq_id, admin_event_tab=admin_event_tab, data=data)
        if web_context.error:
            return web_context.error
        template_context: dict[str, Any] = cls._get_admin_event_render_context(web_context)
        match modal:
            case None:
                pass
            case 'event':
                if data is None:
                    data: dict[str, str] = {}
                    match action:
                        case 'update':
                            data['uniq_id'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.uniq_id)
                        case 'clone':
                            data['uniq_id'] = ''
                        case 'delete':
                            pass
                        case _:
                            raise ValueError(f'action=[{action}]')
                    match action:
                        case 'update' | 'clone':
                            data['uniq_id'] = '' if action == 'clone' else WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.uniq_id)
                            data['name'] = WebContext.value_to_form_data(web_context.admin_event.stored_event.name)
                            data['public'] = WebContext.value_to_form_data(web_context.admin_event.stored_event.public)
                            data['start'] = WebContext.value_to_datetime_form_data(
                                web_context.admin_event.stored_event.start)
                            data['stop'] = WebContext.value_to_datetime_form_data(
                                web_context.admin_event.stored_event.stop)
                            data['background_image_checkbox'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.hide_background_image)
                            data['background_image'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.background_image)
                            data['background_color'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.background_color)
                            data['background_color_checkbox'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.background_color is None)
                            data['path'] = WebContext.value_to_form_data(web_context.admin_event.stored_event.path)
                            data['update_password'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.update_password)
                            data['record_illegal_moves'] = WebContext.value_to_form_data(
                                web_context.admin_event.stored_event.record_illegal_moves)
                            for i in range(1, 4):
                                data[f'color_{i}'] = WebContext.value_to_form_data(
                                    web_context.admin_event.timer_colors[i])
                                data[f'color_{i}_checkbox'] = WebContext.value_to_form_data(
                                    web_context.admin_event.stored_event.timer_colors[i] is None)
                                data[f'delay_{i}'] = WebContext.value_to_form_data(
                                    web_context.admin_event.stored_event.timer_delays[i])
                        case 'delete':
                            pass
                        case _:
                            raise ValueError(f'action=[{action}]')
                    stored_event: StoredEvent = cls._admin_validate_event_update_data(action, web_context, data)
                    errors = stored_event.errors
                if errors is None:
                    errors = {}
                template_context |= {
                    'record_illegal_moves_options': cls._get_record_illegal_moves_options(
                        PapiWebConfig.default_record_illegal_moves_number),
                    'timer_color_texts': cls._get_timer_color_texts(PapiWebConfig.default_timer_delays),
                    'background_images_jstree_data': cls.background_images_jstree_data(
                        data['background_image']) if action == 'update' else {},
                    'modal': 'event',
                    'action': action,
                    'data': data,
                    'errors': errors,
                }
            case _:
                raise ValueError(f'modal=[{modal}]')
        return cls._admin_event_render(template_context)

    def _admin_event(
            self, request: HTMXRequest,
            event_uniq_id: str,
            admin_event_tab: str | None = None,
            admin_columns: int | None = None,
            show_family_screens_on_screen_list: bool | None = None,
            show_details_on_screen_list: bool | None = None,
            show_details_on_family_list: bool | None = None,
            show_details_on_rotator_list: bool | None = None,
            show_boards_screens_on_screen_list: bool | None = None,
            show_input_screens_on_screen_list: bool | None = None,
            show_players_screens_on_screen_list: bool | None = None,
            show_results_screens_on_screen_list: bool | None = None,
            show_image_screens_on_screen_list: bool | None = None,
            min_logging_level: int | None = None,
            modal: str | None = None,
            action: str | None = None,
            data: dict[str, str] | None = None,
            errors: dict[str, str] | None = None,
    ) -> Template | ClientRedirect:
        if admin_columns:
            SessionHandler.set_session_admin_columns(request, admin_columns)
        if show_family_screens_on_screen_list is not None:
            SessionHandler.set_session_show_family_screens_on_screen_list(request, show_family_screens_on_screen_list)
        if show_details_on_screen_list is not None:
            SessionHandler.set_session_show_details_on_screen_list(request, show_details_on_screen_list)
        if show_details_on_family_list is not None:
            SessionHandler.set_session_show_details_on_family_list(request, show_details_on_family_list)
        if show_details_on_rotator_list is not None:
            SessionHandler.set_session_show_details_on_rotator_list(request, show_details_on_rotator_list)
        screen_types: list[str] = SessionHandler.get_session_screen_types_on_screen_list(request)
        for screen_type, param in {
            'boards': show_boards_screens_on_screen_list,
            'input': show_input_screens_on_screen_list,
            'players': show_players_screens_on_screen_list,
            'results': show_results_screens_on_screen_list,
            'image': show_image_screens_on_screen_list,
        }.items():
            if param is not None:
                if param:
                    screen_types.append(screen_type)
                else:
                    screen_types.remove(screen_type)
                SessionHandler.set_session_screen_types_on_screen_list(request, screen_types)
                continue
        if min_logging_level is not None:
            try:
                SessionHandler.set_session_min_logging_level(request, min_logging_level)
            except ValueError:
                return AbstractController.redirect_error(
                    request, f'Le niveau de log [{min_logging_level}] est incorrect.')
        return self._admin_event_config_render(
            request, admin_event_tab=admin_event_tab, event_uniq_id=event_uniq_id, modal=modal, action=action,
            data=data, errors=errors)

    @get(
        path='/admin/event/{event_uniq_id:str}',
        name='admin-event',
        cache=1,
    )
    async def htmx_admin_event(
            self, request: HTMXRequest,
            event_uniq_id: str,
            admin_columns: int | None,
            show_family_screens_on_screen_list: bool | None,
            show_details_on_screen_list: bool | None,
            show_details_on_family_list: bool | None,
            show_details_on_rotator_list: bool | None,
            show_boards_screens_on_screen_list: bool | None,
            show_input_screens_on_screen_list: bool | None,
            show_players_screens_on_screen_list: bool | None,
            show_results_screens_on_screen_list: bool | None,
            show_image_screens_on_screen_list: bool | None,
            min_logging_level: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_event(
            request,
            event_uniq_id=event_uniq_id,
            admin_event_tab=None,
            admin_columns=admin_columns,
            show_family_screens_on_screen_list=show_family_screens_on_screen_list,
            show_details_on_screen_list=show_details_on_screen_list,
            show_details_on_family_list=show_details_on_family_list,
            show_details_on_rotator_list=show_details_on_rotator_list,
            show_boards_screens_on_screen_list=show_boards_screens_on_screen_list,
            show_input_screens_on_screen_list=show_input_screens_on_screen_list,
            show_players_screens_on_screen_list=show_players_screens_on_screen_list,
            show_results_screens_on_screen_list=show_results_screens_on_screen_list,
            show_image_screens_on_screen_list=show_image_screens_on_screen_list,
            min_logging_level=min_logging_level,
        )

    @get(
        path='/admin/event/{event_uniq_id:str}/{admin_event_tab:str}',
        name='admin-event-tab',
        cache=1,
    )
    async def htmx_admin_event_tab(
            self, request: HTMXRequest,
            event_uniq_id: str,
            admin_event_tab: str,
            admin_columns: int | None,
            show_family_screens_on_screen_list: bool | None,
            show_details_on_screen_list: bool | None,
            show_details_on_family_list: bool | None,
            show_details_on_rotator_list: bool | None,
            show_boards_screens_on_screen_list: bool | None,
            show_input_screens_on_screen_list: bool | None,
            show_players_screens_on_screen_list: bool | None,
            show_results_screens_on_screen_list: bool | None,
            show_image_screens_on_screen_list: bool | None,
            min_logging_level: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_event(
            request,
            event_uniq_id=event_uniq_id,
            admin_event_tab=admin_event_tab,
            admin_columns=admin_columns,
            show_family_screens_on_screen_list=show_family_screens_on_screen_list,
            show_details_on_screen_list=show_details_on_screen_list,
            show_details_on_family_list=show_details_on_family_list,
            show_details_on_rotator_list=show_details_on_rotator_list,
            show_boards_screens_on_screen_list=show_boards_screens_on_screen_list,
            show_input_screens_on_screen_list=show_input_screens_on_screen_list,
            show_players_screens_on_screen_list=show_players_screens_on_screen_list,
            show_results_screens_on_screen_list=show_results_screens_on_screen_list,
            show_image_screens_on_screen_list=show_image_screens_on_screen_list,
            min_logging_level=min_logging_level,
        )

    @get(
        path='/admin/event-modal/{action:str}/{event_uniq_id:str}',
        name='admin-event-modal',
        cache=1,
    )
    async def htmx_admin_event_modal(
            self, request: HTMXRequest,
            action: str,
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_event(request, modal='event', action=action, event_uniq_id=event_uniq_id, )

    def _admin_event_update(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            action: str,
            event_uniq_id: str | None,
    ) -> Template | ClientRedirect | Redirect:
        match action:
            case 'clone' | 'update' | 'delete':
                web_context: EventAdminWebContext = EventAdminWebContext(
                    request, event_uniq_id=event_uniq_id, admin_event_tab=None, data=data)
            case _:
                raise ValueError(f'action=[{action}]')
        if web_context.error:
            return web_context.error
        stored_event: StoredEvent = self._admin_validate_event_update_data(action, web_context, data)
        if stored_event.errors:
            return self._admin_event_config_render(
                request, event_uniq_id=event_uniq_id, modal='event', action=action, data=data,
                errors=stored_event.errors)
        uniq_id: str = stored_event.uniq_id
        event_loader = EventLoader.get(request=request)
        match action:
            case 'update':
                rename: bool = uniq_id != web_context.admin_event.uniq_id
                if rename:
                    event_loader.clear_cache(web_context.admin_event.uniq_id)
                    try:
                        EventDatabase(web_context.admin_event.uniq_id).rename(new_uniq_id=uniq_id)
                    except PermissionError as pe:
                        return AbstractController.redirect_error(
                            request, f'Le renommage de la base de données a échoué : {pe}')
                with EventDatabase(uniq_id, write=True) as event_database:
                    event_database.update_stored_event(stored_event)
                    event_database.commit()
                if rename:
                    Message.success(
                        request,
                        f'L\'évènement [{web_context.admin_event.uniq_id}] a été renommé ([{uniq_id}) et modifié.')
                else:
                    Message.success(request, f'L\'évènement [{uniq_id}] a été modifié.')
                event_loader.clear_cache(uniq_id)
                return self._admin_event_config_render(request, event_uniq_id=uniq_id)
            case 'clone':
                EventDatabase(web_context.admin_event.uniq_id).clone(new_uniq_id=uniq_id)
                with EventDatabase(uniq_id, write=True) as event_database:
                    event_database.update_stored_event(stored_event)
                    event_database.commit()
                Message.success(
                    request, f'L\'évènement [{web_context.admin_event.uniq_id}] a été dupliqué ([{uniq_id}]).')
                event_loader.clear_cache(uniq_id)
                return self._admin_event_config_render(request, event_uniq_id=uniq_id)
            case 'delete':
                try:
                    arch = EventDatabase(web_context.admin_event.uniq_id).delete()
                except PermissionError as pe:
                    return AbstractController.redirect_error(
                        request, f'La suppression de la base de données a échoué : {pe}')
                event_loader.clear_cache(web_context.admin_event.uniq_id)
                Message.success(
                    request, f'L\'évènement [{web_context.admin_event.uniq_id}] a été supprimé, la base '
                             f'de données a été archivée ({arch}).')
                return self._admin_render(request)
            case _:
                raise ValueError(f'action=[{action}]')

    @post(
        path='/admin/event-clone/{event_uniq_id:str}',
        name='admin-event-clone',
    )
    async def htmx_admin_event_clone(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_event_update(request, data=data, action='clone', event_uniq_id=event_uniq_id)

    @delete(
        path='/admin/event-delete/{event_uniq_id:str}',
        name='admin-event-delete',
        status_code=HTTP_200_OK,
    )
    async def htmx_admin_event_delete(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_event_update(request, data=data, action='delete', event_uniq_id=event_uniq_id)

    @patch(
        path='/admin/event-update/{event_uniq_id:str}',
        name='admin-event-update'
    )
    async def htmx_admin_event_update(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_event_update(request, data=data, action='update', event_uniq_id=event_uniq_id)
