# QuickBackupM
---------

[中文](https://github.com/TISUnion/QuickBackupM/blob/master/README.md)

A plugin for multi slot back up / restore your world

The `master` branch is the Chinese version and the `english` branch is the English version

Needs `v2.0.1`+ [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

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

`!!qb del <slot>` Delete the world in slot `<slot>`

`!!qb rename <slot> <comment>` Modify the comment of slot `<slot>`, aka rename the slot

`!!qb confirm` Use after execute `back` to confirm restore execution

`!!qb abort` Abort backup restoring

`!!qb list` Display slot information

`!!qb reload` Reload the config file

When `<slot>` is not set the default value is `1`

## Config file explaination

The config file is `config/QuickBackupM.json`. It will automatically generate at the first run

### slots

Default：

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

The amount of seconds for each slots to be protected from overwriting. Set it to `0` to disable protection

The size of this list also determines the amount of backup slot

With the default value, there are 5 slots in total, among which the first 3 slots have no protection, the 4th slot will be protected for 3 hours (3 * 60 * 60 seconds), and the 5th slot will be protected for 3 days

Please ensure that the protection time does not decrease with the slot number, that is, the protection time of the nth slot cannot be greater than the protection time of the n + 1th slot, otherwise there may be undefined behavior

Backups created by older QuickBackupM plugin don't support this feature

### size_display

Default: `true`

Whether the occupied space is displayed when viewing the backup list

### turn_off_auto_save

Default: `true`

If turn off auto save when making backup or not

### copy_on_write

Default: `false`

Useing copy_on_write in some File system(incremental backup)

### ignored_files

Default:

```
"ignored_files": [
    "session.lock"
]
```

A list of file names to be ignored during backup. It contains `session.lock` by default to solve the backup failure problem caused by `session.lock` being occupied by the server

If the name string starts with `*`, then it will ignore files with name ending with specific string, e.g. `*.test` makes all files ends with `.test` be ignored, like `a.test`

If the name string ends with `*`, then it will ignore files with name starting with specific string, e.g. `temp*`  makes all files starts with `temp` be ignored, like `tempfile`

### saved_world_keywords

Default:

```
"saved_world_keywords": [
    "Saved the game",
    "Saved the world"
]
```

Keywords for the plugin to consider if the server has saved the world

It is considered that the world has been saved if any keyword string equals to the server output, then the plugin will start copying the world files

### backup_path

Default: `./qb_multi`

The backup root path

### server_path

Default: `./server`

The folder path of the server. `./server` is the default server path for MCDR

### overwrite_backup_folder

Default: `overwrite`

The backup position of the overwritten world. With default config file the path will be `./qb_multi/overwrite`

### WorldNames

Default:

```
"world_names": [
    "world"
]
```

A list of world folder that you want to back up. For vanilla there should be only 1 folder. 

For not vanilla server like bukkit or paper, there are 3 folders. You can write like:

```
"world_names": [
    "world",
    "world_nether",
    "world_the_end"
]
```

If the world name specified points to a symlink file, all dereferenced symbolic links and the final actual world folder will be backed up:

```sh
mcd_root/
    server.py

    server/
        world -> target_world # world is a symlink currently pointing to target_world
        target_world/
        other_world/

    qb_multi/
        slot1/
            info.json
            world -> target_world  # Symlink copied to backup slot
            target_world/ # The current linked world is copied along with symlink
        ...
```

Doing `!!qb back` will restore everything from world name symlink to the final actual world folder in the slot to the server's corresponding place. This implies that if the symlink has changed its target world, the server will be restored to the world when making backup, and the world before restoring will not be overwritten

### backup_format

The format of the stored backup

| Value    | Explanation                                                                                                                                                             |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `plain`  | Store the backup directly via file / directory copy. The default value, the only supported format in QBM < v1.8                                                         |
| `tar`    | Pack the files into `backup.tar` in tar format. Recommend value. It can significantly reduce the file amount. Although you cannot access files inside the backup easily |
| `tar_gz` | Compress the files into `backup.tar.gz` in tar.gz format. The backup size will be smaller, but the time cost in backup / restore will increase                          |
| `tar_xz` | Compress the files into `backup.tar.xz` in tar.xz format. The backup size will be much smaller, but the time cost in backup / restore will greatly increase             |

The backup format of the slot will be stored inside the `info.json` of the slot, and will be read when restoring, so you can have different backup formats in your slots.
If the backup format value doesn't exist, QBM will assume that it's a backup created from old QBM, and use the default `plain` format

If the `backup_format` value is invalid in the config file, the default value `plain` will be used

### compress_level

An integer in range 1 ~ 9, representing the compress level when config `backup_format` is set to `tar_gz`.
The higher the level is, the higher the compression rate will be, and the longer the time it will take.

Default: 1

### minimum_permission_level

Default:

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

A dict for minimum permission level requirement. For the meaning of these value check [this](https://mcdreforged.readthedocs.io/en/latest/permission.html)

Set everything to `0` so everyone can use every command
