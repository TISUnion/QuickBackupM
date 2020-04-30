# coding: utf8
import copy
import json
import os
import shutil
import sys
import time
from threading import Lock


'''================ Modifiable constant starts ================'''
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
'''================ Modifiable constant ends ================'''


HelpMessage = '''
------MCDR Multi Quick Backup------
A plugin that supports multi slots world §abackup§r and backup §crestore§r
§a[Format]§r
§7{0}§r Display help message
§7{0} make §e[<comment>]§r Make a §abackup§r to slot §61§r, and shift the slots behind。§e<comment>§r is an optional comment message
§7{0} back §6[<slot>]§r §cRestore§r the world to slot §61§r. When §6<slot>§r parameter is set it will §crestore§r to slot §6<slot>§r
§7{0} del §6[<slot>]§r §cDelete§r the world in slot §6<slot>§r
§7{0} confirm§r Use after execute back to confirm §crestore§r execution
§7{0} abort§r Abort backup §crestoring§r
§7{0} list§r Display slot information
When §6<slot>§r is not set the default value is §61§r
§a[Example]§r
§7{0} make
§7{0} make §eworld eater done§r
§7{0} back
§7{0} back §62§r
'''.strip().format(Prefix)
slot_selected = None
abort_restore = False
game_saved = False
plugin_unloaded = False
creating_backup = Lock()
restoring_backup = Lock()
'''
MCDR_root/
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
	def filter_ignore(path, files):
		return [file for file in files if file == 'session.lock' and IgnoreSessionLock]
	for world in WorldNames:
		shutil.copytree('{}/{}'.format(src, world), '{}/{}'.format(dst, world), ignore=filter_ignore)


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
	msg = 'Date: {}; Comment: {}'.format(info['time'], info.get('comment', '§7Empty§r'))
	return msg


def touch_backup_folder():
	def mkdir(path):
		if not os.path.exists(path):
			os.mkdir(path)

	mkdir(BackupPath)
	for i in range(SlotCount):
		mkdir(get_slot_folder(i + 1))


def delete_backup(server, info, slot):
	global creating_backup, restoring_backup
	if creating_backup.locked() or restoring_backup.locked():
		return
	try:
		shutil.rmtree(get_slot_folder(slot))
	except:
		info_message(server, info, "§4Delete fail, check console for more detail")
	else:
		info_message(server, info, "§aDelete success")


def create_backup(server, info, comment):
	global creating_backup
	acquired = creating_backup.acquire(blocking=False)
	if not acquired:
		info_message(server, info, '§aBacking up§r, dont spam')
		return
	try:
		info_message(server, info, '§aBacking up§r, please wait')
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
				server.reply(info, 'Plugin unloaded, §aback up§r aborted!')
				return
		slot_path = get_slot_folder(1)

		copy_worlds(ServerPath, slot_path)
		slot_info = {'time': format_time()}
		if comment is not None:
			slot_info['comment'] = comment
		with open('{}/info.json'.format(slot_path), 'w') as f:
			if sys.version_info.major == 2:
				json.dump(slot_info, f, indent=4, encoding='utf8')
			else:
				json.dump(slot_info, f, indent=4)
		end_time = time.time()
		info_message(server, info, '§aBack up§r successfully, time cost ' + str(end_time - start_time)[:3] + 's')
		info_message(server, info, format_slot_info(info_dict=slot_info))
	except Exception as e:
		info_message(server, info, '§aBack up§r unsuccessfully, error code {}'.format(e))
	finally:
		creating_backup.release()
		if TurnOffAutoSave:
			server.execute('save-on')


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
		info_message(server, info, 'Slot format wrong, it should be a number between [{}, {}]'.format(1, SlotCount))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		info_message(server, info, 'Slot is empty')
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
	info_message(server, info, 'Gonna restore the world to slot §6{}§r, {}'.format(slot, format_slot_info(info_dict=slot_info)))
	info_message(server, info, 'Use §7{0} confirm§r to confirm §crestore§r, §7{0} abort§r to abort'.format(Prefix))


def confirm_restore(server, info):
	global restoring_backup
	acquired = restoring_backup.acquire(blocking=False)
	if not acquired:
		info_message(server, info, '§cRestoring§r, dont spam')
		return
	try:
		global slot_selected
		if slot_selected is None:
			info_message(server, info, 'Nothing to confirm')
			return
		slot = slot_selected
		slot_selected = None

		info_message(server, info, '§cRestore§r after 10 second')
		for countdown in range(1, 10):
			info_message(server, info, '{} second later the world will be §crestored§r to slot §6{}§r, {}'.format(10 - countdown, slot, format_slot_info(slot_number=slot)))
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					info_message(server, info, '§cRestore§r aborted!')
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
			f.write('Overwrite time: {}\nConfirm by: {}'.format(format_time(),
																info.player if info.isPlayer else '$Console$'))

		slot_folder = get_slot_folder(slot)
		print('[QBM] Restoring backup ' + slot_folder)
		remove_worlds(ServerPath)
		time.sleep(0.5)
		copy_worlds(slot_folder, ServerPath)
		print('[QBM] Wait for another 1s before server starts')
		time.sleep(1)

		server.start()
	finally:
		restoring_backup.release()


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
		info_message(server, info, '[Slot §6{}§r] {}'.format(i + 1, format_slot_info(slot_number=i + 1)))


def trigger_abort(server, info):
	global abort_restore, slot_selected
	abort_restore = True
	slot_selected = None
	info_message(server, info, 'Operation terminated!')


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
			print_message(server, info, '§cPermission denied§r')
			return
	# make [<comment>]
	if cmdLen >= 1 and command[0] == 'make':
		comment = content.replace('{} make'.format(Prefix), '', 1).lstrip(' ') if cmdLen >= 1 else None
		create_backup(server, info, comment)
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
	# delete
	elif cmdLen in [1, 2] and command[0] == 'del':
		delete_backup(server, info, command[1] if cmdLen == 2 else '1')

	else:
		print_message(server, info, 'Unknown command, input §7' + Prefix + '§r for help')


def on_info(server, info):
	info2 = copy.deepcopy(info)
	info2.isPlayer = info2.is_player
	onServerInfo(server, info2)


def on_load(server, old):
	server.add_help_message(Prefix, 'back up / restore with {} slots'.format(SlotCount))


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
