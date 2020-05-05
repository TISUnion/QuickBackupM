# coding: utf8
import os
import re
import shutil
import time
from threading import Lock
from utils.rtext import *


'''================ 可修改常量开始 ================'''
SizeDisplay = True
SlotCount = 5
Prefix = '!!qb'
BackupPath = './qb_multi'
TurnOffAutoSave = True
IgnoreSessionLock = True
WorldNames = [
	'world',
]
# 0:guest 1:user 2:helper 3:admin
MinimumPermissionLevel = {
	'make': 1,
	'back': 2,
	'confirm': 1,
	'abort': 1,
	'share': 2,
	'list': 0,
	'del': 2,
}
OverwriteBackupFolder = 'overwrite'
ServerPath = './server'
'''================ 可修改常量结束 ================'''

HelpMessage = '''
------ MCDR Multi Quick Backup 20200505 ------
一个支持多槽位的快速§a备份§r&§c回档§r插件
§d【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} make §e[<cmt>]§r 创建一个储存至槽位§61§r的§a备份§r。§e<cmt>§r为可选注释
§7{0} back §6[<slot>]§r §c回档§r为槽位§6<slot>§r的存档
§7{0} del §6[<slot>]§r §c删除§r槽位§6<slot>§r的存档
§7{0} confirm§r 再次确认是否进行§c回档§r
§7{0} abort§r 在任何时候键入此指令可中断§c回档§r
§7{0} list§r 显示各槽位的存档信息
当§6<slot>§r未被指定时默认选择槽位§61§r
'''.strip().format(Prefix)
slot_selected = None
abort_restore = False
game_saved = False
plugin_unloaded = False
creating_backup = Lock()
restoring_backup = Lock()
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
		return [file for file in files if file == 'session.lock' and IgnoreSessionLock]
	for world in WorldNames:
		shutil.copytree('{}/{}'.format(src, world), '{}/{}'.format(dst, world), ignore=filter_ignore)


def remove_worlds(folder):
	for world in WorldNames:
		shutil.rmtree('{}/{}'.format(folder, world))


def get_slot_folder(slot):
	return '{}/slot{}'.format(BackupPath, slot)


def get_slot_info(slot):
	try:
		with open('{}/info.json'.format(get_slot_folder(slot))) as f:
			info = json.load(f, encoding='utf8')
		for key in info.keys():
			value = info[key]
	except:
		info = None
	return info


def format_time():
	return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


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

	mkdir(BackupPath)
	for i in range(SlotCount):
		mkdir(get_slot_folder(i + 1))


def slot_number_formater(slot):
	flag_fail = False
	if type(slot) is not int:
		try:
			slot = int(slot)
		except ValueError:
			flag_fail = True
	if flag_fail or not 1 <= slot <= SlotCount:
		return None
	return slot


def slot_check(server, info, slot):
	slot = slot_number_formater(slot)
	if slot is None:
		print_message(server, info, '槽位输入错误，应输入一个位于[{}, {}]的数字'.format(1, SlotCount))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(server, info, '槽位输入错误，槽位§6{}§r为空'.format(slot))
		return None
	return slot, slot_info


def delete_backup(server, info, slot):
	global creating_backup, restoring_backup
	if creating_backup.locked() or restoring_backup.locked():
		return
	if slot_check(server, info, slot) is None:
		return
	try:
		shutil.rmtree(get_slot_folder(slot))
	except Exception as e:
		print_message(server, info, RText('§4删除失败§r，详细错误信息请查看服务端后台').set_hover_text(e))
	else:
		print_message(server, info, '§a删除完成§r')


