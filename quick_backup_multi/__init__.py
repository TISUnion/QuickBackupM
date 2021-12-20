import functools
import json
import os
import re
import shutil
import time
from threading import Lock
from typing import Optional, Any, Callable

from mcdreforged.api.all import *

from quick_backup_multi.config import Configure
from quick_backup_multi.constant import BACKUP_DONE_EVENT, Prefix, RESTORE_DONE_EVENT, TRIGGER_BACKUP_EVENT, \
	CONFIG_FILE, TRIGGER_RESTORE_EVENT

config: Configure
server_inst: PluginServerInterface
HelpMessage: RTextBase
slot_selected = None  # type: Optional[int]
abort_restore = False
game_saved = False
plugin_unloaded = False
operation_lock = Lock()
operation_name = RText('?')


def tr(translation_key: str, *args) -> RTextMCDRTranslation:
	return ServerInterface.get_instance().rtr('quick_backup_multi.{}'.format(translation_key), *args)


def print_message(source: CommandSource, msg, tell=True, prefix='[QBM] '):
	msg = RTextList(prefix, msg)
	if source.is_player and not tell:
		source.get_server().say(msg)
	else:
		source.reply(msg)


def command_run(message: Any, text: Any, command: str) -> RTextBase:
	fancy_text = message.copy() if isinstance(message, RTextBase) else RText(message)
	return fancy_text.set_hover_text(text).set_click_event(RAction.run_command, command)


def copy_worlds(src: str, dst: str):
	for world in config.world_names:
		src_path = os.path.join(src, world)
		dst_path = os.path.join(dst, world)
		server_inst.logger.info('copying {} -> {}'.format(src_path, dst_path))
		if os.path.isdir(src_path):
			shutil.copytree(src_path, dst_path, ignore=lambda path, files: set(filter(config.is_file_ignored, files)))
		elif os.path.isfile(src_path):
			dst_dir = os.path.dirname(dst_path)
			if not os.path.isdir(dst_dir):
				os.makedirs(dst_dir)
			shutil.copy(src_path, dst_path)
		else:
			server_inst.logger.warning('{} does not exist while copying ({} -> {})'.format(src_path, src_path, dst_path))


def remove_worlds(folder: str):
	for world in config.world_names:
		target_path = os.path.join(folder, world)
		if os.path.isdir(target_path):
			shutil.rmtree(target_path)
		elif os.path.isfile(target_path):
			os.remove(target_path)
		else:
			ServerInterface.get_instance().logger.warning('[QBM] {} does not exist while removing'.format(target_path))


def get_slot_count():
	return len(config.slots)


def get_slot_folder(slot: int):
	return os.path.join(config.backup_path, f"slot{slot}")


def get_slot_info(slot: int):
	"""
	:param int slot: the index of the slot
	:return: the slot info
	:rtype: dict or None
	"""
	try:
		with open(os.path.join(get_slot_folder(slot), 'info.json'), encoding='utf8') as f:
			info = json.load(f)
	except:
		info = None
	return info


def format_time():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def format_protection_time(time_length: float) -> RTextBase:
	if time_length < 60:
		return tr('second', time_length)
	elif time_length < 60 * 60:
		return tr('minute', round(time_length / 60, 2))
	elif time_length < 24 * 60 * 60:
		return tr('hour', round(time_length / 60 / 60, 2))
	else:
		return tr('day', round(time_length / 60 / 60 / 24, 2))


def format_slot_info(info_dict: Optional[dict] = None, slot_number: Optional[int] = None) -> Optional[RTextBase]:
	if isinstance(info_dict, dict):
		info = info_dict
	elif slot_number is not None:
		info = get_slot_info(slot_number)
	else:
		return None

	if info is None:
		return None
	return tr('slot_info', info['time'], info.get('comment', tr('empty_comment')))


def touch_backup_folder():
	def mkdir(path: str):
		if os.path.isfile(path):
			os.remove(path)
		if not os.path.isdir(path):
			os.mkdir(path)

	mkdir(config.backup_path)
	for i in range(get_slot_count()):
		mkdir(get_slot_folder(i + 1))


def slot_check(source: CommandSource, slot: int):
	if not 1 <= slot <= get_slot_count():
		print_message(source, tr('unknown_slot', 1, get_slot_count()))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(source, tr('empty_slot', slot))
		return None
	return slot, slot_info


