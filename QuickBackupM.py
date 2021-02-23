import json
import os
import re
import shutil
import time
from threading import Lock
from typing import Optional

from mcdreforged.api.all import *

PLUGIN_ID = 'quick_backup_multi'
PLUGIN_METADATA = {
	'id': PLUGIN_ID,
	'version': '1.1.3',
	'name': RTextList(RText('Q', styles=RStyle.bold), 'uick ', RText('B', styles=RStyle.bold), 'ackup ', RText('M', styles=RStyle.bold), 'ulti'),
	'description': 'A backup and restore backup plugin, with multiple backup slots',
	'author': [
		'Fallen_Breath'
	],
	'link': 'https://github.com/TISUnion/QuickBackupM',
	'dependencies': {
		'mcdreforged': '>=1.0.0-alpha.7',
	}
}

BACKUP_DONE_EVENT 		= LiteralEvent('{}.backup_done'.format(PLUGIN_ID))  # -> source, slot_info
RESTORE_DONE_EVENT 		= LiteralEvent('{}.restore_done'.format(PLUGIN_ID))  # -> source, slot, slot_info
TRIGGER_BACKUP_EVENT 	= LiteralEvent('{}.trigger_backup'.format(PLUGIN_ID))  # <- source, comment
TRIGGER_RESTORE_EVENT 	= LiteralEvent('{}.trigger_restore'.format(PLUGIN_ID))  # <- source, slot

# 默认配置文件
config = {
	'size_display': True,
	'turn_off_auto_save': True,
	'ignore_session_lock': True,
	'backup_path': './qb_multi',
	'server_path': './server',
	'overwrite_backup_folder': 'overwrite',
	'world_names': [
		'world',
	],
	# 0:guest 1:user 2:helper 3:admin
	'minimum_permission_level': {
		'make': 1,
		'back': 2,
		'del': 2,
		'confirm': 1,
		'abort': 1,
		'reload': 2,
		'list': 0,
	},
	'slots': [
		{'delete_protection': 0},  # 无保护
		{'delete_protection': 0},  # 无保护
		{'delete_protection': 0},  # 无保护
		{'delete_protection': 3 * 60 * 60},  # 三小时
		{'delete_protection': 3 * 24 * 60 * 60},  # 三天
	]
}
default_config = config.copy()
Prefix = '!!qb'
CONFIG_FILE = os.path.join('config', 'QuickBackupM.json')
HelpMessage = '''
------ {1} v{2} ------
一个支持多槽位的快速§a备份§r&§c回档§r插件
§d【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} make §e[<cmt>]§r 创建一个储存至槽位§61§r的§a备份§r。§e<cmt>§r为可选注释
§7{0} back §6[<slot>]§r §c回档§r为槽位§6<slot>§r的存档
§7{0} del §6[<slot>]§r §c删除§r槽位§6<slot>§r的存档
§7{0} confirm§r 再次确认是否进行§c回档§r
§7{0} abort§r 在任何时候键入此指令可中断§c回档§r
§7{0} list§r 显示各槽位的存档信息
§7{0} reload§r 重新加载配置文件
当§6<slot>§r未被指定时默认选择槽位§61§r
'''.strip().format(Prefix, PLUGIN_METADATA['name'], PLUGIN_METADATA['version'])
slot_selected = None  # type: Optional[int]
abort_restore = False
game_saved = False
plugin_unloaded = False
creating_backup_lock = Lock()
restoring_backup_lock = Lock()
'''
mcdr_root/
	server/
		world/
	qb_multi/
		slot1/
			info.json
			world/
		slot2/
			...
		...
		overwrite/
			info.txt
			world/
'''


def print_message(source: CommandSource, msg, tell=True, prefix='[QBM] '):
	msg = prefix + msg
	if source.is_player and not tell:
		source.get_server().say(msg)
	else:
		source.reply(msg)


def command_run(message, text, command):
	return RText(message).set_hover_text(text).set_click_event(RAction.run_command, command)


def copy_worlds(src, dst):
	def filter_ignore(path, files):
		return [file for file in files if file == 'session.lock' and config['ignore_session_lock']]
	for world in config['world_names']:
		shutil.copytree(os.path.join(src, world),
			os.path.realpath(os.path.join(dst, world)), ignore=filter_ignore)


def remove_worlds(folder):
	for world in config['world_names']:
		shutil.rmtree(os.path.realpath(os.path.join(folder, world)))


