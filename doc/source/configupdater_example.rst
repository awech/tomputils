******************
configupdater.yaml
******************
.. _configupdater.yaml:

File Format
===========
The configupdater configuration file is written in `YAML <http://www.yaml.org/>`_ 1.2. The file consists of a sequqnce node containing a seried of config items to keep track of. The config items are processed in order and it's premissible for a later item to reference an earlier item.

Config Nodes
============
Each config item is presented as a mapping node, continaing a name, a type, and other keys depending on the type.

svndir
------
The svndir type is used to keep track of a collection of files stored in a remote svn repository. Keys:
  * name - a name for this collection
  * type - svndir
  * source - URL of SVN repo
  * target - Local directory where files will be stored
  * user - username to pass to SVN server
  * password - password to pass to SVN server

localfile
---------
The localfile type is used to keep track of a local file. It can be used in conjuntion with svndir to report file-level changes.
If the file has a yaml extension, changes to the remote file will be validated before the working config is updated.
Keys:
  * name - a name for this collection
  * type - localfile
  * source - local path to source file
  * target - local path to working file

remotefile
----------
The remotefile type is used to keep track of a single file stored on a remote server.
If the file has a yaml extension, changes to the remote file will be validated before the working config is updated.
Keys:
  * name - a name for this file
  * type - remotefile
  * source - URL of remote file 
  * target - Local directory where file will be stored
  * user - username to pass to remote server
  * password - password to pass to remote server

Example file::

    configs:
      - name: Config assets
        type: svndir
        source: https://host.wr.usgs.gov/svn/exampleproject
        target: /tmp/camcommander/svn
        user: exampleusername
        passwd: examplepassword

      - name: webrelaypoker.yaml
        type: localfile
        source: /tmp/camcommander/svn/webrelaypoker.yaml
        target: /tmp/comcommander/webrelaypoker.yaml