def single_op(name: RTextBase):
	def wrapper(func: Callable):
		@functools.wraps(func)
		def wrap(source: CommandSource, *args, **kwargs):
			acq = operation_lock.acquire(blocking=False)
			if acq:
				try:
					func(source, *args, **kwargs)
				finally:
					operation_lock.release()
			else:
				print_message(source, tr('lock.warning', name))
		return wrap
	return wrapper


@new_thread('QBM - delete')
@single_op(tr('operations.delete'))
def delete_backup(source: CommandSource, slot: int):
	if slot_check(source, slot) is None:
		return
	try:
		shutil.rmtree(get_slot_folder(slot))
	except Exception as e:
		print_message(source, tr('delete_backup.fail', slot, e), tell=False)
	else:
		print_message(source, tr('delete_backup.success', slot), tell=False)


def clean_up_slot_1():
	"""
	try to cleanup slot 1 for backup
	:rtype: bool
	"""
	slots = []
	empty_slot_idx = None
	target_slot_idx = None
	max_available_idx = None
	for i in range(get_slot_count()):
		slot_idx = i + 1
		slot = get_slot_info(slot_idx)
		slots.append(slot)
		if slot is None:
			if empty_slot_idx is None:
				empty_slot_idx = slot_idx
		else:
			time_stamp = slot.get('time_stamp', None)
			if time_stamp is not None:
				slot_config_data = config.slots[slot_idx - 1]
				if time.time() - time_stamp > slot_config_data.delete_protection:
					max_available_idx = slot_idx
			else:
				# old format, treat it as available
				max_available_idx = slot_idx

	if empty_slot_idx is not None:
		target_slot_idx = empty_slot_idx
	else:
		target_slot_idx = max_available_idx

	if target_slot_idx is not None:
		folder = get_slot_folder(target_slot_idx)
		if os.path.isdir(folder):
			shutil.rmtree(folder)
		for i in reversed(range(1, target_slot_idx)):  # n-1, n-2, ..., 1
			os.rename(get_slot_folder(i), get_slot_folder(i + 1))
		os.mkdir(get_slot_folder(1))
		return True
	else:
		return False


@new_thread('QBM - create')
def create_backup(source: CommandSource, comment: Optional[str]):
	_create_backup(source, comment)


@single_op(tr('operations.create'))
def _create_backup(source: CommandSource, comment: Optional[str]):
	try:
		print_message(source, tr('create_backup.start'), tell=False)
		start_time = time.time()
		touch_backup_folder()

		# start backup
		global game_saved, plugin_unloaded
		game_saved = False
		if config.turn_off_auto_save:
			source.get_server().execute('save-off')
		source.get_server().execute('save-all flush')
		while True:
			time.sleep(0.01)
			if game_saved:
				break
			if plugin_unloaded:
				print_message(source, tr('create_backup.abort.plugin_unload'), tell=False)
				return

		if not clean_up_slot_1():
			print_message(source, tr('create_backup.abort.no_slot'), tell=False)
			return

		slot_path = get_slot_folder(1)

		# copy worlds to backup slot
		copy_worlds(config.server_path, slot_path)
		# create info.json
		slot_info = {
			'time': format_time(),
			'time_stamp': time.time()
		}
		if comment is not None:
			slot_info['comment'] = comment
		with open(os.path.join(slot_path, 'info.json'), 'w', encoding='utf8') as f:
			json.dump(slot_info, f, indent=4, ensure_ascii=False)

		# done
		end_time = time.time()
		print_message(source, tr('create_backup.success', round(end_time - start_time, 1)), tell=False)
		print_message(source, format_slot_info(info_dict=slot_info), tell=False)
	except Exception as e:
		source.get_server().logger.exception('[QBM] Error creating backup')
		print_message(source, tr('create_backup.fail', e), tell=False)
	else:
		source.get_server().dispatch_event(BACKUP_DONE_EVENT, (source, slot_info))
	finally:
		if config.turn_off_auto_save:
			source.get_server().execute('save-on')