def get_slot_count():
	return len(config['slots'])


def get_slot_folder(slot):
	return os.path.join(config['backup_path'], f"slot{slot}")


def get_slot_info(slot):
	"""
	:param int slot: the index of the slot
	:return: the slot info
	:rtype: dict or None
	"""
	try:
		with open(os.path.join(get_slot_folder(slot), 'info.json')) as f:
			info = json.load(f)
		for key in info.keys():
			value = info[key]
	except:
		info = None
	return info


def format_time():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


def format_protection_time(time_length):
	"""
	:rtype: str
	"""
	if time_length < 60:
		return '{}秒'.format(time_length)
	elif time_length < 60 * 60:
		return '{}分钟'.format(round(time_length / 60, 2))
	elif time_length < 24 * 60 * 60:
		return '{}小时'.format(round(time_length / 60 / 60, 2))
	else:
		return '{}天'.format(round(time_length / 60 / 60 / 24, 2))


def format_slot_info(info_dict=None, slot_number=None):
	if type(info_dict) is dict:
		info = info_dict
	elif type(slot_number) is not None:
		info = get_slot_info(slot_number)
	else:
		return None

	if info is None:
		return None
	msg = '日期: {}; 注释: {}'.format(info['time'], info.get('comment', '§7空§r'))
	return msg


def touch_backup_folder():
	def mkdir(path):
		if not os.path.exists(path):
			os.mkdir(path)

	mkdir(config['backup_path'])
	for i in range(get_slot_count()):
		mkdir(get_slot_folder(i + 1))


def slot_number_formatter(slot):
	flag_fail = False
	if type(slot) is not int:
		try:
			slot = int(slot)
		except ValueError:
			flag_fail = True
	if flag_fail or not 1 <= slot <= get_slot_count():
		return None
	return slot


def slot_check(source, slot):
	slot = slot_number_formatter(slot)
	if slot is None:
		print_message(source, '槽位输入错误，应输入一个位于[{}, {}]的数字'.format(1, get_slot_count()))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(source, '槽位输入错误，槽位§6{}§r为空'.format(slot))
		return None
	return slot, slot_info


def delete_backup(source, slot):
	global creating_backup_lock, restoring_backup_lock
	if creating_backup_lock.locked() or restoring_backup_lock.locked():
		return
	if slot_check(source, slot) is None:
		return
	try:
		shutil.rmtree(get_slot_folder(slot))
	except Exception as e:
		print_message(source, '§4删除槽位§6{}§r失败§r，错误代码：{}'.format(slot, e), tell=False)
	else:
		print_message(source, '§a删除槽位§6{}§r完成§r'.format(slot), tell=False)


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
				slot_config_data = config['slots'][slot_idx - 1]  # type: dict
				if time.time() - time_stamp > slot_config_data['delete_protection']:
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
		return True
	else:
		return False


@new_thread('QBM')
def create_backup(source: CommandSource, comment: Optional[str]):
	_create_backup(source, comment)


def _create_backup(source: CommandSource, comment: Optional[str]):
	global restoring_backup_lock, creating_backup_lock
	if restoring_backup_lock.locked():
		print_message(source, '正在§c回档§r中，请不要尝试备份', tell=False)
		return
	acquired = creating_backup_lock.acquire(blocking=False)
	if not acquired:
		print_message(source, '正在§a备份§r中，请不要重复输入', tell=False)
		return
	try:
		print_message(source, '§a备份§r中...请稍等', tell=False)
		start_time = time.time()
		touch_backup_folder()

		# start backup
		global game_saved, plugin_unloaded
		game_saved = False
		if config['turn_off_auto_save']:
			source.get_server().execute('save-off')
		source.get_server().execute('save-all flush')
		while True:
			time.sleep(0.01)
			if game_saved:
				break
			if plugin_unloaded:
				print_message(source, '插件重载，§a备份§r中断！', tell=False)
				return

		if not clean_up_slot_1():
			print_message(source, '未找到可用槽位，§a备份§r中断！', tell=False)
			return

		slot_path = get_slot_folder(1)

		# copy worlds to backup slot
		copy_worlds(config['server_path'], slot_path)
		# create info.json
		slot_info = {
			'time': format_time(),
			'time_stamp': time.time()
		}
		if comment is not None:
			slot_info['comment'] = comment
		with open(os.path.join(slot_path, 'info.json'), 'w') as f:
			json.dump(slot_info, f, indent=4)

		# done
		end_time = time.time()
		print_message(source, '§a备份§r完成，耗时§6{}§r秒'.format(round(end_time - start_time, 1)), tell=False)
		print_message(source, format_slot_info(info_dict=slot_info), tell=False)
	except Exception as e:
		print_message(source, '§a备份§r失败，错误代码{}'.format(e), tell=False)
	else:
		source.get_server().dispatch_event(BACKUP_DONE_EVENT, (source, slot_info))
	finally:
		creating_backup_lock.release()
		if config['turn_off_auto_save']:
			source.get_server().execute('save-on')


