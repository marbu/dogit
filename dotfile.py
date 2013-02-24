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

 * silas.sewell.org/blog/2009/03/08/profile-management-with-git-and-github/
 * necoro.wordpress.com/2009/10/08/managing-your-configuration-files-with-git-and-stgit
 * github.com/silas/scripts/blob/master/bin/config
 * many others ...

Example of such setup (using unique local branch):

    $ mkdir ~/.config.git
    $ alias dotfile='git --git-dir=$HOME/.config.git/ --work-tree=$HOME'
    $ dotfile init
    $ echo '*' > .gitignore
    $ dotfile add -f ~/.gitignore
    $ dotfile commit -m 'initial commit (just gitignore)'
    $ dotfile branch -b local_$(uname)_$(whoami)

This script provides the same functionality as init command:

    $ dotfile.py init ~/.config.git

Then to include config file:

    $ dotfile.py add ~/.gitconfig
    $ dotfile.py commit -m 'initial git configuration'

Note: you can see what the wrapper does using '--debug' option.
"""

# TODO
# compatibility with python 2.4
# add entry into config file durint init
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

    def __init__(self, tree_dir=os.getenv("HOME"), debug=False):
        self.repo_dir = None
        self.tree_dir = tree_dir
        self.debug = debug
        self.branch_name = "local_%s_%s" % (
            platform.uname()[1], getpass.getuser())

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
        self.git(["checkout", "-b", self.branch_name])


def print_help():
    prog_name = os.path.basename(sys.argv[0])
    usage = "Usage: %s [options] <command> [command-options]\n" % prog_name
    options = [
        "-h, --help       show this help message and exit",
        "-d, --debug      enable debug mode",
        "-r, --repo name  use repository name instead of default one",
        ]
    commands = [
        "init path-to-repo-dir   initialize new repository on given path",
        "any-git-command         run this git operation on dotfile repo",
        ]
    print usage
    print "Options:"
    for option in options:
        print "  %s" % option
    print "\nCommands:"
    for cmd in commands:
        print "  %s" % cmd

def main():
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

    # default configuration
    config_file = os.path.join(os.getenv("HOME"), ".dotfile")
    repo_name = "default"
    debug = False
    for opt, arg in opts:
        if opt in ("-h", "help"):
            print_help()
            return 0
        elif opt in ("-r", "--repo"):
            repo_name = arg
        elif opt in ("-d", "--debug"):
            debug = True

    # repository initialization
    repo = DotfileRepo(debug=debug)
    if args[0] == "init":
        if len(args) == 2:
            try:
                retcode = repo.build(repo_dir=args[1])
            except (IOError, OSError), ex:
                print "Error: repository init failed: %s" % ex
                retcode = 1
            return retcode
        else:
            msg = "Error: specify path for the repository (eg. ~/.dotrepo.git)"
            sys.stderr.write(msg + "\n\n")
            print_help()
            return 1

    conf_parser = ConfigParser.SafeConfigParser()
    try:
        conf_file = open(config_file)
        conf_parser.readfp(conf_file)
        conf_file.close()
        repo.repo_dir = conf_parser.get(repo_name, "repo_dir")
        # optional configuration
        if conf_parser.has_option(repo_name, "tree_dir"):
            repo.tree_dir = conf_parser.get(repo_name, "tree_dir")
    except (IOError, ConfigParser.Error), ex:
        msg = "Error: problem with config file or repository: %s\n\n" % ex
        sys.stderr.write(msg)
        print_help()
        return 1

    # other commands are executed via git wrapper
    return repo.git(args)

if __name__ == '__main__':
    sys.exit(main())
