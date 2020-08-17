# coding: utf8
import os
import re
import shutil
import time
from threading import Lock
from utils.rtext import *


'''================ Modifiable constant starts ================'''
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
'''================ Modifiable constant ends ================'''

HelpMessage = '''
------ MCDR Multi Quick Backup 20200817 ------
A plugin that supports multi slots world §abackup§r and backup §crestore§r
§d[Format]§r
§7{0}§r Display help message
§7{0} make §e[<comment>]§r Make a §abackup§r to slot §61§r. §e<comment>§r is an optional comment message
§7{0} back §6[<slot>]§r §cRestore§r the world to slot §6<slot>§r
§7{0} del §6[<slot>]§r §cDelete§r the world in slot §6<slot>§r
§7{0} confirm§r Use after execute back to confirm §crestore§r execution
§7{0} abort§r Abort backup §crestoring§r
§7{0} list§r Display slot information
When §6<slot>§r is not set the default value is §61§r
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
		shutil.copytree(os.path.join(src, world),
                        os.path.realpath(os.path.join(dst, world)), ignore=filter_ignore)


def remove_worlds(folder):
	for world in WorldNames:
		shutil.rmtree(os.path.realpath(os.path.join(folder, world)))


def get_slot_folder(slot):
	return os.path.join(BackupPath, f"slot{slot}")


def get_slot_info(slot):
	try:
		with open(os.path.join(get_slot_folder(slot), 'info.json')) as f:
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
	msg = 'Date: {}; Comment: {}'.format(info['time'], info.get('comment', '§7Empty§r'))
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
		print_message(server, info, 'Slot format wrong, it should be a number between [{}, {}]'.format(1, SlotCount))
		return None

	slot_info = get_slot_info(slot)
	if slot_info is None:
		print_message(server, info, 'Slot §6{}§r is empty'.format(slot))
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
		print_message(server, info, '§4Slot §6{}§r delete fail, error code {}§r'.format(slot, e), tell=False)
	else:
		print_message(server, info, '§aSlot §6{}§r delete success§r'.format(slot), tell=False)


def create_backup(server, info, comment):
	global creating_backup
	acquired = creating_backup.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '§aBacking up§r, don''t spam', tell=False)
		return
	try:
		print_message(server, info, '§aBacking up§r, please wait', tell=False)
		start_time = time.time()
		touch_backup_folder()

		# previous plain logic
		'''
		# remove the last backup
		shutil.rmtree(get_slot_folder(SlotCount))

		# move slot i-1 to slot i
		for i in range(SlotCount, 1, -1):
			os.rename(get_slot_folder(i - 1), get_slot_folder(i))
		'''

		# make empty space for slot <slot>
		def move_backwards(slot):
			if get_slot_info(slot) is None or slot == SlotCount:
				folder = get_slot_folder(slot)
				if os.path.isdir(folder):
					shutil.rmtree(folder)
				return
			move_backwards(slot + 1)
			os.rename(get_slot_folder(slot), get_slot_folder(slot + 1))

		move_backwards(1)

		# start backup
		global game_saved, plugin_unloaded
		game_saved = False
		if TurnOffAutoSave:
			server.execute('save-off')
		server.execute('save-all flush')
		while True:
			time.sleep(0.01)
			if game_saved:
				break
			if plugin_unloaded:
				server.reply(info, 'Plugin unloaded, §aback up§r aborted!', tell=False)
				return
		slot_path = get_slot_folder(1)

		copy_worlds(ServerPath, slot_path)
		slot_info = {'time': format_time()}
		if comment is not None:
			slot_info['comment'] = comment
		with open(os.path.join(slot_path, 'info.json'), 'w') as f:
			json.dump(slot_info, f, indent=4)
		end_time = time.time()
		print_message(server, info, '§aBack up§r successfully, time cost §6{}§rs'.format(round(end_time - start_time, 1)), tell=False)
		print_message(server, info, format_slot_info(info_dict=slot_info), tell=False)
	except Exception as e:
		print_message(server, info, '§aBack up§r unsuccessfully, error code {}'.format(e), tell=False)
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
	print_message(server, info, 'Gonna restore the world to slot §6{}§r, {}'.format(slot, format_slot_info(info_dict=slot_info)), tell=False)
	print_message(
		server, info,
		command_run('Use §7{0} confirm§r to confirm §crestore§r'.format(Prefix), 'click to confirm', '{0} confirm'.format(Prefix))
		+ ', '
		+ command_run('§7{0} abort§r to abort'.format(Prefix), 'click to abort', '{0} abort'.format(Prefix))
		, tell=False
	)


def confirm_restore(server, info):
	global restoring_backup
	acquired = restoring_backup.acquire(blocking=False)
	if not acquired:
		print_message(server, info, '§cRestoring§r, don''t spam', tell=False)
		return
	try:
		global slot_selected
		if slot_selected is None:
			print_message(server, info, 'Nothing to confirm', tell=False)
			return
		slot = slot_selected
		slot_selected = None

		print_message(server, info, '§cRestore§r after 10 second', tell=False)
		for countdown in range(1, 10):
			print_message(server, info, command_run(
				'{} second later the world will be §crestored§r to slot §6{}§r, {}'.format(10 - countdown, slot, format_slot_info(slot_number=slot)),
				'click to abort restore!',
				'{} abort'.format(Prefix)
			), tell=False)
			for i in range(10):
				time.sleep(0.1)
				global abort_restore
				if abort_restore:
					print_message(server, info, '§cRestore§r aborted!', tell=False)
					return

		server.stop()
		server.logger.info('[QBM] Wait for server to stop')
		server.wait_for_start()

		server.logger.info('[QBM] Backup current world to avoid idiot')
		overwrite_backup_path = BackupPath + '/' + OverwriteBackupFolder
		if os.path.exists(overwrite_backup_path):
			shutil.rmtree(overwrite_backup_path)
		copy_worlds(ServerPath, overwrite_backup_path)
		with open(os.path.join(overwrite_backup_path, 'info.txt'), 'w') as f:
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
	print_message(server, info, 'Operation terminated!', tell=False)


def list_backup(server, info, size_display=SizeDisplay):
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

	print_message(server, info, '§d[Slot Information]§r', prefix='')
	backup_size = 0
	for i in range(SlotCount):
		slot = i + 1
		slot_info = format_slot_info(slot_number=slot)
		if size_display:
			dir_size = get_dir_size(get_slot_folder(slot))
		else:
			dir_size = 0
		backup_size += dir_size
		text = RTextList('[Slot §6{}§r] '.format(slot))
		if slot_info is not None:
			text += RTextList(
				RText('[▷] ', color=RColor.green).h(f'click to restore to slot §6{slot}§r').c(RAction.run_command, f'{Prefix} back {slot}'),
				RText('[×] ', color=RColor.red).h(f'click to delete slot §6{slot}§r').c(RAction.suggest_command, f'{Prefix} del {slot}')
			)
			if size_display:
				text += '§2{}§r '.format(format_dir_size(dir_size))
		text += slot_info
		print_message(server, info, text, prefix='')
	if size_display:
		print_message(server, info, 'Total space consumed: §a{}§r'.format(format_dir_size(backup_size)))


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
		'§d[Hotbar]§r' + '\n' +
		RText('>>> §aClick me to create a backup§r <<<')
			.h('Remember to write the comment')
			.c(RAction.suggest_command, f'{Prefix} make I''m a comment') + '\n' +
		RText('>>> §cClick me to restore to the latest backup§r <<<')
			.h('as known as the first slot')
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
	if cmd_len >= 2 and command[1] in MinimumPermissionLevel.keys():
		if server.get_permission_level(info) < MinimumPermissionLevel[command[1]]:
			print_message(server, info, '§cPermission denied§r')
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
	elif cmd_len == 3 and command[1] == 'del':
		delete_backup(server, info, command[2])

	else:
		print_message(server, info, command_run(
			'Unknown command, input §7{}§r for more information'.format(Prefix),
			'click to see help',
			Prefix
		))


def on_load(server, old):
	server.add_help_message(Prefix, command_run('§aback up§r/§crestore§r your world with §6{}§r slots'.format(SlotCount), 'click to check help message', Prefix))
	global creating_backup, restoring_backup
	if hasattr(old, 'creating_backup') and type(old.creating_backup) == type(creating_backup):
		creating_backup = old.creating_backup
	if hasattr(old, 'restoring_backup') and type(old.restoring_backup) == type(restoring_backup):
		restoring_backup = old.restoring_backup


def on_unload(server):
	global abort_restore, plugin_unloaded
	abort_restore = True
	plugin_unloaded = True
