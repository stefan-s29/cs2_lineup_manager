#!/usr/bin/env python3
# Copyright (c) 2026 Stefan Schätz
#
# This script was written by Claude (Anthropic).
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
cs2_lineup_manager.py

Creates or updates a CS2 configuration file (.cfg) that stores utility
lineups (Smoke, HE, Molotov, Flash) as "setpos_exact"/"setang_exact"
aliases. In-game, you can cycle back and forth between the lineups via
a bind (next_pos / prev_pos).

Each lineup is named "lineup_<type>_<name>", e.g. "lineup_sm_apps" for a
smoke titled "apps".

Examples:

    # Create a new file and add a smoke (type is optional, default = smoke)
    python cs2_lineup_manager.py -f lineups.cfg -n apps \
        -p "setpos_exact 1911.966309 -361.971741 261.031250;setang_exact 0.000000 166.384720 0.000000"

    # Add a flash (type via abbreviation or initial letter, case-insensitive)
    python cs2_lineup_manager.py -f lineups.cfg -n ct-spawn -t flash \
        -p "setpos_exact ...;setang_exact ..."
    python cs2_lineup_manager.py -f lineups.cfg -n ct-spawn -t F \
        -p "setpos_exact ...;setang_exact ..."

    # Add a molotov
    python cs2_lineup_manager.py -f lineups.cfg -n banana -t ml \
        -p "setpos_exact ...;setang_exact ..."

    # Remove a lineup ("lineup_"/type prefix optional, as long as the name is unique)
    python cs2_lineup_manager.py -f lineups.cfg -d apps
    python cs2_lineup_manager.py -f lineups.cfg -d sm_apps   # explicit, if ambiguous

    # Overwrite an existing lineup (same type + name = update instead of new entry)
    python cs2_lineup_manager.py -f lineups.cfg -n apps -t smoke -p "setpos_exact ...;setang_exact ..."
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

LINEUP_PREFIX = "lineup_"

# Keys used to cycle between lineups. Adjacent, unused by default in CS2 (no movement,
# chat, buy-menu or weapon binds sit here), and easy to reach without
# moving the hand off WASD. Adjust here if needed.
BIND_PREV = "["
BIND_NEXT = "]"

# Valid type abbreviations, as used in the alias name.
KNOWN_ABBRS = {"sm", "he", "ml", "fl"}

# Human-readable label per abbreviation (used in the "say" output on the HUD).
TYPE_LABELS = {"sm": "Smoke", "he": "HE", "ml": "Molotov", "fl": "Flash"}

# All accepted spellings (full name, abbreviation, initial letter) -> abbreviation.
# Input is lowercased before lookup, so it's case-insensitive.
TYPE_ALIASES = {
    "smoke": "sm", "sm": "sm", "s": "sm",
    "he": "he", "h": "he",
    "molotov": "ml", "ml": "ml", "m": "ml",
    "flash": "fl", "fl": "fl", "f": "fl",
}

DEFAULT_TYPE = "sm"

# Matches lines of the form: alias lineup_<rest> "<body>"
ALIAS_RE = re.compile(
    r'^\s*alias\s+' + re.escape(LINEUP_PREFIX) + r'(\S+)\s+"([^"]*)"\s*$',
    re.MULTILINE,
)

# lineups is kept as {(type_abbr, name): body}.
LineupKey = tuple  # (str, str)


def normalize_type(value: str) -> str:
    """Converts smoke/sm/s (in any case) etc. into the internal abbreviation
    (sm/he/ml/fl). Raises ValueError for an unknown type."""
    key = value.strip().lower()
    if key not in TYPE_ALIASES:
        valid = "smoke/sm/s, he/h, molotov/ml/m, flash/fl/f"
        raise ValueError(f'Unknown type "{value}". Valid options: {valid}')
    return TYPE_ALIASES[key]


# Matches lines of the form: bind <key> prev_pos / bind <key> next_pos
# The key may optionally be quoted (e.g. bind "KP_PLUS" next_pos).
BIND_RE = re.compile(
    r'^\s*bind\s+"?([^"\s]+)"?\s+(prev_pos|next_pos)\s*$',
    re.MULTILINE,
)


