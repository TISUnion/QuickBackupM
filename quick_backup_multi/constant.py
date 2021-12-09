import os

from mcdreforged.api.event import LiteralEvent

PLUGIN_ID = 'quick_backup_multi'
Prefix = '!!qb'
CONFIG_FILE = os.path.join('config', 'QuickBackupM.json')

BACKUP_DONE_EVENT 		= LiteralEvent('{}.backup_done'.format(PLUGIN_ID))  # -> source, slot_info
RESTORE_DONE_EVENT 		= LiteralEvent('{}.restore_done'.format(PLUGIN_ID))  # -> source, slot, slot_info
TRIGGER_BACKUP_EVENT 	= LiteralEvent('{}.trigger_backup'.format(PLUGIN_ID))  # <- source, comment
TRIGGER_RESTORE_EVENT 	= LiteralEvent('{}.trigger_restore'.format(PLUGIN_ID))  # <- source, slot


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
