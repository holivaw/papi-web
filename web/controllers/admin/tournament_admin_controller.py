import re
from logging import Logger
from typing import Annotated, Any

from litestar import post, get, delete, patch
from litestar.contrib.htmx.request import HTMXRequest
from litestar.contrib.htmx.response import ClientRedirect
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template
from litestar.status_codes import HTTP_200_OK

from common.logger import get_logger
from data.event import Event
from data.loader import EventLoader
from data.tournament import Tournament
from database.sqlite import EventDatabase
from database.store import StoredTournament
from web.controllers.admin.event_admin_controller import EventAdminWebContext, AbstractEventAdminController
from web.controllers.index_controller import WebContext
from web.messages import Message

logger: Logger = get_logger()


class TournamentAdminWebContext(EventAdminWebContext):
    def __init__(
            self, request: HTMXRequest,
            event_uniq_id: str,
            admin_event_tab: str | None,
            tournament_id: int | None,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ] | None,
    ):
        super().__init__(request, event_uniq_id=event_uniq_id, admin_event_tab=admin_event_tab, data=data)
        self.admin_tournament: Tournament | None = None
        if self.error:
            return
        if tournament_id:
            try:
                self.admin_tournament = self.admin_event.tournaments_by_id[tournament_id]
            except KeyError:
                self._redirect_error(f'Le tournoi [{tournament_id}] n\'existe pas')
                return

    @property
    def template_context(self) -> dict[str, Any]:
        return super().template_context | {
            'admin_tournament': self.admin_tournament,
        }