def parse_binds(text: str) -> tuple[str | None, str | None]:
    """Reads the current prev_pos/next_pos key binds from an existing file,
    if present. Returns (bind_prev, bind_next), either of which may be
    None if not found (or found more than once, in which case the first
    match wins)."""
    bind_prev = None
    bind_next = None
    for match in BIND_RE.finditer(text):
        key, target = match.group(1), match.group(2)
        if target == "prev_pos" and bind_prev is None:
            bind_prev = key
        elif target == "next_pos" and bind_next is None:
            bind_next = key
    return bind_prev, bind_next


def strip_prefix(name: str) -> str:
    """Removes a leading 'lineup_' prefix from the name, if present."""
    if name.startswith(LINEUP_PREFIX):
        return name[len(LINEUP_PREFIX):]
    return name


def parse_lineups(text: str) -> dict:
    """Reads all 'alias lineup_<type>_<name> "<body>"' lines from an
    existing file. Every alias is required to have a valid type prefix
    (sm/he/ml/fl); aliases without one are considered invalid/foreign and
    raise an error."""
    lineups: dict = {}
    for match in ALIAS_RE.finditer(text):
        raw, body = match.group(1), match.group(2)
        first, _, rest = raw.partition("_")
        if not rest or first.lower() not in KNOWN_ABBRS:
            raise ValueError(
                f'Alias "{LINEUP_PREFIX}{raw}" has no valid type prefix '
                f"(expected one of: {', '.join(sorted(KNOWN_ABBRS))}). "
                "Every lineup alias must be named 'lineup_<type>_<name>'."
            )
        type_abbr, name = first.lower(), rest
        lineups[(type_abbr, name)] = body
    return lineups


def build_lineup_body(pos: str, type_abbr: str, name: str) -> str:
    """Builds the alias body from the getpos/getpos_exact output and
    appends a 'say' command with type + name so the position is shown
    readably on the HUD."""
    pos = pos.strip().lstrip("]").strip().rstrip(";").strip()
    if not pos:
        raise ValueError("The given position is empty.")
    label = f"{TYPE_LABELS[type_abbr]} {name}"
    return f'{pos}; say {label}'


