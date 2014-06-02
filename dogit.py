#!/usr/bin/env python2
# -*- coding: utf8 -*-

"""
dogit: simple git wrapper for dotfile management
"""

# Copyright (C) 2013 martin.bukatovic@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import os
import sys
import subprocess
import platform
import getpass
import getopt
import ConfigParser


def shell_cmd(cmd_list, debug=False):
    """
    Execute given command. When debug mode is enabled, just print command to
    sdtout instead.
    """
    if debug:
        # quote arguments with space in it so that output is copy-paste friendly
        cmd_list, cmd_list_copy = [], cmd_list
        for cmd in cmd_list_copy:
            if ' ' in cmd:
                cmd = "'%s'" % cmd
            cmd_list.append(cmd)
        print " ".join(cmd_list)
    else:
        return subprocess.call(cmd_list)


class DotfileRepo(object):
    """
    Git repository wrapper.
    """

    # predefined git commands
    _commands = {
        "ls": ["ls-tree", "--full-tree", "--name-only", "-r", "HEAD"],
        }

    def __init__(self, repo_dir=None, tree_dir=None, debug=False):
        self.repo_dir = repo_dir
        self.tree_dir = tree_dir
        self.debug = debug

    def wrap(self, args):
        """
        Wrap git args list: try new commands first, then general git wrapper.
        """
        if len(args) < 1:
            return
        # if args doesn't match any predefined command, just run it as it is
        arg_list = self._commands.get(args[0]) or args
        return self.git(arg_list)

    def git(self, args):
        """
        Wrap git command for given args list.
        """
        cmd = ["git", "--git-dir=%s" % self.repo_dir]
        # HACK: submodule command uses --work-tree as a path to submodule itself
        if args[0] == "submodule":
            if len(args) > 1 and args[1] == "add":
                args.insert(2, "-f")
            else:
                # when not adding new module, it will cd into treedir itself
                if self.debug:
                    print "cd %s" % self.tree_dir
                else:
                    os.chdir(self.tree_dir)
        else:
            cmd.append("--work-tree=%s" % self.tree_dir)
        if args[0] == "add":
            args.insert(1, "-f")
        cmd.extend(args)
        return shell_cmd(cmd, self.debug)

    def clone(self, repo_url, repo_dir):
        """
        Setup repository by cloning from remote repo.

        Details: clone into bare repo, create local branch and switch into it
        without touching the working tree.
        """
        self.repo_dir = repo_dir
        local_branch = "local_%s@%s" % (getpass.getuser(), platform.uname()[1])

        self.git(["clone", "--bare", repo_url, repo_dir])
        # create new local branch
        self.git(["branch", local_branch])
        # switch branch on bare repository (to not touch files in working tree)
        self.git(["symbolic-ref", "HEAD", "refs/heads/%s" % local_branch])
        self.git(["config", "--bool", "core.bare", "false"])
        self.git(["reset"])
        if not self.debug:
            print "Check state of the repository:"
        self.git(["branch"])
        self.git(["status", "-s"])

    def build(self, repo_dir):
        """
        Create new git repository for dotfiles.
        """
        self.repo_dir = repo_dir

        if self.debug:
            print "mkdir %s" % self.repo_dir
        else:
            os.mkdir(self.repo_dir)

        self.git(["init", self.repo_dir])

        git_ignore_path = os.path.join(self.tree_dir, ".gitignore")
        if self.debug:
            print "echo '*' > %s" % git_ignore_path
        else:
            git_ignore = open(git_ignore_path, "w")
            git_ignore.write("*\n")
            git_ignore.close()

        self.git(["add", "-f", git_ignore_path])
        self.git(["commit", "-m", "initial commit (just gitignore)"])


def print_help():
    prog_name = os.path.basename(sys.argv[0])
    usage = "Usage: %s [options] <command> [command-options]\n" % prog_name
    options = [
        "-h, --help       show this help message and exit",
        "-d, --debug      enable debug mode",
        "-r, --repo name  use repository name instead of primary one",
        ]
    commands = [
        "init  path       create new repo on given path (eg. ~/data/dot.git)",
        "clone url path   clone repository from url into local repo on path",
        "ls               list all files in repository (via git ls-tree)",
        "repos            list all initialized dotfile repositories",
        "any-git-command  run this git operation on dotfile repo",
        ]
    print usage
    print "Options:"
    for option in options:
        print "  %s" % option
    print "\nCommands:"
    for cmd in commands:
        print "  %s" % cmd

