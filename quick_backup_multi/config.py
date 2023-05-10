from typing import List, Dict

from mcdreforged.api.utils.serializer import Serializable


class SlotInfo(Serializable):
	delete_protection: int = 0


class Configuration(Serializable):
	size_display: bool = True
	turn_off_auto_save: bool = True
	copy_on_write: bool = False
	ignored_files: List[str] = [
		'session.lock'
	]
	saved_world_keywords: List[str] = [
		'Saved the game',  # 1.13+
		'Saved the world',  # 1.12-
	]
	backup_path: str = './qb_multi'
	server_path: str = './server'
	overwrite_backup_folder: str = 'overwrite'
	world_names: List[str] = [
		'world'
	]
	backup_format: str = 'plain'  # "plain", "tar", "tar_gz"
	# 0:guest 1:user 2:helper 3:admin 4:owner
	minimum_permission_level: Dict[str, int] = {
		'make': 1,
		'back': 2,
		'del': 2,
		'rename': 2,
		'confirm': 1,
		'abort': 1,
		'reload': 2,
		'list': 0,
	}
	slots: List[SlotInfo] = [
		SlotInfo(delete_protection=0),  # 无保护
		SlotInfo(delete_protection=0),  # 无保护
		SlotInfo(delete_protection=0),  # 无保护
		SlotInfo(delete_protection=3 * 60 * 60),  # 三小时
		SlotInfo(delete_protection=3 * 24 * 60 * 60),  # 三天
	]

	def is_file_ignored(self, file_name: str) -> bool:
		for item in self.ignored_files:
			if len(item) > 0:
				if item[0] == '*' and file_name.endswith(item[1:]):
					return True
				if item[-1] == '*' and file_name.startswith(item[:-1]):
					return True
				if file_name == item:
					return True
		return False


if __name__ == '__main__':
	config = Configuration().get_default()
	config.ignored_files = ['*.abc', 'test', 'no*']
	assert config.is_file_ignored('.abc')
	assert config.is_file_ignored('1.abc')
	assert config.is_file_ignored('abc') is False
	assert config.is_file_ignored('test')
	assert config.is_file_ignored('1test') is False
	assert config.is_file_ignored('notest')
	assert config.is_file_ignored('no')
