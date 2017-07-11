#!/bin/bash

WHO=tparker@usgs.gov
VERBOSE=0


convert_mac() {
   echo 2-01:11:18 | awk -F'[-:]' '{if (NF > 1) {t=$(NF) + $(NF-1) * 60; if (NF > 2) { t += $(NF-2) * 3600 } if (NF > 3) { t += $(NF-3) * 86400 } print t}}'
}

# check command line
while getopts t:c:f:v opt; do
    case $opt in
        t)  
            TIMEOUT=$OPTARG
            ;;
        c)  
            COMMAND=$OPTARG
            ;;
        f)  
            LOCKFILE=$OPTARG
            ;;
        v)  
            VERBOSE=1
    esac
done

if [  "X$TIMEOUT" = X -o "X$COMMAND" = X ]; then
    echo "Usage: $0 -t <timeout in seconds> -c <command> [ -f <lockfile> ]"
    exit 1
fi

if [ X$LOCKFILE != X ]; then
    LOCKFILEARG="-f $LOCKFILE"
fi

OUT=`single.py --status $LOCKFILEARG -c $COMMAND`

# not locked, exit
if [ $? = 0 ]; then
    if [ $VERBOSE = 1 ]; then
        echo "Process not running"
    fi
    exit 0
fi

PID=`echo $OUT | awk '{print$3}' | sed -e 's/:$//'`
if [ "$(uname)" == "Darwin" ]; then
    T=`ps -p $PID -o etime=`
    TIME=`echo $T | awk -F'[-:]' '{if (NF > 1) { t=$(NF) + $(NF-1) * 60; \
                                                if (NF > 2) { t += $(NF-2) * 3600 } \
                                                if (NF > 3) { t += $(NF-3) * 86400 } \
                                                print t}}'`
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    TIME=`ps -p $PID -o etimes= | xargs`
else
    echo "I've only been tested on Mac and Linux. Sorry, I don't know what to do with $(uname)"
    exit 1
fi

# not stale exit
if (( $TIME < $TIMEOUT )) ; then
    if [ $VERBOSE = 1 ]; then
        echo "Process not stale. ($TIME < $TIMEOUT)"
    fi
    exit 0
fi

OUT_MSG="Command running too long, killing it. ($TIME > $TIMEOUT)\n"
OUT_MSG+=`ps -fp $PID | sed -e 's/$/\\n/'`
kill -9 $PID

if [ $VERBOSE = 1 ]; then
    echo -e $OUT_MSG
fi
echo -e $OUT_MSG | mailx -s "stale proc: $COMMAND" $WHO