def restore_backup(source: CommandSource, slot: int):
	ret = slot_check(source, slot)
	if ret is None:
		return
	else:
		slot, slot_info = ret
	global slot_selected, abort_restore
	slot_selected = slot
	abort_restore = False
	print_message(source, tr('restore_backup.echo_action', slot, format_slot_info(info_dict=slot_info)), tell=False)
	print_message(
		source,
		command_run(tr('restore_backup.confirm_hint', Prefix), tr('restore_backup.confirm_hover'), '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run(tr('restore_backup.abort_hint', Prefix), tr('restore_backup.abort_hover'), '{0} abort'.format(Prefix))
		, tell=False
	)


@new_thread('QBM - restore')
def confirm_restore(source: CommandSource):
	global slot_selected
	if slot_selected is None:
		print_message(source, tr('confirm_restore.nothing_to_confirm'), tell=False)
	else:
		slot = slot_selected
		slot_selected = None
		_do_restore_backup(source, slot)


@single_op(tr('operations.restore'))
def _do_restore_backup(source: CommandSource, slot: int):
	try:
		print_message(source, tr('do_restore.countdown.intro'), tell=False)
		slot_info = get_slot_info(slot)
		for countdown in range(1, 10):
			print_message(source, command_run(
				tr('do_restore.countdown.text', 10 - countdown, slot, format_slot_info(info_dict=slot_info)),
				tr('do_restore.countdown.hover'),
				'{} abort'.format(Prefix)
			), tell=False)
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					print_message(source, tr('do_restore.abort'), tell=False)
					return

		source.get_server().stop()
		server_inst.logger.info('Wait for server to stop')
		source.get_server().wait_for_start()

		server_inst.logger.info('Backup current world to avoid idiot')
		overwrite_backup_path = os.path.join(config.backup_path, config.overwrite_backup_folder)
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(config.server_path, overwrite_backup_path)
		with open(os.path.join(overwrite_backup_path, 'info.txt'), 'w') as f:
			f.write('Overwrite time: {}\n'.format(format_time()))
			f.write('Confirmed by: {}'.format(source))

		slot_folder = get_slot_folder(slot)
		server_inst.logger.info('Deleting world')
		remove_worlds(config.server_path)
		server_inst.logger.info('Restore backup ' + slot_folder)
		copy_worlds(slot_folder, config.server_path)

		source.get_server().start()
	except:
		server_inst.logger.exception('Fail to restore backup to slot {}, triggered by {}'.format(slot, source))
	else:
		source.get_server().dispatch_event(RESTORE_DONE_EVENT, (source, slot, slot_info))  # async dispatch


def trigger_abort(source: CommandSource):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	print_message(source, tr('trigger_abort.abort'), tell=False)


@new_thread('QBM - list')
def list_backup(source: CommandSource, size_display: bool = None):
	if size_display is None:
		size_display = config.size_display

	def get_dir_size(dir_: str):
		size = 0
		for root, dirs, files in os.walk(dir_):
			size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
		return size

	def format_dir_size(size: int):
		if size < 2 ** 30:
			return f'{round(size / 2 ** 20, 2)} MB'
		else:
			return f'{round(size / 2 ** 30, 2)} GB'

	print_message(source, tr('list_backup.title'), prefix='')
	backup_size = 0
	for i in range(get_slot_count()):
		slot_idx = i + 1
		slot_info = format_slot_info(slot_number=slot_idx)
		if size_display:
			dir_size = get_dir_size(get_slot_folder(slot_idx))
		else:
			dir_size = 0
		backup_size += dir_size
		# noinspection PyTypeChecker
		text = RTextList(
			RText(tr('list_backup.slot.header', slot_idx)).h(tr('list_backup.slot.protection', format_protection_time(config.slots[slot_idx - 1].delete_protection))),
			' '
		)
		if slot_info is not None:
			text += RTextList(
				RText('[▷] ', color=RColor.green).h(tr('list_backup.slot.restore', slot_idx)).c(RAction.run_command, f'{Prefix} back {slot_idx}'),
				RText('[×] ', color=RColor.red).h(tr('list_backup.slot.delete', slot_idx)).c(RAction.suggest_command, f'{Prefix} del {slot_idx}')
			)
			if size_display:
				text += '§2{}§r '.format(format_dir_size(dir_size))
		text += slot_info
		print_message(source, text, prefix='')
	if size_display:
		print_message(source, tr('list_backup.total_space', format_dir_size(backup_size)), prefix='')


@new_thread('QBM - help')
def print_help_message(source: CommandSource):
	if source.is_player:
		source.reply('')
	with source.preferred_language_context():
		for line in HelpMessage.to_plain_text().splitlines():
			prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
			if prefix is not None:
				print_message(source, RText(line).set_click_event(RAction.suggest_command, prefix.group()), prefix='')
			else:
				print_message(source, line, prefix='')
		list_backup(source, size_display=False).join()
		print_message(
			source,
			tr('print_help.hotbar') +
			'\n' +
			RText(tr('print_help.click_to_create.text'))
				.h(tr('print_help.click_to_create.hover'))
				.c(RAction.suggest_command, tr('print_help.click_to_create.command', Prefix).to_plain_text()) +
			'\n' +
			RText(tr('print_help.click_to_restore.text'))
				.h(tr('print_help.click_to_restore.hover'))
				.c(RAction.suggest_command, tr('print_help.click_to_restore.command', Prefix).to_plain_text()),
			prefix=''
		)


def on_info(server: PluginServerInterface, info: Info):
	if not info.is_user:
		if info.content in config.saved_world_keywords:
			global game_saved
			game_saved = True


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
	print_message(source, command_run(
		tr('unknown_command.text', Prefix),
		tr('unknown_command.hover'),
		Prefix
	))


def register_command(server: PluginServerInterface):
	def get_literal_node(literal):
		lvl = config.minimum_permission_level.get(literal, 0)
		return Literal(literal).requires(lambda src: src.has_permission(lvl)).on_error(RequirementNotMet, lambda src: src.reply(tr('command.permission_denied')), handled=True)

	def get_slot_node():
		return Integer('slot').requires(lambda src, ctx: 1 <= ctx['slot'] <= get_slot_count()).on_error(RequirementNotMet, lambda src: src.reply(tr('command.wrong_slot')), handled=True)

	server.register_command(
		Literal(Prefix).
		runs(print_help_message).
		on_error(UnknownArgument, print_unknown_argument_message, handled=True).
		then(
			get_literal_node('make').
			runs(lambda src: create_backup(src, None)).
			then(GreedyText('comment').runs(lambda src, ctx: create_backup(src, ctx['comment'])))
		).
		then(
			get_literal_node('back').
			runs(lambda src: restore_backup(src, 1)).
			then(get_slot_node().runs(lambda src, ctx: restore_backup(src, ctx['slot'])))
		).
		then(
			get_literal_node('del').
			then(get_slot_node().runs(lambda src, ctx: delete_backup(src, ctx['slot'])))
		).
		then(get_literal_node('confirm').runs(confirm_restore)).
		then(get_literal_node('abort').runs(trigger_abort)).
		then(get_literal_node('list').runs(lambda src: list_backup(src))).
		then(get_literal_node('reload').runs(lambda src: load_config(src.get_server(), src)))
	)


def load_config(server: ServerInterface, source: CommandSource or None = None):
	global config
	config = server_inst.load_config_simple(CONFIG_FILE, target_class=Configure, in_data_folder=False, source_to_reply=source)
	last = 0
	for i in range(get_slot_count()):
		this = config.slots[i].delete_protection
		if this < 0:
			server.logger.warning('Slot {} has a negative delete protection time'.format(i + 1))
		elif not last <= this:
			server.logger.warning('Slot {} has a delete protection time smaller than the former one'.format(i + 1))
		last = this


def register_event_listeners(server: PluginServerInterface):
	server.register_event_listener(TRIGGER_BACKUP_EVENT, lambda svr, source, comment: _create_backup(source, comment))
	server.register_event_listener(TRIGGER_RESTORE_EVENT, lambda svr, source, slot: _do_restore_backup(source, slot))


def on_load(server: PluginServerInterface, old):
	global operation_lock, HelpMessage, server_inst
	server_inst = server
	if hasattr(old, 'operation_lock') and type(old.operation_lock) == type(operation_lock):
		operation_lock = old.operation_lock

	meta = server.get_self_metadata()
	HelpMessage = tr('help_message', Prefix, meta.name, meta.version)
	load_config(server)
	register_command(server)
	register_event_listeners(server)
	server.register_help_message(Prefix, command_run(tr('register.summory_help', get_slot_count()), tr('register.show_help'), Prefix))


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
