#!/usr/bin/env python2
# -*- coding: utf8 -*-

"""
Simple git wrapper for dotfile management.

The idea
========

The trick is to turn your home directory into git repository and track
configuration files directly in the orginal place.
This way you don't need to setup symlinks for tracked configuration files or
copy them into the right place manually.
Since homedir usually contains many other files besides configuration worth
tracking, git needs to ignore all files in the working tree with the exception
of config files we actually want to track.

The idea itself is not new, see eg.:

 * psung.blogspot.com/2008/06/managing-dotfiles-with-git-continued.html
 * silas.sewell.org/blog/2009/03/08/profile-management-with-git-and-github/
 * necoro.wordpress.com/2009/10/08/managing-your-configuration-files-with-git-and-stgit
 * github.com/silas/scripts/blob/master/bin/config
 * many others ...

Example of such setup:

    $ mkdir ~/.config.git
    $ alias dotfile='git --git-dir=$HOME/.config.git/ --work-tree=$HOME'
    $ dotfile init
    $ echo '*' > .gitignore
    $ dotfile add -f ~/.gitignore
    $ dotfile commit -m 'initial commit (just gitignore)'

This script provides the same functionality as init command:

    $ dotfile.py init ~/.config.git

Then to include config file:

    $ dotfile.py add ~/.gitconfig
    $ dotfile.py commit -m 'initial git configuration'

Note: you can see what the wrapper does using '--debug' option.
"""

# TODO
# compatibility with python 2.4
# list available repos
# branching, public pushes, merging


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
        if args[0] == "ls":
            return self.cmd_ls()
        else:
            return self.git(args)

    def cmd_ls(self):
        """
        New command: list all files in repository.
        """
        return self.git(["ls-tree", "--full-tree", "--name-only", "-r", "HEAD"])

    def git(self, args):
        """
        Wrap git command for given args list.
        """
        if args[0] == "add":
            args.insert(1, "-f")
        cmd = ["git",
            "--git-dir=%s" % self.repo_dir,
            "--work-tree=%s" % self.tree_dir]
        cmd.extend(args)
        return shell_cmd(cmd, self.debug)

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
        "init path-to-repo-dir  initialize new repository on given path",
        "ls                     list all files in repository (via git ls-tree)",
        "repos                  list all initialized dotfile repositories",
        "any-git-command        run this git operation on dotfile repo",
        ]
    print usage
    print "Options:"
    for option in options:
        print "  %s" % option
    print "\nCommands:"
    for cmd in commands:
        print "  %s" % cmd


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

    # try to initialize repository first
    if args[0] == "init":
        if repo_dir is not None:
            msg = "Error: repository is already here: %s\n" % repo_dir
            sys.stderr.write(msg)
            return 1
        if len(args) == 2:
            repo_dir = args[1]
            try:
                retcode = repo.build(repo_dir=repo_dir)
                config.add_section(repo_name)
                config.set(repo_name, "repo_dir", repo_dir)
                config.set(repo_name, "tree_dir", tree_dir)
                config_file = open(os.path.expanduser("~/.dotfile"), "w")
                config.write(config_file)
                config_file.close()
            except (IOError, OSError), ex:
                sys.stderr.write("Error: repository init failed: %s\n" % ex)
                retcode = 1
        else:
            msg = "Error: specify path for the repository (eg. ~/.dotrepo.git)"
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
