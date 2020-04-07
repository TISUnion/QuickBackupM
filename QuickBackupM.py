# coding: utf8
import copy
import json
import os
import shutil
import sys
import time

SlotCount = 5
Prefix = '!!qb'
BackupPath = './qb_multi'
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
}
OverwriteBackupFolder = 'overwrite'
ServerPath = './server'
HelpMessage = '''------MCD Multi Quick Backup------
一个支持多槽位的快速§a备份§r&§c回档§r插件
§a【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} make §e[<comment>]§r 创建一个储存至槽位1的§a备份§r，并将后移已有槽位。§e<comment>§r为可选存档注释
§7{0} back §6[<slot>]§r §c回档§r为槽位§6<slot>§r的存档。当§6<slot>§r参数被指定时将会§c回档§r为槽位§6<slot>§r
§7{0} confirm§r 在执行back后使用，再次确认是否进行§c回档§r
§7{0} abort§r 在任何时候键入此指令可中断§c回档§r
§7{0} list§r 显示各槽位的存档信息
当§6<slot>§r未被指定时默认选择槽位§61§r
§a【例子】§r
§7{0} make
§7{0} make §e世吞完成§r
§7{0} back
§7{0} back §62§r
'''.format(Prefix)
slot_selected = None
abort_restore = False
creating_backup = False
restoring_backup = False
'''
mcd_root/
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


def print_message(server, info, msg, tell=True):
	for line in msg.splitlines():
		if info.isPlayer:
			if tell:
				server.tell(info.player, line)
			else:
				server.say(line)
		else:
			print(line)


def copy_worlds(src, dst):
	for world in WorldNames:
		shutil.copytree('{}/{}'.format(src, world), '{}/{}'.format(dst, world))


def remove_worlds(folder):
	for world in WorldNames:
		shutil.rmtree('{}/{}'.format(folder, world))


def info_message(server, info, msg, tell=False):
	for line in msg.splitlines():
		print_message(server, info, '[QBM] ' + line, tell)


def get_slot_folder(slot):
	return '{}/slot{}'.format(BackupPath, slot)


def get_slot_info(slot):
	try:
		with open('{}/info.json'.format(get_slot_folder(slot))) as f:
			info = json.load(f, encoding='utf8')
		for key in info.keys():
			value = info[key]
			if sys.version_info.major == 2 and type(value) is unicode:
				info[key] = value.encode('utf8')
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


def create_backup(server, info, comment):
	global creating_backup
	if creating_backup:
		info_message(server, info, '正在§a备份§r中，请不要重复输入')
		return
	creating_backup = True
	try:
		info_message(server, info, '§a备份§r中...请稍等')
		start_time = time.time()
		touch_backup_folder()

		# remove the last backup
		shutil.rmtree(get_slot_folder(SlotCount))

		# move slot i-1 to slot i
		for i in range(SlotCount, 1, -1):
			os.rename(get_slot_folder(i - 1), get_slot_folder(i))

		# start backup
		global game_saved
		game_saved = False
		server.execute('save-all')
		for i in range(1000):
			time.sleep(0.01)
			if game_saved:
				break
		slot_path = get_slot_folder(1)
		try:
			copy_worlds(ServerPath, slot_path)
		except Exception as e:
			info_message(server, info, '§a备份§r失败，错误代码{}'.format(e))
		else:
			slot_info = {'time': format_time()}
			if comment is not None:
				slot_info['comment'] = comment
			with open('{}/info.json'.format(slot_path), 'w') as f:
				if sys.version_info.major == 2:
					json.dump(slot_info, f, indent=4, encoding='utf8')
				else:
					json.dump(slot_info, f, indent=4)
			end_time = time.time()
			info_message(server, info, '§a备份§r完成，耗时' + str(end_time - start_time)[:3] + '秒')
			info_message(server, info, format_slot_info(info_dict=slot_info))
	finally:
		creating_backup = False


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
		info_message(server, info, '槽位输入错误，应输入一个位于[{}, {}]的数字'.format(1, SlotCount))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		info_message(server, info, '槽位输入错误，此槽位为空')
		return None
	return slot, slot_info


def restore_backup(server, info, slot):
	ret = slot_check(server, info, slot)
	if ret is None:
		return
	else:
		slot, slot_info = ret
	global slot_selected, abort_restore
	slot_selected = slot
	abort_restore = False
	info_message(server, info, '准备将存档恢复至槽位§6{}§r， {}'.format(slot, format_slot_info(info_dict=slot_info)))
	info_message(server, info, '使用§7{0} confirm§r 确认§c回档§r，§7{0} abort§r 取消'.format(Prefix))


def confirm_restore(server, info):
	global restoring_backup
	if restoring_backup:
		info_message(server, info, '正在准备§c回档§r中，请不要重复输入')
		return
	restoring_backup = True
	try:
		global slot_selected
		if slot_selected is None:
			info_message(server, info, '没有什么需要确认的')
			return
		slot = slot_selected
		slot_selected = None

		info_message(server, info, '10秒后关闭服务器§c回档§r')
		for countdown in range(1, 10):
			info_message(server, info, '还有{}秒，将§c回档§r为槽位§6{}§r， {}'.format(10 - countdown, slot, format_slot_info(slot_number=slot)))
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					info_message(server, info, '§c回档§r被中断！')
					return

		kick_bots(server, info)
		server.stop()
		# MCDaemon
		if sys.version_info.major == 2:
			print('[QBM] Wait for up to 10s for server to stop')
			time.sleep(10)
		# MCDReforged
		else:
			print('[QBM] Wait for server to stop')
			while server.is_server_running():
				time.sleep(0.1)

		print('[QBM] Backup current world to avoid idiot')
		overwrite_backup_path = BackupPath + '/' + OverwriteBackupFolder
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(ServerPath, overwrite_backup_path)
		with open('{}/info.txt'.format(overwrite_backup_path), 'w') as f:
			f.write('Overwrite time: {}\nConfirm by: {}'.format(format_time(), info.player if info.isPlayer else '$Console$'))

		slot_folder = get_slot_folder(slot)
		print('[QBM] Restore backup ' + slot_folder)
		remove_worlds(ServerPath)
		time.sleep(1)
		copy_worlds(slot_folder, ServerPath)
		print('[QBM] Wait for another 5s before server starts')
		time.sleep(5)

		server.start()
	finally:
		restoring_backup = False


def kick_bots(server, info):
	try:
		import mcdbot
		import copy
		iinfo = copy.deepcopy(info)
		iinfo.content = '!!bot kickall'
		mcdbot.onServerInfo(server, iinfo)
	except:
		pass


def list_backup(server, info):
	for i in range(SlotCount):
		info_message(server, info, '[槽位§6{}§r] {}'.format(i + 1, format_slot_info(slot_number=i + 1)))


def trigger_abort(server, info):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	info_message(server, info, '终止操作！')


def onServerInfo(server, info):
	content = info.content
	if content == 'Saved the game' and not info.isPlayer:
		global game_saved
		game_saved = True
	if not info.isPlayer and content.endswith('<--[HERE]'):
		content = content.replace('<--[HERE]', '')

	command = content.split()
	if len(command) == 0 or command[0] != Prefix:
		return
	del command[0]

	if len(command) == 0:
		print_message(server, info, HelpMessage)
		return

	cmdLen = len(command)
	# MCDR permission check
	global MinimumPermissionLevel
	if hasattr(server, 'MCDR') and cmdLen >= 1 and command[0] in MinimumPermissionLevel.keys():
		if server.get_permission_level(info) < MinimumPermissionLevel[command[0]]:
			print_message(server, info, '§c权限不足！§r')
			return
	# make [<comment>]
	if cmdLen in [1, 2] and command[0] == 'make':
		create_backup(server, info, command[1] if cmdLen == 2 else None)
	# back [<slot>]
	elif cmdLen in [1, 2] and command[0] == 'back':
		restore_backup(server, info, command[1] if cmdLen == 2 else '1')
	# confirm
	elif cmdLen == 1 and command[0] == 'confirm':
		confirm_restore(server, info)
	# abort
	elif cmdLen == 1 and command[0] == 'abort':
		trigger_abort(server, info)
	# list
	elif cmdLen == 1 and command[0] == 'list':
		list_backup(server, info)
	else:
		print_message(server, info, '参数错误！请输入§7' + Prefix + '§r以获取插件帮助')


def on_info(server, info):
	info2 = copy.deepcopy(info)
	info2.isPlayer = info2.is_player
	onServerInfo(server, info2)


def on_load(server, old):
	server.add_help_message(Prefix, '备份/回档，{}槽位'.format(SlotCount))


def on_unload(server):
	global abort_restore
	abort_restore = True
