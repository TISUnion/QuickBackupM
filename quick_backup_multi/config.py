from typing import List, Dict

from mcdreforged.api.utils.serializer import Serializable


class SlotInfo(Serializable):
    delete_protection: int = 0


class Configuration(Serializable):
    size_display: bool = True
    turn_off_auto_save: bool = True
    enable_copy_file_range: bool = False
    ignored_files: List[str] = [
        'session.lock'
    ]
    kept_files: List[str] = ["ledger.sqlite","ledger.mv.db","ledger.h2.db"]  # Add kept_files for ledger database etc..

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
