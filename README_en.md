# QuickBackupM
---------

[中文](https://github.com/TISUnion/QuickBackupM/blob/master/README.md)

A plugin for multi slot back up / restore your world

Needs `0.8.2-alpha`+ [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

![snapshot](https://raw.githubusercontent.com/TISUnion/QuickBackupM/master/snapshot_en.png)

The backup worlds will be store in folder qb_multi like below:
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

## Command

`!!qb` help message

`!!qb make [<comment>]` Make a backup to slot 1, and shift the slots behind. `<comment>` is an optional comment message

`!!qb back [<slot>]` Restore the world to slot 1. When `<slot>` parameter is set it will restore to slot `<slot>`

`!!qb del [<slot>]` Delete the world in slot `<slot>`

`!!qb confirm` Use after execute `back` to confirm restore execution

`!!qb abort` Abort backup restoring

`!!qb list` Display slot information

When `<slot>` is not set the default value is `1`

In MCDR `!!qb back` and `!!qb del` needs permission level `helper`

## Constant explain

Custom your QuickBackupM 

### SizeDisplay

Default: `SizeDisplay = True`

Whether the occupied space is displayed when viewing the backup list

### SlotCount

Default: `SlotCount = 5`

The number of slot

### Prefix

Default: `Prefix = '!!qb'`

The command prefix

### BackupPath

Default: `BackupPath = './qb_multi'`

The backup root path

### TurnOffAutoSave

Default: `TurnOffAutoSave = True`

If turn off auto save when making backup or not

### IgnoreSessionLock

Default: `IgnoreSessionLock = True`

If ignore file `session.lock` during backup, which can solve the back up failure problem caused by `session.lock` being occupied by the server

### WorldNames

Default:

```
WorldNames = [
    'world',
]
```

A list of world folder that you want to backup. For vanilla there should be only 1 folder. For not vanilla server like bukkit or paper, there are 3 folders. You can write like:

```
WorldNames = [
    'world',
    'world_nether',
    'world_the_end',
]
```

### MinimumPermissionLevel

Default:

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

A dict for minimum permission level requirement. For the meaning of these value check [this](https://github.com/Fallen-Breath/MCDReforged/blob/master/doc/readme.md#权限)

Set everything to `0` so everyone can use every command
