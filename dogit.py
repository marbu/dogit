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

def get_local_branch_name():
    """
    Generate default name of local git branch: local_user@hostname
    """
    return "local_%s@%s" % (getpass.getuser(), platform.uname()[1])


class DotfileRepo(object):
    """
    Git repository wrapper.
    """

    # dict of dogit specific git aliases
    aliasess = {
        "ls": ["ls-tree", "--full-tree", "--name-only", "-r", "HEAD"],
        }

    def __init__(self, repo_dir, tree_dir=None, repo_name=None, debug=False):
        self.repo_dir = repo_dir
        self.tree_dir = tree_dir or os.getenv("HOME")
        self.debug = debug
        self.repo_name = repo_name # this is used for configuration dump only

    @classmethod
    def load_repo(cls, repo_name, config, debug=False):
        """
        Create repository object based on info from config file.
        """
        repo_dir = config.get(repo_name, "repo_dir")
        tree_dir = config.get(repo_name, "tree_dir", None)
        repo = cls(repo_dir, tree_dir, repo_name=repo_name, debug=debug)
        return repo

    def export_config(self):
        """
        Export dictionary with configuration of this repository.
        """
        conf = {
            "repo_dir": self.repo_dir,
            "tree_dir": self.tree_dir, }
        return conf

    def git(self, *args):
        """
        Wrap git command for given args list.
        """
        args = list(args)
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

    def wrap(self, args):
        """
        Wrap git command for given args list, predefined commands has priority.
        """
        if len(args) < 1:
            return
        # if args doesn't match any predefined command, just run it as it is
        args = self.aliasess.get(args[0]) or args
        return self.git(*args)

    @classmethod
    def clone(cls, repo_name, repo_url, repo_dir, debug=False):
        """
        Setup repository by cloning from remote repo.

        Details: clone into bare repo, create local branch and switch into it
        without touching the working tree.
        """
        local_branch = get_local_branch_name()
        # TODO: repo_tree undefined by default, fix it
        repo = cls(repo_dir, tree_dir=None, repo_name=repo_name, debug=debug)
        repo.git("clone", "--bare", repo_url, repo_dir)
        # create new local branch
        repo.git("branch", local_branch)
        # switch branch on bare repository (to not touch files in working tree)
        repo.git("symbolic-ref", "HEAD", "refs/heads/%s" % local_branch)
        repo.git("config", "--bool", "core.bare", "false")
        repo.git("reset")
        if not repo.debug:
            print "Check state of the repository:"
        repo.git("branch")
        repo.git("status", "-s")
        return repo

    @classmethod
    def init(cls, repo_name, repo_dir, repo_tree=None, debug=False):
        """
        Create new git repository for dotfiles.
        """
        repo = cls(repo_dir, repo_tree, repo_name=repo_name, debug=debug)

        if repo.debug:
            print "mkdir %s" % repo.repo_dir
        else:
            os.mkdir(repo.repo_dir)

        repo.git("init", repo.repo_dir)

        git_ignore_path = os.path.join(repo.tree_dir, ".gitignore")
        if repo.debug:
            print "echo '*' > %s" % git_ignore_path
        else:
            git_ignore = open(git_ignore_path, "w")
            git_ignore.write("*\n")
            git_ignore.close()

        repo.git("add", git_ignore_path)
        repo.git("commit", "-m", "initial commit (just gitignore)")
        repo.git("checkout", "-b", get_local_branch_name())

        return repo

def update_config(config, repo):
    """
    Update configuration for current repo.
    """
    if not config.has_section(repo.repo_name):
        config.add_section(repo.repo_name)
    for conf_name, conf_val in repo.export_config().iteritems():
        config.set(repo.repo_name, conf_name, conf_val)
    config_file = open(os.path.expanduser("~/.dogit"), "w")
    config.write(config_file)
    config_file.close()

def print_help():
    prog_name = os.path.basename(sys.argv[0])
    usage = "Usage: %s [options] <command> [command-options]\n" % prog_name
    options = [
        "-h, --help       show this help message and exit",
        "-d, --debug      enable debug mode (aka dry run)",
        "-r, --repo name  use repository name instead of primary one",
        ]
    commands = [
        "init repo [tree] create new dogit repository",
        "                 repo is path of bare git repo (eg. ~/data/dot.git)",
        "                 tree is working tree path (~ by default)",
        "clone url path   clone repository from url into local repo on path",
        "repos            list all initialized dotfile repositories",
        "ls               list all files in repository (via git ls-tree)",
        "any-git-command  run this git operation on dotfile repo",
        ]
    print usage
    print "Options:"
    for option in options:
        print "  %s" % option
    print "\nCommands:"
    for cmd in commands:
        print "  %s" % cmd

def main():
    debug = False       # when True, no real actions are performed (dry run)
    repo_name = None    # name of current working repository

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

    # try to read config file
    config = ConfigParser.SafeConfigParser()
    config.read(os.path.expanduser("~/.dogit"))

    # get list of repositories listed in config file
    repo_list = config.sections()

    # get name of working repository (specified or first one from config file)
    if repo_name is None and len(repo_list) > 0:
        repo_name = repo_list[0]

    # cli commands: listing known repositories
    if args[0] == "repos":
        for repo_name in repo_list:
            print repo_name
        return

    # cli commands: initialization
    if args[0] in ("init", "clone"):
        # don't touch a repository which is already defined
        if repo_name in repo_list:
            msg = "Error: repository {0:s} is already defined\n"
            sys.stderr.write(msg.format(repo_name))
            return 1
        # try to use default repo name if suitable
        if repo_name is None:
            if len(repo_list) == 0:
                repo_name = "primary-repo"
            else:
                msg = ("Error: this is not 1st repository "
                    "so you need to specify repo name to create another one\n")
                sys.stderr.write(msg)
                return 1
        try:
            if args[0] == "init":
                repo = DotfileRepo.init(repo_name, *args[1:], debug=debug)
            elif args[0] == "clone":
                repo = DotfileRepo.clone(repo_name, *args[1:], debug=debug)
            if not debug:
                update_config(config, repo)
        except (IOError, OSError), ex:
            msg = "Error: repository {0:s} failed: %s\n".format(args[0], ex)
            sys.stderr.write(msg)
            return 1
        except TypeError, ex:
            msg = "Error: {0:s} command got wrong number of arguments\n\n"
            sys.stderr.write(msg.format(args[0]))
            print_help()
            return 1
        return

    # for all the rest: try to run it as a git operation on dotfile repo
    try:
        repo = DotfileRepo.load_repo(repo_name, config, debug)
        return repo.wrap(args)
    except ConfigParser.Error, ex:
        msg = "Error: wrong configuration: '%s'.\n" % ex
        sys.stderr.write(msg)
        return 1

if __name__ == '__main__':
    sys.exit(main())
