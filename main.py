import argparse
import logging
import os
import subprocess as sp
import sys
from pathlib import Path
from shutil import which
from typing import Optional

from iterfzf import iterfzf

logging.basicConfig(
    level=logging.DEBUG, format="{levelname}: {message}", style="{", stream=sys.stderr
)


def git(*cmds: str, cwd: Optional[Path] = None) -> sp.CompletedProcess:
    if not cwd:
        cwd = Path.cwd()
    git_command = [which("git"), *cmds]
    proc = sp.run(git_command, capture_output=True, cwd=cwd, text=True, check=True)
    return proc


def list_worktrees() -> str:
    return git("worktree", "list").stdout


def get_bare_worktree_path() -> Path:
    for worktree in list_worktrees().splitlines():
        if "(bare)" in worktree:
            return Path(worktree.split()[0])
    raise ValueError("No bare worktree found")


def add_worktree(args: argparse.Namespace) -> Path:
    bare_path = get_bare_worktree_path()
    git("worktree", "add", *args.path, cwd=bare_path)
    worktree_path = bare_path / args.path[0]
    logging.info("Fetching changes")
    git("fetch", "--all", cwd=worktree_path)
    logging.info("Merging with master")
    git("merge", "master", cwd=worktree_path)
    return worktree_path


def select_worktree(exclude_bare: bool = True) -> Path:
    worktrees = list_worktrees().splitlines()
    options = [line for line in worktrees if not ("(bare)" in line and exclude_bare)]
    if not options:
        logging.error("No worktrees available.")
        return Path()
    try:
        choice = iterfzf(options, prompt="Select worktree > ")
        return Path(choice.split()[0])  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
    except KeyboardInterrupt:
        return Path()


# TODO: check if there are modified or untracked files before removing
def remove_worktree(args: argparse.Namespace) -> Path:
    bare_path = get_bare_worktree_path()
    if args.all:
        os.chdir(bare_path)
        worktrees = list_worktrees().splitlines()
        for line in worktrees:
            if "(bare)" in line:
                continue
            dir_path = line.split()[0]
            try:
                logging.info(f"Removing {dir_path}...")
                git("worktree", "remove", dir_path)
            except sp.CalledProcessError:
                logging.exception(
                    f"Failed to remove {dir_path} worktree", exc_info=True
                )
        return bare_path
    else:
        dir_path = select_worktree()
        cwd_path = Path.cwd()
        if dir_path:
            logging.info(f"Removing worktree: {dir_path}")
            git("worktree", "remove", str(dir_path))
            return bare_path if dir_path.name == cwd_path.name else cwd_path
        return Path()


def switch_worktree() -> Path:
    dir_path = select_worktree()
    logging.info(f"Changing current worktree: {dir_path.name}")
    return dir_path


def cd_bare() -> Path:
    bare_path = get_bare_worktree_path()
    logging.info(f"Changing to bare directory: {bare_path}")
    return bare_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Git worktrees.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List all worktrees")
    subparsers.add_parser("bare", help="CD to a bare directory")

    parser_add = subparsers.add_parser("add", help="Add a new worktree")
    parser_add.add_argument(
        "path", nargs=argparse.REMAINDER, help="Path and branch for new worktree"
    )

    parser_remove = subparsers.add_parser("remove", help="Remove worktree(s)")
    parser_remove.add_argument(
        "--all", action="store_true", help="Remove all non-bare, non-master worktrees"
    )

    args = parser.parse_args()

    if args.command == "list":
        print(list_worktrees(), file=sys.stderr)
    elif args.command == "bare":
        print(cd_bare())
    elif args.command == "add":
        print(add_worktree(args))
    elif args.command == "remove":
        print(remove_worktree(args))
    else:
        print(switch_worktree())


if __name__ == "__main__":
    main()
