Command line tools
==================

downloader
^^^^^^^^^^

Download a file of HTTP or HTTPS, in concurrent segments if supported by the remote server. Usage::

    usage: downloader [-h] [-r RETRIES] [-n NUM_CON] [-s SEG_SIZE] [-v] url

    Provides a console interface for downloading a file, possibly in segments.

    positional arguments:
      url                   URL of file to download.

    optional arguments:
      -h, --help            show this help message and exit
      -r RETRIES, --retries RETRIES
                            Maximum number of attemps to fulfill request
      -n NUM_CON, --num-con NUM_CON
                            Maximum number of concurrent requests to the remote
                            server
      -s SEG_SIZE, --seg-size SEG_SIZE
                            Largest file size, in bytes, that will not trigger
                            segmenting.
      -v, --verbose         Verbose logging


mattermost.py
^^^^^^^^^^^^^

Interact with a mattermost server. Usage::

    usage: mattermost [-h] [-a ATTACHMENTS] [-r RETRIES] [-t TIMEOUT]
                      [--team-name TEAM_NAME] [--channel-name CHANNEL_NAME] [-v]
                      {post,getteams,getchannels}

    Interact with a Mattermost server. Not all possible combinations of arguments
    will make sense, avoid those that do not make sense. The message to post, if
    any, will be read from <STDIN>.

    positional arguments:
      {post,getteams,getchannels}
                            Command

    optional arguments:
      -h, --help            show this help message and exit
      -a ATTACHMENTS, --attachments ATTACHMENTS
                            File to attach. Argument may be repeated to attach
                            multiple files.
      -r RETRIES, --retries RETRIES
                            Maximum number of attemps to fulfill request
      -t TIMEOUT, --timeout TIMEOUT
                            request timeout
      --team-name TEAM_NAME
                            Mattermost team name. Will override MATTERMOST_TEAM_ID
                            environment variable.
      --channel-name CHANNEL_NAME
                            Mattermost channel name. Will override
                            MATTERMOST_CHANNEL_ID environment variable.
  -v, --verbose         Verbose logging


singleTimeout.sh
^^^^^^^^^^^^^^^^

Kill a job started with single.py if it has been running too long. Usage::

    Usage: ./singleTimeout.sh [-g] [-v]  -t <timeout in seconds> [ -m <email addr>] [ -f <lockfile> ] -c <command>"

    Kill a long-running job started with single.py.

    required arguments:
      -c COMMAND              Command as passed to single.py
      -t TIMEOUT              Time, in seconds, job is allowed to run

    optional arguments:
      -f LOCKFILE             Path to the lock file. If not specified, use the
                              default. If a lockfile is provided and the job has
                              been running too long, I will attempt to remove the
                              lockfile after killing the job.
      -m ADDRESS              Address to email when a job is killed
      -g                      Kill job by group id rather than process id
      -v                      Print more stuff
