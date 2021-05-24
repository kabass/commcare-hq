#!/bin/bash
# TODO convert to using docker compose'depends_on' feature with health checks

set -e

if [ -f /mnt/commcare-hq-ro/scripts/bash-utils.sh ]; then
    source /mnt/commcare-hq-ro/scripts/bash-utils.sh # provides logmsg
else
    # if bash-utils.sh is not where we expect it, stub out logmsg (allows this
    # script to be used outside the docker environment).
    function logmsg { echo "$@"; }
fi

if [ -n "$1" ]; then
    # always use argv if provided
    SERVICES="$1"
elif [ -n "$DEPENDENT_SERVICES" ]; then
    # otherwise use DEPENDENT_SERVICES (if present)
    SERVICES="$DEPENDENT_SERVICES"
else
    logmsg ERROR "No services to wait for!"
    exit 1
fi

logmsg INFO "Waiting for services: $SERVICES"

for service in $SERVICES; do
    svc=$(echo $service | cut -d : -f 1)
    port=$(echo $service | cut -d : -f 2)

    logmsg -n INFO "Waiting for TCP connection to $svc:$port..."

    counter=0
    while ! { exec 6<>/dev/tcp/${svc}/${port}; } 2>/dev/null
    do
      echo -n . >&2  # append dot to most recent log line
      sleep 1
      let counter=counter+1
      if [ $counter -gt 90 ]; then
        echo " TIMEOUT" >&2  # finalize log line
        exit 1
      fi
    done

    echo " $svc ok" >&2  # finalize log line
done

logmsg INFO "Services ready!"
