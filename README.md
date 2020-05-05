# QuickBackupM
---------

[English](https://github.com/TISUnion/QuickBackupM/blob/master/README_en.md)

一个支持多槽位的快速备份＆回档插件

兼容 [MCDaemon](https://github.com/kafuuchino-desu/MCDaemon) 以及 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

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

当 `<slot>` 未被指定时默认选择槽位 `1`

在 MCDR 环境下，默认配置下 `!!qb back` 以及 `!!qb share` 需要权限等级 `helper`

## 一些常量说明

调整这些常量的数值也就是在配置 QuickBackupM 插件

### SizeDisplay

默认值: `SizeDisplay = True`

查看备份列表是否显示占用空间

### SlotCount

默认值: `SlotCount = 5`

存档槽位的数量

### Prefix

默认值: `Prefix = '!!qb'`

触发指令的前缀

### BackupPath

默认值: `BackupPath = './qb_multi'`

备份储存的路径

### TurnOffAutoSave

默认值: `TurnOffAutoSave = True`

是否在备份时临时关闭自动保存

### IgnoreSessionLock

默认值: `IgnoreSessionLock = True`

是否在备份时忽略文件 `session.lock`。这可以解决 `session.lock` 被服务端占用导致备份失败的问题

### WorldNames

默认值:

```
WorldNames = [
    'world',
]
```

需要备份的世界文件夹列表，原版服务端只会有一个世界，在默认值基础上填上世界文件夹的名字即可

对于非原版服务端如水桶、水龙头服务端，会有三个世界文件夹，此时可填写：
```
WorldNames = [
    'world',
    'world_nether',
    'world_the_end',
]
```

### MinimumPermissionLevel

默认值:

```
MinimumPermissionLevel = {
	'make': 1,
	'back': 2,
	'confirm': 1,
	'abort': 1,
	'share': 2,
	'list': 0,
}
```

一个字典，代表使用不同类型指令需要权限等级。数值含义见[此处](https://github.com/Fallen-Breath/MCDReforged/blob/master/doc/readme_cn.md#权限)

把所有数值设置成 `0` 以让所有人均可操作