@new_thread('QBM')
def restore_backup(source: CommandSource, slot: int):
	ret = slot_check(source, slot)
	if ret is None:
		return
	else:
		slot, slot_info = ret
	global slot_selected, abort_restore
	slot_selected = slot
	abort_restore = False
	print_message(source, '准备将存档恢复至槽位§6{}§r， {}'.format(slot, format_slot_info(info_dict=slot_info)), tell=False)
	print_message(
		source,
		command_run('使用§7{0} confirm§r 确认§c回档§r'.format(Prefix), '点击确认', '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run('§7{0} abort§r 取消'.format(Prefix), '点击取消', '{0} abort'.format(Prefix))
		, tell=False
	)


@new_thread('QBM')
def confirm_restore(source: CommandSource):
	global slot_selected
	if slot_selected is None:
		print_message(source, '没有什么需要确认的', tell=False)
	else:
		slot = slot_selected
		slot_selected = None
		_do_restore_backup(source, slot)


def _do_restore_backup(source: CommandSource, slot: int):
	global restoring_backup_lock, creating_backup_lock
	if creating_backup_lock.locked():
		print_message(source, '正在§a备份§r中，请不要尝试回档', tell=False)
		return
	acquired = restoring_backup_lock.acquire(blocking=False)
	if not acquired:
		print_message(source, '正在准备§c回档§r中，请不要重复输入', tell=False)
		return
	try:
		print_message(source, '10秒后关闭服务器§c回档§r', tell=False)
		slot_info = get_slot_info(slot)
		for countdown in range(1, 10):
			print_message(source, command_run(
				'还有{}秒，将§c回档§r为槽位§6{}§r，{}'.format(10 - countdown, slot, format_slot_info(info_dict=slot_info)),
				'点击终止回档！',
				'{} abort'.format(Prefix)
			), tell=False)
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					print_message(source, '§c回档§r被中断！', tell=False)
					return

		source.get_server().stop()
		source.get_server().logger.info('[QBM] Wait for server to stop')
		source.get_server().wait_for_start()

		source.get_server().logger.info('[QBM] Backup current world to avoid idiot')
		overwrite_backup_path = os.path.join(config['backup_path'], config['overwrite_backup_folder'])
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(config['server_path'], overwrite_backup_path)
		with open(os.path.join(overwrite_backup_path, 'info.txt'), 'w') as f:
			f.write('Overwrite time: {}\n'.format(format_time()))
			f.write('Confirmed by: {}'.format(source))

		slot_folder = get_slot_folder(slot)
		source.get_server().logger.info('[QBM] Deleting world')
		remove_worlds(config['server_path'])
		source.get_server().logger.info('[QBM] Restore backup ' + slot_folder)
		copy_worlds(slot_folder, config['server_path'])

		source.get_server().start()
	except:
		source.get_server().logger.exception('Fail to restore backup to slot {}, triggered by {}'.format(slot, source))
	else:
		source.get_server().dispatch_event(RESTORE_DONE_EVENT, (source, slot, slot_info))  # async dispatch
	finally:
		restoring_backup_lock.release()


def trigger_abort(source):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	print_message(source, '终止操作！', tell=False)


@new_thread('QBM')
def list_backup(source: CommandSource, size_display=config['size_display']):
	def get_dir_size(dir):
		size = 0
		for root, dirs, files in os.walk(dir):
			size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
		return size

	def format_dir_size(size):
		if size < 2 ** 30:
			return f'{round(size / 2 ** 20, 2)} MB'
		else:
			return f'{round(size / 2 ** 30, 2)} GB'

	print_message(source, '§d【槽位信息】§r', prefix='')
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
			RText('[槽位§6{}§r] '.format(slot_idx)).h('存档保护时长: ' + format_protection_time(config['slots'][slot_idx - 1]['delete_protection']))
		)
		if slot_info is not None:
			text += RTextList(
				RText('[▷] ', color=RColor.green).h(f'点击回档至槽位§6{slot_idx}§r').c(RAction.run_command, f'{Prefix} back {slot_idx}'),
				RText('[×] ', color=RColor.red).h(f'点击删除槽位§6{slot_idx}§r').c(RAction.suggest_command, f'{Prefix} del {slot_idx}')
			)
			if size_display:
				text += '§2{}§r '.format(format_dir_size(dir_size))
		text += slot_info
		print_message(source, text, prefix='')
	if size_display:
		print_message(source, '备份总占用空间: §a{}§r'.format(format_dir_size(backup_size)), prefix='')