def update_config(config, repo_name, **kwargs):
    """
    Update configuration for current repo.
    """
    if not config.has_section(repo_name):
        config.add_section(repo_name)
    for conf_name, conf_val in kwargs.iteritems():
        config.set(repo_name, conf_name, conf_val)
    config_file = open(os.path.expanduser("~/.dotfile"), "w")
    config.write(config_file)
    config_file.close()

def main():
    # default configuration
    repo_name = "primary-repo"
    repo_dir = None
    tree_dir = os.getenv("HOME")
    debug = False

    # using getopts config parsing to make wrapping of any command possible
    short_opts = "hdr:"
    long_opts = ["help", "debug", "repo="]
    try:
        opts, args = getopt.getopt(sys.argv[1:], short_opts, long_opts)
    except getopt.GetoptError as ex:
        sys.stderr.write("Error: %s\n" % ex)
        print_help()
        return 1
    if len(args) == 0:
        print_help()
        return 0
    for opt, arg in opts:
        if opt in ("-h", "help"):
            print_help()
            return 0
        elif opt in ("-r", "--repo"):
            repo_name = arg
        elif opt in ("-d", "--debug"):
            debug = True

    # try config file
    config = ConfigParser.SafeConfigParser()
    files_used = config.read([
        os.path.expanduser("~/.dotfile"),
        os.path.expanduser("~/.config/dotfile.conf"),
        ])
    if debug:
        sys.stderr.write("using config files: %s\n" % files_used)
    if config.has_option(repo_name, "repo_dir"):
        repo_dir = config.get(repo_name, "repo_dir")
    if config.has_option(repo_name, "tree_dir"):
        tree_dir = config.get(repo_name, "tree_dir")

    repo = DotfileRepo(repo_dir, tree_dir, debug=debug)

    # show error when initializing repo which seems to already exist
    if args[0] in ("init", "clone") and repo_dir is not None:
        msg = "Error: repository is already here: %s\n" % repo_dir
        sys.stderr.write(msg)
        return 1

    # try to initialize repository first
    if args[0] == "init":
        if len(args) == 2:
            repo_dir = args[1]
            try:
                retcode = repo.build(repo_dir=repo_dir)
                if not debug:
                    update_config(config, repo_name,
                        repo_dir=repo_dir,
                        tree_dir=tree_dir)
            except (IOError, OSError), ex:
                sys.stderr.write("Error: repository init failed: %s\n" % ex)
                retcode = 1
        else:
            msg = "Error: specify path for the repository (eg. ~/.dotrepo.git)"
            sys.stderr.write(msg + "\n\n")
            print_help()
            retcode = 1
        return retcode

    # clone repository from given url
    if args[0] == "clone":
        if len(args) == 3:
            repo_url = args[1]
            repo_dir = args[2]
            try:
                retcode = repo.clone(repo_url, repo_dir)
                if not debug:
                    update_config(config, repo_name,
                        repo_dir=repo_dir,
                        tree_dir=tree_dir)
            except (IOError, OSError), ex:
                sys.stderr.write("Error: repository clone failed: %s\n" % ex)
                retcode = 1
        else:
            msg = "Error: specify source url for origin repo and local path"
            sys.stderr.write(msg + "\n\n")
            print_help()
            retcode = 1
        return retcode

    # list names of all repositories
    if args[0] == "repos":
        for section in config.sections():
            print section
        return

    if repo_dir is None:
        if repo_name == "primary-repo":
            msg = "Error: Initialize primary repository first.\n\n"
        else:
            msg = "Error: No such repository: '%s'.\n\n" % repo_name
        sys.stderr.write(msg)
        print_help()
        return 1

    # other commands are executed via git wrapper
    return repo.wrap(args)

if __name__ == '__main__':
    sys.exit(main())
