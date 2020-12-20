# coding: utf8
import os
import re
import shutil
import time
from threading import Lock

from utils.rtext import *

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
	'share_path': '/home/shared',
	'share_address': '192.168.0.0',
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
------ MCDR Multi Quick Backup 20201220 ------
一个支持多槽位的快速§a备份§r&§c回档§r插件
§d【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} make §e[<cmt>]§r 创建一个储存至槽位§61§r的§a备份§r。§e<cmt>§r为可选注释
§7{0} back §6[<slot>]§r §c回档§r为槽位§6<slot>§r的存档
§7{0} del §6[<slot>]§r §c删除§r槽位§6<slot>§r的存档
§7{0} confirm§r 再次确认是否进行§c回档§r
§7{0} abort§r 在任何时候键入此指令可中断§c回档§r
§7{0} list§r 显示各槽位的存档信息
§7{0} share §6[<slot>]§r 分享存档至云盘
当§6<slot>§r未被指定时默认选择槽位§61§r
'''.strip().format(Prefix)
slot_selected = None
abort_restore = False
game_saved = False
plugin_unloaded = False
creating_backup_lock = Lock()
restoring_backup_lock = Lock()
sharing_backup_lock = Lock()
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


def print_message(server, info, msg, tell=True, prefix='[QBM] '):
	msg = prefix + msg
	if info.is_player and not tell:
		server.say(msg)
	else:
		server.reply(info, msg)


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
	for i in range(len(config['slots'])):
		mkdir(get_slot_folder(i + 1))


def slot_number_formatter(slot):
	flag_fail = False
	if type(slot) is not int:
		try:
			slot = int(slot)
		except ValueError:
			flag_fail = True
	if flag_fail or not 1 <= slot <= len(config['slots']):
		return None
	return slot


def slot_check(server, info, slot):
	slot = slot_number_formatter(slot)
	if slot is None:
		print_message(server, info, '槽位输入错误，应输入一个位于[{}, {}]的数字'.format(1, len(config['slots'])))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(server, info, '槽位输入错误，槽位§6{}§r为空'.format(slot))
		return None
	return slot, slot_info


def delete_backup(server, info, slot):
	global creating_backup_lock, restoring_backup_lock
	if creating_backup_lock.locked() or restoring_backup_lock.locked():
		return
	if slot_check(server, info, slot) is None:
		return
	try:
		shutil.rmtree(get_slot_folder(slot))
	except Exception as e:
		print_message(server, info, RText('§4删除槽位§6{}§r失败§r，错误代码：{}'.format(slot, e)).set_hover_text(e), tell=False)
	else:
		print_message(server, info, '§a删除槽位§6{}§r完成§r'.format(slot), tell=False)


def clean_up_slot_1():
	"""
	try to cleanup slot 1 for backup
	:rtype: bool
	"""
	slots = []
	empty_slot_idx = None
	target_slot_idx = None
	max_available_idx = None
	for i in range(len(config['slots'])):
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


def create_backup(server, info, comment):
	global restoring_backup_lock, creating_backup_lock
	if restoring_backup_lock.locked():
		print_message(server, info, '正在§c回档§r中，请不要尝试备份', tell=False)
		return
	acquired = creating_backup_lock.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '正在§a备份§r中，请不要重复输入', tell=False)
		return
	try:
		print_message(server, info, '§a备份§r中...请稍等', tell=False)
		start_time = time.time()
		touch_backup_folder()

		# start backup
		global game_saved, plugin_unloaded
		game_saved = False
		if config['turn_off_auto_save']:
			server.execute('save-off')
		server.execute('save-all flush')
		while True:
			time.sleep(0.01)
			if game_saved:
				break
			if plugin_unloaded:
				print_message(server, info, '插件重载，§a备份§r中断！', tell=False)
				return

		if not clean_up_slot_1():
			print_message(server, info, '未找到可用槽位，§a备份§r中断！', tell=False)
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
		print_message(server, info, '§a备份§r完成，耗时§6{}§r秒'.format(round(end_time - start_time, 1)), tell=False)
		print_message(server, info, format_slot_info(info_dict=slot_info), tell=False)
	except Exception as e:
		print_message(server, info, '§a备份§r失败，错误代码{}'.format(e), tell=False)
	finally:
		creating_backup_lock.release()
		if config['turn_off_auto_save']:
			server.execute('save-on')


def restore_backup(server, info, slot):
	ret = slot_check(server, info, slot)
	if ret is None:
		return
	else:
		slot, slot_info = ret
	global slot_selected, abort_restore
	slot_selected = slot
	abort_restore = False
	print_message(server, info, '准备将存档恢复至槽位§6{}§r， {}'.format(slot, format_slot_info(info_dict=slot_info)), tell=False)
	print_message(
		server, info,
		command_run('使用§7{0} confirm§r 确认§c回档§r'.format(Prefix), '点击确认', '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run('§7{0} abort§r 取消'.format(Prefix), '点击取消', '{0} abort'.format(Prefix))
		, tell=False
	)


def confirm_restore(server, info):
	global restoring_backup_lock, creating_backup_lock
	if creating_backup_lock.locked():
		print_message(server, info, '正在§a备份§r中，请不要尝试回档', tell=False)
		return
	acquired = restoring_backup_lock.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '正在准备§c回档§r中，请不要重复输入', tell=False)
		return
	try:
		global slot_selected
		if slot_selected is None:
			print_message(server, info, '没有什么需要确认的', tell=False)
			return
		slot = slot_selected
		slot_selected = None

		print_message(server, info, '10秒后关闭服务器§c回档§r', tell=False)
		for countdown in range(1, 10):
			print_message(server, info, command_run(
				'还有{}秒，将§c回档§r为槽位§6{}§r，{}'.format(10 - countdown, slot, format_slot_info(slot_number=slot)),
				'点击终止回档！',
				'{} abort'.format(Prefix)
			), tell=False)
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					print_message(server, info, '§c回档§r被中断！', tell=False)
					return

		server.stop()
		server.logger.info('[QBM] Wait for server to stop')
		server.wait_for_start()

		server.logger.info('[QBM] Backup current world to avoid idiot')
		overwrite_backup_path = os.path.join(config['backup_path'], config['overwrite_backup_folder'])
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(config['server_path'], overwrite_backup_path)
		with open(os.path.join(overwrite_backup_path, 'info.txt'), 'w') as f:
			f.write('Overwrite time: {}\n'.format(format_time()))
			f.write('Confirmed by: {}'.format(info.player if info.is_player else '$Console$'))

		slot_folder = get_slot_folder(slot)
		server.logger.info('[QBM] Deleting world')
		remove_worlds(config['server_path'])
		server.logger.info('[QBM] Restore backup ' + slot_folder)
		copy_worlds(slot_folder, config['server_path'])

		server.start()
	finally:
		restoring_backup_lock.release()


def trigger_abort(server, info):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	print_message(server, info, '终止操作！', tell=False)


def share_backup(server, info, slot):
	global restoring_backup_lock, creating_backup_lock, sharing_backup_lock
	if restoring_backup_lock.locked() or creating_backup_lock.locked():
		print_message(server, info, '正在§a备份§r/§c回档§r中，请不要重复输入')
		return
	acquired = sharing_backup_lock.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '正在分享存档至云盘中，请不要重复输入')
		return
	try:
		ret = slot_check(server, info, slot)
		if ret is None:
			return
		else:
			slot, slot_info = ret

		dir_name = slot_info['time'].replace(' ', '_')
		print_message(server, info, '传输中...请稍等')
		share_path = str(config['share_path'])
		if share_path == '':  # wtf u r doing
			print_message(server, info, '[ERROR] WRONG SHARE PATH WTF')
			server.logger.warning('WRONG SHARE PATH WTF')
			return
		else:
			os.system('ssh root@{} "rm -rf {}/*" > nul'.format(config['share_address'], share_path))
		for world in config['world_names']:
			os.system('scp -r {} root@{}:{} > nul'.format(
				os.path.join(get_slot_folder(slot), world),
				config['share_address'],
				os.path.join(share_path, dir_name)
			))
		print_message(server, info, '已经成功分享到内服云盘')
	finally:
		sharing_backup_lock.release()


def list_backup(server, info, size_display=config['size_display']):
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

	print_message(server, info, '§d【槽位信息】§r', prefix='')
	backup_size = 0
	for i in range(len(config['slots'])):
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
		print_message(server, info, text, prefix='')
	if size_display:
		print_message(server, info, '备份总占用空间: §a{}§r'.format(format_dir_size(backup_size)), prefix='')


def print_help_message(server, info):
	if info.is_player:
		server.reply(info, '')
	for line in HelpMessage.splitlines():
		prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
		if prefix is not None:
			print_message(server, info, RText(line).set_click_event(RAction.suggest_command, prefix.group()), prefix='')
		else:
			print_message(server, info, line, prefix='')
	list_backup(server, info, size_display=False)
	print_message(
		server, info,
		'§d【快捷操作】§r' + '\n' +
		RText('>>> §a点我创建一个备份§r <<<')
			.h('记得修改注释')
			.c(RAction.suggest_command, f'{Prefix} make 我是一个注释') + '\n' +
		RText('>>> §c点我回档至最近的备份§r <<<')
			.h('也就是回档至第一个槽位')
			.c(RAction.suggest_command, f'{Prefix} back'),
		prefix=''
	)


def on_info(server, info):
	if not info.is_user:
		if info.content == 'Saved the game':
			global game_saved
			game_saved = True
		return

	command = info.content.split()
	if len(command) == 0 or command[0] != Prefix:
		return

	cmd_len = len(command)

	# MCDR permission check
	if cmd_len >= 2 and command[1] in config['minimum_permission_level'].keys():
		if server.get_permission_level(info) < config['minimum_permission_level'][command[1]]:
			print_message(server, info, '§c权限不足！§r')
			return

	# !!qb
	if cmd_len == 1:
		print_help_message(server, info)

	# !!qb make [<comment>]
	elif cmd_len >= 2 and command[1] == 'make':
		comment = info.content.replace('{} make'.format(Prefix), '', 1).lstrip(' ')
		create_backup(server, info, comment if len(comment) > 0 else None)

	# !!qb back [<slot>]
	elif cmd_len in [2, 3] and command[1] == 'back':
		restore_backup(server, info, command[2] if cmd_len == 3 else '1')

	# !!qb delete
	elif cmd_len == 3 and command[1] == 'del':
		delete_backup(server, info, command[2])

	# !!qb confirm
	elif cmd_len == 2 and command[1] == 'confirm':
		confirm_restore(server, info)

	# !!qb abort
	elif cmd_len == 2 and command[1] == 'abort':
		trigger_abort(server, info)

	# !!qb list
	elif cmd_len == 2 and command[1] == 'list':
		list_backup(server, info)

	# !!qb reload
	elif cmd_len == 2 and command[1] == 'reload':
		load_config(server, info)

	# !!qb share [<slot>]
	elif cmd_len in [2, 3] and command[1] == 'share':
		share_backup(server, info, command[2] if cmd_len == 3 else '1')

	else:
		print_message(server, info, command_run(
			'参数错误！请输入§7{}§r以获取插件信息'.format(Prefix),
			'点击查看帮助',
			Prefix
		))


def load_config(server, info=None):
	global config
	try:
		config = {}
		with open(CONFIG_FILE) as file:
			js = json.load(file)
		for key in default_config.keys():
			config[key] = js[key]
		server.logger.info('Config file loaded')
		if info:
			print_message(server, info, '配置文件加载成功', tell=True)

		# delete_protection check
		last = 0
		for i in range(len(config['slots'])):
			# noinspection PyTypeChecker
			this = config['slots'][i]['delete_protection']
			if this < 0:
				server.logger.warning('Slot {} has a negative delete protection time'.format(i + 1))
			elif not last <= this:
				server.logger.warning('Slot {} has a delete protection time smaller than the former one'.format(i + 1))
			last = this
	except:
		server.logger.info('Fail to read config file, using default value')
		if info:
			print_message(server, info, '配置文件加载失败，使用默认配置', tell=True)
		config = default_config
		with open(CONFIG_FILE, 'w') as file:
			json.dump(config, file, indent=4)


def on_load(server, old):
	server.add_help_message(Prefix, command_run('§a备份§r/§c回档§r，§6{}§r槽位'.format(len(config['slots'])), '点击查看帮助信息', Prefix))
	global creating_backup_lock, restoring_backup_lock, sharing_backup_lock
	if hasattr(old, 'creating_backup_lock') and type(old.creating_backup_lock) == type(creating_backup_lock):
		creating_backup_lock = old.creating_backup_lock
	if hasattr(old, 'restoring_backup_lock') and type(old.restoring_backup_lock) == type(restoring_backup_lock):
		restoring_backup_lock = old.restoring_backup_lock
	if hasattr(old, 'sharing_backup_lock') and type(old.sharing_backup) == type(sharing_backup_lock):
		sharing_backup_lock = old.sharing_backup_lock

	load_config(server)


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