class TournamentAdminController(AbstractEventAdminController):

    @staticmethod
    def _admin_validate_tournament_update_data(
            action: str,
            web_context: TournamentAdminWebContext,
            data: dict[str, str] | None = None,
    ) -> StoredTournament:
        errors: dict[str, str] = {}
        if data is None:
            data = {}
        uniq_id: str = WebContext.form_data_to_str(data, 'uniq_id')
        if action == 'delete':
            if not uniq_id:
                errors['uniq_id'] = 'Veuillez entrer l\'identifiant du tournoi.'
            elif uniq_id != web_context.admin_tournament.uniq_id:
                errors['uniq_id'] = f'L\'identifiant entré n\'est pas valide.'
        else:
            if not uniq_id:
                errors['uniq_id'] = 'Veuillez entrer l\'identifiant du tournoi.'
            elif uniq_id.find('/') != -1:
                errors['uniq_id'] = "le caractère « / » n\'est pas autorisé"
            else:
                match action:
                    case 'create' | 'clone':
                        if uniq_id in web_context.admin_event.tournaments_by_uniq_id:
                            errors['uniq_id'] = f'Le tournoi [{uniq_id}] existe déjà.'
                    case 'update':
                        if uniq_id != web_context.admin_tournament.uniq_id \
                                and uniq_id in web_context.admin_event.tournaments_by_uniq_id:
                            errors['uniq_id'] = f'Le tournoi [{uniq_id}] existe déjà.'
                    case _:
                        raise ValueError(f'action=[{action}]')
        name: str | None = None
        path: str | None = None
        filename: str | None = None
        ffe_id: int | None = None
        ffe_password: str | None = None
        match action:
            case 'create' | 'update' | 'clone':
                name = WebContext.form_data_to_str(data, 'name')
                if not name:
                    errors['name'] = 'Veuillez entrer le nom du tournoi.'
                path = WebContext.form_data_to_str(data, 'path')
                filename = WebContext.form_data_to_str(data, 'filename')
                try:
                    ffe_id = WebContext.form_data_to_int(data, 'ffe_id')
                except ValueError:
                    errors['ffe_id'] = 'L\'identifiant FFE est un entier positif.'
                ffe_password = WebContext.form_data_to_str(data, 'ffe_password')
                if ffe_password and not re.match('^[A-Z]{10}$', ffe_password):
                    errors['ffe_password'] = \
                        'Le mot de passe du tournoi sur le site FFE doit être composé de 10 lettres majuscules.'
            case 'delete':
                pass
            case _:
                raise ValueError(f'action=[{action}]')
        time_control_initial_time: int | None = None
        time_control_increment: int | None = None
        time_control_handicap_penalty_value: int | None = None
        time_control_handicap_penalty_step: int | None = None
        time_control_handicap_min_time: int | None = None
        chessevent_id: int | None = None
        chessevent_tournament_name: str | None = None
        record_illegal_moves: int | None = None
        match action:
            case 'update':
                time_control_initial_time = WebContext.form_data_to_int(data, 'time_control_initial_time')
                time_control_increment = WebContext.form_data_to_int(data, 'time_control_increment')
                time_control_handicap_penalty_value = WebContext.form_data_to_int(
                    data, 'time_control_handicap_penalty_value')
                time_control_handicap_penalty_step = WebContext.form_data_to_int(
                    data, 'time_control_handicap_penalty_step')
                time_control_handicap_min_time = WebContext.form_data_to_int(
                    data, 'time_control_handicap_min_time')
                chessevent_id = WebContext.form_data_to_int(data, 'chessevent_id')
                chessevent_tournament_name = WebContext.form_data_to_str(data, 'chessevent_tournament_name')
                record_illegal_moves = WebContext.form_data_to_str(data, 'record_illegal_moves')
            case 'delete' | 'create' | 'clone':
                pass
            case _:
                raise ValueError(f'action=[{action}]')
        return StoredTournament(
            id=web_context.admin_tournament.id if action != 'create' else None,
            uniq_id=uniq_id,
            name=name,
            path=path,
            filename=filename,
            ffe_id=ffe_id,
            ffe_password=ffe_password,
            time_control_initial_time=time_control_initial_time,
            time_control_increment=time_control_increment,
            time_control_handicap_penalty_value=time_control_handicap_penalty_value,
            time_control_handicap_penalty_step=time_control_handicap_penalty_step,
            time_control_handicap_min_time=time_control_handicap_min_time,
            chessevent_id=chessevent_id,
            chessevent_tournament_name=chessevent_tournament_name,
            record_illegal_moves=record_illegal_moves,
            errors=errors,
        )

    @staticmethod
    def _get_chessevent_options(admin_event: Event) -> dict[str, str]:
        options: dict[str, str] = {
            '': 'Pas de connexion à ChessEvent',
        }
        for chessevent in admin_event.chessevents_by_id.values():
            options[str(chessevent.id)] = (f' {chessevent.uniq_id} ({chessevent.user_id}'
                                           f'/{chessevent.shadowed_password}/{chessevent.event_id})')
        return options

    @classmethod
    def _admin_event_tournaments_render(
            cls,
            request: HTMXRequest,
            event_uniq_id: str,
            modal: str | None = None,
            action: str | None = None,
            tournament_id: int | None = None,
            data: dict[str, str] | None = None,
            errors: dict[str, str] | None = None,
    ) -> Template | ClientRedirect:
        web_context: TournamentAdminWebContext = TournamentAdminWebContext(
            request, event_uniq_id=event_uniq_id, admin_event_tab='tournaments', tournament_id=tournament_id, data=data)
        if web_context.error:
            return web_context.error
        template_context: dict[str, Any] = cls._get_admin_event_render_context(web_context)
        match modal:
            case None:
                pass
            case 'tournament':
                if data is None:
                    data = {}
                    match action:
                        case 'update':
                            data['uniq_id'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.uniq_id)
                        case 'create' | 'clone':
                            data['uniq_id'] = ''
                        case 'delete':
                            pass
                        case _:
                            raise ValueError(f'action=[{action}]')
                    match action:
                        case 'update' | 'clone':
                            data['name'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.name)
                            data['path'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.path)
                            data['filename'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.filename)
                            data['ffe_id'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.ffe_id)
                            data['ffe_password'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.ffe_password)
                        case 'create':
                            data['name'] = ''
                            data['path'] = ''
                            data['filename'] = ''
                            data['ffe_id'] = ''
                            data['ffe_password'] = ''
                        case 'delete':
                            pass
                        case _:
                            raise ValueError(f'action=[{action}]')
                    match action:
                        case 'update':
                            data['time_control_initial_time'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.time_control_initial_time)
                            data['time_control_increment'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.time_control_increment)
                            data['time_control_handicap_penalty_value'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.time_control_handicap_penalty_value)
                            data['time_control_handicap_penalty_step'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.time_control_handicap_penalty_step)
                            data['time_control_handicap_min_time'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.time_control_handicap_min_time)
                            data['chessevent_id'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.chessevent_id)
                            data['chessevent_tournament_name'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.chessevent_tournament_name)
                            data['record_illegal_moves'] = WebContext.value_to_form_data(
                                web_context.admin_tournament.stored_tournament.record_illegal_moves)
                        case 'delete' | 'clone' | 'create':
                            pass
                        case _:
                            raise ValueError(f'action=[{action}]')
                    stored_tournament: StoredTournament = cls._admin_validate_tournament_update_data(
                        action, web_context, data)
                    errors = stored_tournament.errors
                if errors is None:
                    errors = {}
                template_context |= {
                    'chessevent_options': cls._get_chessevent_options(web_context.admin_event),
                    'record_illegal_moves_options': cls._get_record_illegal_moves_options(
                        web_context.admin_event.record_illegal_moves),
                    'modal': modal,
                    'action': action,
                    'data': data,
                    'errors': errors,
                }
            case _:
                raise ValueError(f'modal=[{modal}]')
        return cls._admin_event_render(template_context)

    @get(
        path='/admin/tournament-modal/create/{event_uniq_id:str}',
        name='admin-tournament-create-modal',
        cache=1,
    )
    async def htmx_admin_tournament_create_modal(
            self, request: HTMXRequest,
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_event_tournaments_render(
            request, event_uniq_id=event_uniq_id, modal='tournament', action='create', tournament_id=None)

    @get(
        path='/admin/tournament-modal/{action:str}/{event_uniq_id:str}/{tournament_id:int}',
        name='admin-tournament-modal',
        cache=1,
    )
    async def htmx_admin_tournament_modal(
            self, request: HTMXRequest,
            action: str,
            event_uniq_id: str,
            tournament_id: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_event_tournaments_render(
            request, event_uniq_id=event_uniq_id, modal='tournament', action=action, tournament_id=tournament_id)

    def _admin_tournament_update(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            action: str,
            event_uniq_id: str,
            tournament_id: int | None,
    ) -> Template | ClientRedirect:
        match action:
            case 'update' | 'delete' | 'clone' | 'create':
                web_context: TournamentAdminWebContext = TournamentAdminWebContext(
                    request, event_uniq_id=event_uniq_id, admin_event_tab='tournaments', tournament_id=tournament_id,
                    data=data)
            case _:
                raise ValueError(f'action=[{action}]')
        if web_context.error:
            return web_context.error
        stored_tournament: StoredTournament = self._admin_validate_tournament_update_data(
            action, web_context, data)
        if stored_tournament.errors:
            return self._admin_event_tournaments_render(
                request, event_uniq_id=event_uniq_id, modal='tournament', action=action, tournament_id=tournament_id,
                data=data, errors=stored_tournament.errors)
        event_loader: EventLoader = EventLoader.get(request=request)
        with (EventDatabase(web_context.admin_event.uniq_id, write=True) as event_database):
            match action:
                case 'create':
                    stored_tournament = event_database.add_stored_tournament(stored_tournament)
                    event_database.commit()
                    Message.success(request, f'Le tournoi [{stored_tournament.uniq_id}] a été créé.')
                    event_loader.clear_cache(event_uniq_id)
                    return self._admin_event_tournaments_render(
                        request, event_uniq_id=event_uniq_id, modal='tournament', action='update',
                        tournament_id=stored_tournament.id)
                case 'update':
                    stored_tournament = event_database.update_stored_tournament(stored_tournament)
                    event_database.commit()
                    Message.success(request, f'Le tournoi [{stored_tournament.uniq_id}] a été modifié.')
                    event_loader.clear_cache(event_uniq_id)
                    return self._admin_event_tournaments_render(request, event_uniq_id=event_uniq_id)
                case 'delete':
                    event_database.delete_stored_tournament(web_context.admin_tournament.id)
                    event_database.commit()
                    Message.success(request, f'Le tournoi [{web_context.admin_tournament.uniq_id}] a été supprimé.')
                    event_loader.clear_cache(event_uniq_id)
                    return self._admin_event_tournaments_render(request, event_uniq_id=event_uniq_id)
                case 'clone':
                    stored_tournament = event_database.clone_stored_tournament(
                        web_context.admin_tournament.id, stored_tournament.uniq_id, stored_tournament.name,
                        stored_tournament.path, stored_tournament.filename, stored_tournament.ffe_id,
                        stored_tournament.ffe_password, )
                    event_database.commit()
                    Message.success(
                        request, f'Le tournoi [{web_context.admin_tournament.uniq_id}] a été dupliqué '
                                 f'([{stored_tournament.uniq_id}]).')
                    event_loader.clear_cache(event_uniq_id)
                    return self._admin_event_tournaments_render(
                        request, event_uniq_id=event_uniq_id, modal='tournament', action='update',
                        tournament_id=stored_tournament.id)
                case _:
                    raise ValueError(f'action=[{action}]')

    @post(
        path='/admin/tournament-create/{event_uniq_id:str}',
        name='admin-tournament-create'
    )
    async def htmx_admin_tournament_create(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
    ) -> Template | ClientRedirect:
        return self._admin_tournament_update(
            request, event_uniq_id=event_uniq_id, action='create', tournament_id=None, data=data)

    @post(
        path='/admin/tournament-clone/{event_uniq_id:str}/{tournament_id:int}',
        name='admin-tournament-clone'
    )
    async def htmx_admin_tournament_clone(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
            tournament_id: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_tournament_update(
            request, event_uniq_id=event_uniq_id, action='clone', tournament_id=tournament_id, data=data)

    @patch(
        path='/admin/tournament-update/{event_uniq_id:str}/{tournament_id:int}',
        name='admin-tournament-update'
    )
    async def htmx_admin_tournament_update(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
            tournament_id: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_tournament_update(
            request, event_uniq_id=event_uniq_id, action='update', tournament_id=tournament_id, data=data)

    @delete(
        path='/admin/tournament-delete/{event_uniq_id:str}/{tournament_id:int}',
        name='admin-tournament-delete',
        status_code=HTTP_200_OK,
    )
    async def htmx_admin_tournament_delete(
            self, request: HTMXRequest,
            data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED), ],
            event_uniq_id: str,
            tournament_id: int | None,
    ) -> Template | ClientRedirect:
        return self._admin_tournament_update(
            request, event_uniq_id=event_uniq_id, action='delete', tournament_id=tournament_id, data=data)
