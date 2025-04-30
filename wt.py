import argparse
import os
import sys
from pathlib import Path

from git import GitCommandError, Repo
from iterfzf import iterfzf

from utils import logger


def get_repo() -> Repo:
    return Repo(Path.cwd(), search_parent_directories=True)


def get_bare_worktree_path(repo: Repo) -> Path | None:
    for worktree in repo.git.worktree("list").splitlines():
        if "(bare)" in worktree:
            return Path(worktree.split()[0])
    raise ValueError("No bare worktree found")


def list_worktrees(repo: Repo) -> str:
    return repo.git.worktree("list")


# TODO: chdir to the bare_path does not affect the next line git command
def add_worktree(args: argparse.Namespace, repo: Repo) -> Path:
    bare_path = get_bare_worktree_path(repo)
    logger.info(f"The bare path found: {bare_path}")
    os.chdir(bare_path)
    repo.git.worktree("add", *args.path)
    os.chdir(bare_path / args.path[0])
    logger.info("Fetching changes")
    repo.remotes.origin.fetch(all=True)
    logger.info("Merging with master")
    repo.git.merge("origin/master")
    return Path.cwd()


def select_worktree(repo: Repo, exclude_bare: bool = True) -> Path | str:
    worktrees = repo.git.worktree("list").splitlines()
    options = [line for line in worktrees if not ("(bare)" in line and exclude_bare)]
    if not options:
        logger.error("No worktrees available.")
        return ""
    try:
        choice = iterfzf(options, prompt="Select worktree > ")
        return Path(choice.split()[0])
    except KeyboardInterrupt:
        return ""


# TODO: check if there are modified or untracked files before removing
def remove_worktree(args: argparse.Namespace, repo: Repo) -> Path:
    bare_path = get_bare_worktree_path(repo)
    if args.all:
        os.chdir(bare_path)
        worktrees = repo.git.worktree("list").splitlines()
        for line in worktrees:
            if "(bare)" in line or "master" in line:
                continue
            dir_path = line.split()[0]
            try:
                repo.git.worktree("remove", dir_path)
            except GitCommandError:
                logger.exception("Failed to remove worktree", exc_info=True)
        return bare_path
    else:
        dir_path = select_worktree(repo)
        cwd_path = Path.cwd()
        if dir_path:
            logger.info(f"Removing worktree: {dir_path}")
            repo.git.worktree("remove", dir_path)
            return bare_path if dir_path.name == cwd_path.name else cwd_path


def switch_worktree(repo: Repo) -> Path:
    dir_path = select_worktree(repo)
    if dir_path:
        logger.info(f"Changing current worktree: {dir_path.name}")
        return dir_path


def cd_bare(repo: Repo) -> str:
    bare_path = get_bare_worktree_path(repo)
    logger.info(f"Changing to bare directory: {bare_path}")
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
    repo = get_repo()

    if args.command == "list":
        print(list_worktrees(repo), file=sys.stderr)
    elif args.command == "bare":
        print(cd_bare(repo))
    elif args.command == "add":
        print(add_worktree(args, repo))
    elif args.command == "remove":
        print(remove_worktree(args, repo))
    else:
        print(switch_worktree(repo))


if __name__ == "__main__":
    main()
