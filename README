# CS2 Lineup Manager

A small Python command-line tool that manages a CS2 configuration file
(`.cfg`) containing utility lineups (Smoke, HE, Molotov, Flash). In-game,
you can cycle between all saved positions with a key press.

Requires Python 3.9+ (standard library only, no external dependencies).

## How it works

1. Walk to the desired position in-game (e.g. for a smoke lineup) and
   type `getpos` or `getpos_exact` into the console.
2. Copy the printed line (`setpos_exact ...;setang_exact ...`).
3. Add it as a named lineup to the configuration file using this script
   (see examples below).
4. Load the file in-game via `exec <filename>` and cycle between the
   lineups using the configured keys.

> **Note:** The generated file contains `sv_cheats 1` along with
> `setpos_exact`/`setang_exact` calls, so it only works on local
> practice servers or bot matches, not in matchmaking.

## Usage

```bash
python cs2_lineup_manager.py -f <file> [options]
```

If `<file>` already exists, its lineups are read in first and the
requested changes are applied on top. If it doesn't exist yet, it is
created (in that case at least one new lineup must be given via
`-n`/`-p`).

### Parameters

| Parameter | Short | Meaning |
|---|---|---|
| `--file` | `-f` | **Required.** Path of the `.cfg` file to create or read. |
| `--name` | `-n` | Title of the lineup to add/update (used together with `--pos`). |
| `--pos` | `-p` | Position, as printed by `getpos`/`getpos_exact` in-game (used together with `--name`). |
| `--type` | `-t` | Utility type: `smoke`/`sm`/`s`, `he`/`h`, `molotov`/`ml`/`m`, `flash`/`fl`/`f` (case-insensitive). Default when adding: `smoke`. When deleting, used to disambiguate between lineups that share a name but have different types. |
| `--delete` | `-d` | Title of the lineup to delete (the `lineup_`/type prefix is optional, as long as the name is unambiguous). |
| `--bind-prev` | – | Key that switches to the previous lineup. If omitted, a bind already present in the file is kept; otherwise defaults to `[`. |
| `--bind-next` | – | Key that switches to the next lineup. If omitted, a bind already present in the file is kept; otherwise defaults to `]`. |
| `--help` | `-h` | Shows help, including a detailed guide with examples. |

If none of the effective parameters (`--delete`, `--name`+`--pos`,
`--bind-prev`, `--bind-next`) are given, an existing file is left
unchanged.

## Examples

Create a new file and add a smoke (type is optional, default `smoke`):

```bash
python cs2_lineup_manager.py -f lineups.cfg -n apps \
    -p "setpos_exact 1911.966309 -361.971741 261.031250;setang_exact 0.000000 166.384720 0.000000"
```

Add a flash (type via abbreviation or initial letter, any case):

```bash
python cs2_lineup_manager.py -f lineups.cfg -n ctspawn -t flash \
    -p "setpos_exact ...;setang_exact ..."
```

Overwrite an existing lineup (same name + same type):

```bash
python cs2_lineup_manager.py -f lineups.cfg -n apps -t smoke \
    -p "setpos_exact ...;setang_exact ..."
```

Delete a lineup:

```bash
python cs2_lineup_manager.py -f lineups.cfg -d apps
```

If the name exists for more than one type (e.g. a smoke *and* a flash
both named "apps"), also give the type:

```bash
python cs2_lineup_manager.py -f lineups.cfg -d apps -t flash
```

Change the keys used to cycle between lineups:

```bash
python cs2_lineup_manager.py -f lineups.cfg --bind-prev F5 --bind-next F6
```

## Structure of the generated file

Each lineup is stored as its own alias `lineup_<type>_<name>`, e.g.
`lineup_sm_apps` for a smoke named "apps". The type abbreviations are
`sm` (Smoke), `he` (HE), `ml` (Molotov) and `fl` (Flash).

All lineup aliases are chained into a cycle (`goto_pos1`, `goto_pos2`,
...), which `next_pos`/`prev_pos` step through on key press. Calling a
lineup sets the position via `setpos_exact`/`setang_exact` and briefly
shows its name and type on the HUD via `say`.

Example output for two lineups:

```
sv_cheats 1

alias lineup_sm_apps "setpos_exact 1911.966309 -361.971741 261.031250;setang_exact 0.000000 166.384720 0.000000; say Smoke apps"
alias lineup_fl_ctspawn "setpos_exact -569.968750 909.951904 26.031250;setang_exact 0.000000 -12.000854 0.000000; say Flash ctspawn"

alias goto_pos1 "lineup_sm_apps; alias next_pos goto_pos2; alias prev_pos goto_pos2"
alias goto_pos2 "lineup_fl_ctspawn; alias next_pos goto_pos1; alias prev_pos goto_pos1"

alias next_pos goto_pos1
alias prev_pos goto_pos2

bind [ prev_pos
bind ] next_pos
```

In-game, load the file with `exec lineups.cfg` and then cycle between
the lineups using `[`/`]` (or whichever keys you configured).

## Limitations / notes

- Files created by an older version of this script without a type
  prefix in the alias name are no longer supported — every alias must
  be named `lineup_<type>_<name>`.
- If `--bind-prev` and `--bind-next` are set to the same key, the
  script prints a warning but still writes the file (cycling will then
  only work in one direction).

## License

MIT License, see [LICENSE](LICENSE).
Copyright (c) 2026 Stefan Schätz.

## Credits

This script and its documentation were written by [Claude](https://claude.com) (Anthropic).