@new_thread('QBM')
def print_help_message(source: CommandSource):
	if source.is_player:
		source.reply('')
	for line in HelpMessage.splitlines():
		prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
		if prefix is not None:
			print_message(source, RText(line).set_click_event(RAction.suggest_command, prefix.group()), prefix='')
		else:
			print_message(source, line, prefix='')
	list_backup(source, size_display=False).join()
	print_message(
		source,
		'§d【快捷操作】§r' + '\n' +
		RText('>>> §a点我创建一个备份§r <<<')
			.h('记得修改注释')
			.c(RAction.suggest_command, f'{Prefix} make 我是一个注释') + '\n' +
		RText('>>> §c点我回档至最近的备份§r <<<')
			.h('也就是回档至第一个槽位')
			.c(RAction.suggest_command, f'{Prefix} back'),
		prefix=''
	)


def on_info(server, info: Info):
	if not info.is_user:
		if info.content == 'Saved the game' or info.content == 'Saved the world':
			global game_saved
			game_saved = True


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
	print_message(source, command_run(
		'参数错误！请输入§7{}§r以获取插件信息'.format(Prefix),
		'点击查看帮助',
		Prefix
	))


def register_command(server: ServerInterface):
	def get_literal_node(literal):
		lvl = config['minimum_permission_level'].get(literal, 0)
		return Literal(literal).requires(lambda src: src.has_permission(lvl), lambda: '权限不足')

	def get_slot_node():
		return Integer('slot').requires(lambda src, ctx: 1 <= ctx['slot'] <= get_slot_count(), lambda: '错误的槽位序号')

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


def load_config(server, source: CommandSource or None = None):
	global config
	try:
		config = {}
		with open(CONFIG_FILE) as file:
			js = json.load(file)
		for key in default_config.keys():
			config[key] = js[key]
		server.logger.info('Config file loaded')
		if source is not None:
			print_message(source, '配置文件加载成功', tell=True)

		# delete_protection check
		last = 0
		for i in range(get_slot_count()):
			# noinspection PyTypeChecker
			this = config['slots'][i]['delete_protection']
			if this < 0:
				server.logger.warning('Slot {} has a negative delete protection time'.format(i + 1))
			elif not last <= this:
				server.logger.warning('Slot {} has a delete protection time smaller than the former one'.format(i + 1))
			last = this
	except:
		server.logger.info('Fail to read config file, using default value')
		if source is not None:
			print_message(source, '配置文件加载失败，使用默认配置', tell=True)
		config = default_config
		with open(CONFIG_FILE, 'w') as file:
			json.dump(config, file, indent=4)


def register_event_listeners(server: ServerInterface):
	server.register_event_listener(TRIGGER_BACKUP_EVENT, lambda svr, source, comment: _create_backup(source, comment))
	server.register_event_listener(TRIGGER_RESTORE_EVENT, lambda svr, source, slot: _do_restore_backup(source, slot))


def on_load(server: ServerInterface, old):
	global creating_backup_lock, restoring_backup_lock
	if hasattr(old, 'creating_backup_lock') and type(old.creating_backup_lock) == type(creating_backup_lock):
		creating_backup_lock = old.creating_backup_lock
	if hasattr(old, 'restoring_backup_lock') and type(old.restoring_backup_lock) == type(restoring_backup_lock):
		restoring_backup_lock = old.restoring_backup_lock

	load_config(server)
	register_command(server)
	register_event_listeners(server)
	server.register_help_message(Prefix, command_run('§a备份§r/§c回档§r，§6{}§r槽位'.format(get_slot_count()), '点击查看帮助信息', Prefix))


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
