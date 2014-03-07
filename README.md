# gidot - git based dotfiles manager

## The idea

The trick is to turn your home directory into git repository and track
configuration files directly in the original place.
This way you don't need to setup symlinks for tracked configuration files or
copy them into the right place manually.
The main advantage of such approach is that you are still able to use all git
tools on the dotfiles, such as blame, checkout, log ...
Since homedir usually contains many other files besides configuration worth
tracking, git needs to ignore all files in the working tree with the exception
of config files we actually want to track.

This idea itself is not new, see eg.:

 * [managing dotfiles with git](http://psung.blogspot.com/2008/06/managing-dotfiles-with-git-continued.html) (2008)
 * [profile management with git and github](http://silas.sewell.org/blog/2009/03/08/profile-management-with-git-and-github/) (2009)
 * [managing your configuration files with git and stgit](http://necoro.wordpress.com/2009/10/08/managing-your-configuration-files-with-git-and-stgit) (2009)
 * [config](http://github.com/silas/scripts/blob/master/bin/config)
 * and many others ...

## Example of such setup

To get a better idea what's going on here, let's see how it may work if done
in bash by hand:

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
