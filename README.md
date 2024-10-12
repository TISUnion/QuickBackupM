# QuickBackupM

> [!NOTE]
> QuickBackupM 已进入维护模式，只进行 bug 修复，不再增加新功能
> 
> 可以去看看 [Prime Backup](https://github.com/TISUnion/PrimeBackup) 插件，这是 QuickBackupM 的接替者，
> 是一套更为先进完善的备份解决方案，也是 QuickBackupM 的上位替代

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

`!!qb del <slot>` 删除槽位 `<slot>` 的存档。默认为槽位 1

`!!qb rename <slot> <comment>` 修改槽位 `<slot>` 的注释，即重命名这一槽位

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

### enable_copy_file_range

默认值: `false`

使用 `os.copy_file_range` 进行文件的复制

在某些文件系统中，它会使用基于写时复制（copy-on-write）的 reflink 技术，从而极大地提升复制速度

需求：

- Linux 平台
- Python >= 3.8
- 选项 `backup_format` 为 `plain`

### concurrent_copy_workers

默认值：`0`

参考值：`0`, `2`, `4`

复制文件时的并行度，当其值为 `n` 时，QBM 将使用 `n` 线程并行复制文件

当使用 SSD 或其他高 IO 性能的存储设备时，开启并行复制可以有效提升复制的速度，但 CPU、磁盘负载也会显著增加

设为 `0` 以关闭并行复制

需求：

- 选项 `backup_format` 为 `plain`

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

如果指定的世界名指向了一个符号链接文件, 则该链接文件指向的最终实际世界文件夹，以及中途所有解引用出的符号链接文件都会被备份:

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

执行 `!!qb back` 时，会从备份槽中指定世界名对应的符号链接开始，将所有符号链接以及最终实际的世界文件夹恢复至服务端的对应位置。这表示如果后续服务端的符号链接更改了指向的世界，回档时将恢复到备份时保存的世界，且不同世界的内容不会互相覆盖

### backup_format

备份的储存格式

| 值        | 含义                                                                        |
|----------|---------------------------------------------------------------------------|
| `plain`  | 直接复制文件夹/文件来储存。默认值，这同时也是 v1.8 以前版本的 QBM 唯一支持的储存格式                          |
| `tar`    | 使用 tar 格式直接打包储存至 `backup.tar` 文件中。推荐使用，可有效减少文件的数量，但无法方便地访问备份里面的文件         |
| `tar_gz` | 使用 tar.gz 格式压缩打包储存至 `backup.tar.gz` 文件中。能减小备份体积，但是备份/回档的耗时将显著增加。支持自定义压缩等级 |
| `tar_xz` | 使用 tar.xz 格式压缩打包储存至 `backup.tar.xz` 文件中。能最大化地减小备份体积，但是备份/回档的耗时将极大增加       |

槽位的备份模式会储存在槽位的 `info.json` 中，并在回档时读取，因此的不同的槽位可以有着不同的储存格式。
若其值不存在，QBM 会假定这个槽位是由旧版 QBM 创建的，并使用默认值 `plain`

若配置文件中的 `backup_format` 非法，则会使用默认值 `plain`

### compress_level

一个 1 ~ 9 的整数，代表在 `backup_format` 选项为 `tar_gz` 时，使用的压缩等级。
等级越高，压缩率相对越高，耗时也越高

默认值：1

### minimum_permission_level

默认值:

```
"minimum_permission_level": {
	"make": 1,
	"back": 2,
	"del": 2,
    "rename": 2,
	"confirm": 1,
	"abort": 1,
	"reload": 2,
	"list": 0,
}
```

一个字典，代表使用不同类型指令需要权限等级。数值含义见[此处](https://mcdreforged.readthedocs.io/zh_CN/latest/permission.html)

把所有数值设置成 `0` 以让所有人均可操作
