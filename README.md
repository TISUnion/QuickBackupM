# QuickBackupM
---------

[English](https://github.com/TISUnion/QuickBackupM/blob/master/README_en.md)

一个支持多槽位的快速备份＆回档插件

`master` 分支为中文版，`english` 分支为英文版

需要 `v2.0.1` 以上的 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

![snapshot](https://raw.githubusercontent.com/TISUnion/QuickBackupM/master/snapshot.png)

备份的存档将会存放至 qb_multi 文件夹中，文件目录格式如下：
```
mcd_root/
    server.py

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
```

## 命令格式说明

`!!qb` 显示帮助信息

`!!qb make [<comment>]` 创建一个储存至槽位 `1` 的备份，并将后移已有槽位。`<comment>` 为可选存档注释

`!!qb back [<slot>]` 回档为槽位 `<slot>` 的存档。

`!!qb del [<slot>]` 删除槽位 `<slot>` 的存档。

`!!qb confirm` 在执行 `back` 后使用，再次确认是否进行回档

`!!qb abort` 在任何时候键入此指令可中断回档

`!!qb list` 显示各槽位的存档信息

`!!qb reload` 重新加载配置文件

当 `<slot>` 未被指定时默认选择槽位 `1`

## 配置文件选项说明

配置文件为 `config/QuickBackupM.json`。它会在第一次运行时自动生成

### slots

默认值：

```
"slots": [
    {
        "delete_protection": 0
    },
    {
        "delete_protection": 0
    },
    {
        "delete_protection": 0
    },
    {
        "delete_protection": 10800
    },
    {
        "delete_protection": 259200
    }
]
```

每个槽位被保护不被覆盖的秒数。设置为 `0` 则表示不保护

该列表的长度也决定了槽位的数量

在默认值中，一共有 5 个槽位，其中前三个槽位未设置保护时间，第四个槽位会被保护三个小时（3 * 60 * 60 秒），第五个槽位会被保护三天

请保证保护时间是随着槽位序号单调不下降的，也就是第 n 给个槽位的保护时间不能大于第 n + 1 个槽位的保护时间，否则可能有未定义的行为

由旧的 QuickBackupM 插件创建的备份不支持这个特性

### size_display

默认值: `true`

查看备份列表是否显示占用空间

### turn_off_auto_save

默认值: `true`

是否在备份时临时关闭自动保存

### ignored_files

默认值:

```
"ignored_files": [
    "session.lock"
]
```

在备份时忽略的文件名列表，默认仅包含 `session.lock` 以解决 `session.lock` 被服务端占用导致备份失败的问题

若文件名字符串以 `*` 开头，则将忽略以指定字符串结尾的文件，如 `*.test` 表示忽略所有以 `.test` 结尾的文件，如 `a.test`

若文件名字符串以 `*` 结尾，则将忽略以指定字符串开头的文件，如 `temp*` 表示忽略所有以 `temp` 开头的文件，如 `tempfile`

### saved_world_keywords

默认值:

```
"saved_world_keywords": [
    "Saved the game",
    "Saved the world"
]
```

用于识别服务端已保存完毕存档的关键词

如果服务器的输出与任何一个关键词相符，则认为存档已保存完毕，随后插件将开始复制存档文件

### backup_path

默认值: `./qb_multi`

备份储存的路径

### server_path

默认值：`./server`

服务端文件夹的路径。`./server` 即为 MCDR 的默认服务端文件夹路径

### overwrite_backup_folder

默认值: `overwrite`

被覆盖的存档的备份位置，在配置文件均为默认值的情况下路径为 `./qb_multi/overwrite`

### world_names

默认值:

```
"world_names": [
    "world"
]
```

需要备份的世界文件夹列表，原版服务端只会有一个世界，在默认值基础上填上世界文件夹的名字即可

对于非原版服务端如水桶、水龙头服务端，会有三个世界文件夹，此时可填写：
```
"world_names": [
    "world",
    "world_nether",
    "world_the_end"
]
```

如果指定的世界名指向了一个符号链接文件, 则该链接文件指向的最终世界文件夹，以及中途所有解引用出的符号链接文件都会被备份:

```sh
mcd_root/
    server.py

    server/
        world -> target_world # world 是一个当前指向 target_world 文件夹的符号链接
        target_world/
        other_world/

    qb_multi/
        slot1/
            info.json
            world -> target_world  # 符号链接复制到了备份槽中
            target_world/ # 符号链接当前指向的世界一起复制到了备份槽中
        ...
```

执行`!!qb back`时，会恢复备份槽中保存的世界文件夹，并将符号链接重新设置至备份槽中保存的世界。这表示如果后续该符号链接更改了指向的世界，回档时将恢复到备份时保存的世界

### minimum_permission_level

默认值:

```
"minimum_permission_level": {
	"make": 1,
	"back": 2,
	"del": 2,
	"confirm": 1,
	"abort": 1,
	"reload": 2,
	"list": 0,
}
```

一个字典，代表使用不同类型指令需要权限等级。数值含义见[此处](https://mcdreforged.readthedocs.io/zh_CN/latest/permission.html)

把所有数值设置成 `0` 以让所有人均可操作