def resolve_delete_key(delete_arg: str, lineups: dict, type_abbr: str | None = None) -> LineupKey:
    """Finds the lineup key to delete. Accepts both the full identifier
    ('sm_apps') and just the name ('apps'), as long as it's unique.
    If type_abbr is given (via -t/--type), it takes precedence and is used
    to disambiguate lineups that share the same name but have different
    types, instead of requiring the type prefix inside the name itself."""
    given = strip_prefix(delete_arg)

    # 0) Explicit type given via -t/--type: use it to pin down the lineup.
    if type_abbr is not None:
        # Allow the name to still carry a (matching or redundant) type
        # prefix, e.g. "-d sm_apps -t sm", without breaking the lookup.
        first, _, rest = given.partition("_")
        name = rest if (rest and first.lower() in KNOWN_ABBRS) else given
        key = (type_abbr, name)
        if key in lineups:
            return key
        raise ValueError(
            f'Lineup "{type_abbr}_{name}" was not found. '
            f"Available: {', '.join(f'{t}_{n}' for t, n in lineups) or '(none)'}"
        )

    # 1) Exact match as "type_name" (e.g. "sm_apps")
    first, _, rest = given.partition("_")
    if rest and first.lower() in KNOWN_ABBRS:
        key = (first.lower(), rest)
        if key in lineups:
            return key

    # 2) Look up by plain name across all types
    matches = [key for key in lineups if key[1].lower() == given.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(f"{t}_{n}" for t, n in matches)
        raise ValueError(
            f'Lineup name "{given}" is ambiguous (multiple types exist). '
            f"Please specify it unambiguously, e.g.: {options}, "
            f"or narrow it down with -t/--type."
        )

    available = ", ".join(f"{t}_{n}" for t, n in lineups) or "(none)"
    raise ValueError(f'Lineup "{given}" was not found. Available: {available}')


def render_file(lineups: dict, bind_prev: str = BIND_PREV, bind_next: str = BIND_NEXT) -> str:
    """Generates the complete file content from the collected lineups."""
    lines: list = ["sv_cheats 1", ""]

    keys = list(lineups.keys())

    # One alias per lineup, named lineup_<type>_<name>
    for type_abbr, name in keys:
        lines.append(f'alias {LINEUP_PREFIX}{type_abbr}_{name} "{lineups[(type_abbr, name)]}"')
    lines.append("")

    if keys:
        n = len(keys)
        for i, (type_abbr, name) in enumerate(keys):
            next_i = (i + 1) % n
            prev_i = (i - 1) % n
            lines.append(
                f'alias goto_pos{i + 1} "{LINEUP_PREFIX}{type_abbr}_{name}; '
                f'alias next_pos goto_pos{next_i + 1}; '
                f'alias prev_pos goto_pos{prev_i + 1}"'
            )
        lines.append("")

        lines.append("alias next_pos goto_pos1")
        lines.append(f"alias prev_pos goto_pos{n}")
        lines.append("")

        lines.append(f"bind {bind_prev} prev_pos")
        lines.append(f"bind {bind_next} next_pos")
        lines.append("")

    return "\n".join(lines)


def _param_table(rows: list[tuple[str, str]], indent: str = "  ") -> str:
    """Formats (parameter, description) pairs as an aligned two-column
    table. Multi-line descriptions (containing '\\n') wrap under the
    first column, staying aligned with it."""
    width = max(len(name) for name, _ in rows) + 2
    lines = []
    for name, desc in rows:
        desc_lines = desc.split("\n")
        lines.append(f"{indent}{name.ljust(width)}{desc_lines[0]}")
        for cont in desc_lines[1:]:
            lines.append(f"{indent}{' ' * width}{cont}")
    return "\n".join(lines)


EPILOG = f"""\
Detailed guide
--------------

Adding a lineup:
{_param_table([
    ("-n/--name", 'Title of the lineup, e.g. "apps"'),
    ("-p/--pos", "Position, paste the line getpos/getpos_exact prints"),
    ("-t/--type", "smoke (default), he, molotov or flash - full word,\n"
                   "abbreviation (sm/he/ml/fl) or initial letter (s/h/m/f),\n"
                   "any case"),
])}

  Example:
    python cs2_lineup_manager.py -f lineups.cfg -n apps -t flash \\
        -p "setpos_exact ...;setang_exact ..."

  Note: a name + type that already exists gets overwritten with the new position.

Deleting a lineup:
{_param_table([
    ("-d/--delete", 'Title of the lineup to remove, e.g. "apps"'),
    ("-t/--type", "only needed if that name exists under more than one type"),
])}

  Example:
    python cs2_lineup_manager.py -f lineups.cfg -d apps -t smoke

Cycle keys:
{_param_table([
    ("--bind-prev", "key that switches to the previous lineup"),
    ("--bind-next", "key that switches to the next lineup"),
])}

  Accepts anything the CS2 "bind" command understands, e.g. "F5", "[".
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manages a CS2 lineup configuration file.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,  # enables -h/--help, printing the description + epilog above
    )
    parser.add_argument(
        "-f", "--file", required=True,
        help="Filename of the .cfg file to create or read",
    )
    parser.add_argument(
        "-d", "--delete", metavar="NAME",
        help=(
            'Deletes the lineup with this name ("lineup_"/type prefix optional, '
            "if unambiguous, or disambiguate via -t/--type)"
        ),
    )
    parser.add_argument(
        "-n", "--name",
        help='Title of the lineup to add/update (without the "lineup_" prefix)',
    )
    parser.add_argument(
        "-p", "--pos",
        help="Position as output by getpos/getpos_exact in-game",
    )
    parser.add_argument(
        "-t", "--type", default=None,
        help=(
            "Utility type: smoke/sm/s, he/h, molotov/ml/m or flash/fl/f "
            "(case-insensitive). When adding a lineup, sets its type "
            "(default: smoke). When deleting, disambiguates between "
            "lineups that share the same name but have different types."
        ),
    )
    parser.add_argument(
        "--bind-prev", metavar="KEY", default=None,
        help=(
            'Key bound to "prev_pos" in the generated file. If omitted, '
            "the bind already present in the file is kept (if any), "
            f'otherwise defaults to "{BIND_PREV}". Any value accepted by '
            'the CS2 "bind" command, e.g. "[", "F5" or "KP_MINUS".'
        ),
    )
    parser.add_argument(
        "--bind-next", metavar="KEY", default=None,
        help=(
            'Key bound to "next_pos" in the generated file. If omitted, '
            "the bind already present in the file is kept (if any), "
            f'otherwise defaults to "{BIND_NEXT}". Any value accepted by '
            'the CS2 "bind" command, e.g. "]", "F6" or "KP_PLUS".'
        ),
    )
    args = parser.parse_args()

    path = Path(args.file)
    file_exists = path.exists()

    if file_exists:
        text = path.read_text(encoding="utf-8")
        try:
            lineups = parse_lineups(text)
        except ValueError as exc:
            parser.error(str(exc))
        existing_bind_prev, existing_bind_next = parse_binds(text)
    else:
        lineups = {}
        existing_bind_prev, existing_bind_next = None, None

    type_abbr = None
    if args.type is not None:
        try:
            type_abbr = normalize_type(args.type)
        except ValueError as exc:
            parser.error(str(exc))

    action_requested = (
        args.delete is not None
        or (args.name is not None and args.pos is not None)
        or args.bind_prev is not None
        or args.bind_next is not None
    )

    if not action_requested:
        if not file_exists:
            parser.error(
                "Nothing to do: to create a new file, at least one lineup must "
                "be given via --name and --pos."
            )
        print(f'Nothing to do, "{args.file}" is left unchanged.\n')
        parser.print_help()
        return

    # --- Delete ---
    if args.delete is not None:
        if not file_exists:
            parser.error(
                f'--delete cannot be used: the file "{args.file}" '
                "does not exist yet and would be newly created."
            )
        try:
            key = resolve_delete_key(args.delete, lineups, type_abbr)
        except ValueError as exc:
            parser.error(str(exc))
        del lineups[key]
        print(f'Lineup "{key[0]}_{key[1]}" deleted.')

    # --- Add/update ---
    if args.name is not None and args.pos is not None:
        add_type = type_abbr if type_abbr is not None else DEFAULT_TYPE
        add_name = strip_prefix(args.name)
        try:
            body = build_lineup_body(args.pos, add_type, add_name)
        except ValueError as exc:
            parser.error(str(exc))
        lineups[(add_type, add_name)] = body
        print(f'Lineup "{add_type}_{add_name}" added/updated.')
    elif args.name is not None and args.pos is None:
        parser.error("--name was given, but --pos is missing.")
    elif args.pos is not None and args.name is None:
        parser.error("--pos was given, but --name is missing.")

    if args.bind_prev is not None and not args.bind_prev.strip():
        parser.error("--bind-prev must not be empty.")
    if args.bind_next is not None and not args.bind_next.strip():
        parser.error("--bind-next must not be empty.")

    bind_prev = (args.bind_prev.strip() if args.bind_prev else None) or existing_bind_prev or BIND_PREV
    bind_next = (args.bind_next.strip() if args.bind_next else None) or existing_bind_next or BIND_NEXT
    if bind_prev.lower() == bind_next.lower():
        print(
            f'Warning: --bind-prev and --bind-next resolve to the same key '
            f'("{bind_prev}"). Both prev_pos and next_pos will be bound to it, '
            "so only cycling in one direction will work as expected."
        )

    content = render_file(lineups, bind_prev=bind_prev, bind_next=bind_next)
    path.write_text(content, encoding="utf-8")
    print(f'File "{args.file}" written ({len(lineups)} lineup(s)).')



if __name__ == "__main__":
    main()