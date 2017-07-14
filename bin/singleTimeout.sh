#!/bin/bash

# check command line
while getopts t:c:f:m:gv opt; do
    case $opt in
        t)  
            TIMEOUT=$OPTARG
            ;;
        c)  
            COMMAND=$OPTARG
            ;;
        g)  
            KILL_GROUP=1
            ;;
        m)  
            MAILTO=$OPTARG
            ;;
        f)  
            LOCKFILE=$OPTARG
            ;;
        v)  
            VERBOSE=1
    esac
done

if [  "X$TIMEOUT" = X -o "X$COMMAND" = X ]; then
    cat <<EoF
Usage: $0 [-g] [-v]  -t <timeout in seconds> [ -m <email addr>] [ -f <lockfile> ] -c <command>"

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
EoF
    exit 1
fi

if [ X$LOCKFILE != X ]; then
    LOCKFILEARG="-f $LOCKFILE"
fi

OUT=`single.py --status $LOCKFILEARG -c $COMMAND`

# not locked, exit
if [ $? = 0 ]; then
    if [ X$VERBOSE != X ]; then
        echo "Process not running"
    fi
    exit 0
fi

PID=`echo $OUT | awk '{print$3}' | sed -e 's/:$//'`
if [ "$(uname)" == "Darwin" ]; then
    T=`ps -p $PID -o etime=`
    TIME=`echo $T | awk -F'[-:]' '{ if (NF > 1) { \
                                      t=$(NF) + $(NF-1) * 60; \
                                      if (NF > 2) { t += $(NF-2) * 3600 } \
                                      if (NF > 3) { t += $(NF-3) * 86400 } \
                                      print t} \
                                  }'`
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    TIME=`ps -p $PID -o etimes= | xargs`
else
    echo "I've only been tested on Mac and Linux. Sorry, I don't know what to do with $(uname)"
    exit 1
fi

# not stale exit
if (( $TIME < $TIMEOUT )) ; then
    if [ X$VERBOSE != X ]; then
        echo "Process not stale. ($TIME < $TIMEOUT)"
    fi
    exit 0
fi

OUT_MSG="Command running too long, killing it. ($TIME > $TIMEOUT)"
echo $OUT_MSG
if [ X$VERBOSE != X ]; then
    echo `ps -fp $PID | sed -e 's/$/\\n/'`
fi
if [ X$KILL_GROUP != X ]; then
    GPID=`ps  -o  "pgid=" -p $PID`
    kill -9 -$GPID
else
    kill -9 $PID
fi

if [ X$LOCKFILE != X ]; then
    rm $LOCKFILE
fi

if [ X$MAILTO != X ]; then
    echo -e $OUT_MSG | mailx -s "stale proc: $COMMAND" $MAILTO
fi
