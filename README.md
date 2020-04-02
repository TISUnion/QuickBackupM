# QuickBackupM

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

## 格式说明

`!!qb` 显示帮助信息

`!!qb make [<comment>]` 创建一个储存至槽位 `1` 的备份，并将后移已有槽位。`<comment>` 为可选存档注释

`!!qb back [<slot>]` 回档为槽位 `<slot>` 的存档。当 `<slot>` 参数被指定时将会回档为槽位 `<slot>`

`!!qb confirm` 在执行 `back` 后使用，再次确认是否进行回档

`!!qb abort` 在任何时候键入此指令可中断回档

`!!qb list` 显示各槽位的存档信息

当 `<slot>` 未被指定时默认选择槽位 `1`
