import argparse
import os
from pathlib import Path

from git import Repo
from iterfzf import iterfzf

from utils import logger


def get_repo() -> Repo:
    return Repo(Path.cwd(), search_parent_directories=True)


def get_bare_worktree_path(repo: Repo) -> str:
    for worktree in repo.git.worktree("list").splitlines():
        if "(bare)" in worktree:
            return worktree.split()[0]
    raise ValueError("No bare worktree found")


def list_worktrees(repo: Repo) -> None:
    print(repo.git.worktree("list"))


def add_worktree(args: argparse.Namespace, repo: Repo) -> str:
    bare_path = get_bare_worktree_path(repo)
    os.chdir(bare_path)
    repo.git.worktree("add", *args.path)
    os.chdir(args.path[0])
    logger.info("Fetching changes")
    repo.remotes.origin.fetch(all=True)
    logger.info("Merging with master")
    repo.git.merge("origin/master")
    return os.getcwd()


def select_worktree(repo: Repo, exclude_bare: bool = True) -> str:
    worktrees = repo.git.worktree("list").splitlines()
    options = [line for line in worktrees if not ("(bare)" in line and exclude_bare)]
    if not options:
        logger.error("No worktrees available.")
        return ""
    try:
        choice = iterfzf(options, prompt="Select worktree > ")
        return choice.split()[0] or ""
    except KeyboardInterrupt:
        return ""


def remove_worktree(args: argparse.Namespace, repo: Repo) -> str:
    bare_path = get_bare_worktree_path(repo)
    if args.all:
        os.chdir(bare_path)
        worktrees = repo.git.worktree("list").splitlines()
        for line in worktrees:
            if "bare" in line or "master" in line:
                continue
            dir_path = line.split()[0]
            repo.git.worktree("remove", dir_path)
    else:
        dir_path = select_worktree(repo)
        if dir_path:
            if os.getcwd() == dir_path:
                os.chdir(bare_path)
            logger.info(f"Removing worktree: {dir_path}")
            repo.git.worktree("remove", dir_path)
    return bare_path


def switch_worktree(repo: Repo) -> str:
    dir_path = select_worktree(repo)
    if dir_path:
        logger.info(f"Changing current worktree: {os.path.basename(dir_path)}")
        os.chdir(dir_path)
    return dir_path


def cd_bare(repo: Repo) -> str:
    bare_path = get_bare_worktree_path(repo)
    logger.info(f"Changing to bare directory: {bare_path}")
    os.chdir(bare_path)
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
        list_worktrees(repo)
    elif args.command == "bare":
        cd_bare(repo)
    elif args.command == "add":
        add_worktree(args, repo)
    elif args.command == "remove":
        remove_worktree(args, repo)
    else:
        switch_worktree(repo)


if __name__ == "__main__":
    main()