def create_backup(server, info, comment):
	global creating_backup
	acquired = creating_backup.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '正在§a备份§r中，请不要重复输入')
		return
	try:
		print_message(server, info, '§a备份§r中...请稍等')
		start_time = time.time()
		touch_backup_folder()

		# remove the last backup
		shutil.rmtree(get_slot_folder(SlotCount))

		# move slot i-1 to slot i
		for i in range(SlotCount, 1, -1):
			os.rename(get_slot_folder(i - 1), get_slot_folder(i))

		# start backup
		global game_saved, plugin_unloaded
		game_saved = False
		if TurnOffAutoSave:
			server.execute('save-off')
		server.execute('save-all')
		while True:
			time.sleep(0.01)
			if game_saved:
				break
			if plugin_unloaded:
				server.reply(info, '插件重载，§a备份§r中断！')
				return
		slot_path = get_slot_folder(1)

		copy_worlds(ServerPath, slot_path)
		slot_info = {'time': format_time()}
		if comment is not None:
			slot_info['comment'] = comment
		with open('{}/info.json'.format(slot_path), 'w') as f:
			json.dump(slot_info, f, indent=4)
		end_time = time.time()
		print_message(server, info, '§a备份§r完成，耗时§6{}§r秒'.format(round(end_time - start_time, 1)))
		print_message(server, info, format_slot_info(info_dict=slot_info))
	except Exception as e:
		print_message(server, info, '§a备份§r失败，错误代码{}'.format(e))
	finally:
		creating_backup.release()
		if TurnOffAutoSave:
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
	print_message(server, info, '准备将存档恢复至槽位§6{}§r， {}'.format(slot, format_slot_info(info_dict=slot_info)))
	print_message(
		server, info,
		command_run('使用§7{0} confirm§r 确认§c回档§r'.format(Prefix), '点击确认', '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run('§7{0} abort§r 取消'.format(Prefix), '点击取消', '{0} abort'.format(Prefix))
	)


def confirm_restore(server, info):
	global restoring_backup
	acquired = restoring_backup.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '正在准备§c回档§r中，请不要重复输入')
		return
	try:
		global slot_selected
		if slot_selected is None:
			print_message(server, info, '没有什么需要确认的')
			return
		slot = slot_selected
		slot_selected = None

		print_message(server, info, '10秒后关闭服务器§c回档§r')
		for countdown in range(1, 10):
			print_message(server, info, command_run(
				'还有{}秒，将§c回档§r为槽位§6{}§r，{}'.format(10 - countdown, slot, format_slot_info(slot_number=slot)),
				'点击终止回档！',
				'{} abort'.format(Prefix)
			))
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					print_message(server, info, '§c回档§r被中断！')
					return

		server.stop()
		server.logger.info('[QBM] Wait for server to stop')
		server.wait_for_start()

		server.logger.info('[QBM] Backup current world to avoid idiot')
		overwrite_backup_path = BackupPath + '/' + OverwriteBackupFolder
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(ServerPath, overwrite_backup_path)
		with open('{}/info.txt'.format(overwrite_backup_path), 'w') as f:
			f.write('Overwrite time: {}\n'.format(format_time()))
			f.write('Confirmed by: {}'.format(info.player if info.is_player else '$Console$'))

		slot_folder = get_slot_folder(slot)
		server.logger.info('[QBM] Deleting world')
		remove_worlds(ServerPath)
		server.logger.info('[QBM] Restore backup ' + slot_folder)
		copy_worlds(slot_folder, ServerPath)

		server.start()
	finally:
		restoring_backup.release()


def trigger_abort(server, info):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	print_message(server, info, '终止操作！')


def list_backup(server, info, size_display=SizeDisplay):
	def get_dir_size(dir):
		size = 0
		for root, dirs, files in os.walk(dir):
			size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
		if size < 2 ** 30:
			return f'{round(size / 2 ** 20, 2)} MB'
		else:
			return f'{round(size / 2 ** 30, 2)} GB'

	print_message(server, info, '§d【槽位信息】§r', prefix='')
	for i in range(SlotCount):
		j = i + 1
		print_message(
			server, info,
			RTextList(
				f'[槽位§6{j}§r] ',
				RText('[▷] ', color=RColor.green).h(f'点击回档至槽位§6{j}§r').c(RAction.run_command, f'{Prefix} back {j}'),
				RText('[×] ', color=RColor.red).h(f'点击删除槽位§6{j}§r').c(RAction.suggest_command, f'{Prefix} del {j}'),
				format_slot_info(slot_number=j)
			),
			prefix=''
		)
	if size_display:
		print_message(server, info, '备份总占用空间: §a{}§r'.format(get_dir_size(BackupPath)), prefix='')


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
	global MinimumPermissionLevel
	if cmd_len >= 2 and command[0] in MinimumPermissionLevel.keys():
		if server.get_permission_level(info) < MinimumPermissionLevel[command[0]]:
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

	# !!qb confirm
	elif cmd_len == 2 and command[1] == 'confirm':
		confirm_restore(server, info)

	# !!qb abort
	elif cmd_len == 2 and command[1] == 'abort':
		trigger_abort(server, info)

	# !!qb list
	elif cmd_len == 2 and command[1] == 'list':
		list_backup(server, info)

	# !!qb delete
	elif cmd_len in [2, 3] and command[1] == 'del':
		delete_backup(server, info, command[2] if cmd_len == 3 else '1')

	else:
		print_message(server, info, command_run(
			'参数错误！请输入§7{}§r以获取插件信息'.format(Prefix),
			'点击查看帮助',
			Prefix
		))


def on_load(server, old):
	server.add_help_message(Prefix, command_run('§a备份§r/§c回档§r，§6{}§r槽位'.format(SlotCount), '点击查看帮助信息', Prefix))
	global creating_backup, restoring_backup
	if hasattr(old, 'creating_backup') and type(old.creating_backup) == type(creating_backup):
		creating_backup = old.creating_backup
	if hasattr(old, 'restoring_backup') and type(old.restoring_backup) == type(restoring_backup):
		restoring_backup = old.restoring_backup


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
