#!/bin/sh
# The wrapper for zabbix python script.
# It runs the script every 5 min. and parses the cache file on each following run.
# Authors: earl86

USERNAME=zabbix
PASSWORD=zabbix

SERVICEHOST=$1
SERVICEPORT=$2
ITEM=$3

DIR=`dirname $0`

CMD="/usr/bin/python $DIR/get_mysql_stats.py --servicehost $SERVICEHOST --serviceport $SERVICEPORT --username $USERNAME--password $PASSWORD"
CACHEFILE="/tmp/$SERVICEHOST-$SERVICEPORT-mysql_zabbix_stats.txt"

if [ "$ITEM" = "mysqld_alive" ]; then
    RES=`HOME=~zabbix mysql -h $SERVICEHOST -P $SERVICEPORT -u$USERNAME -p$PASSWORD -N -e 'select 1 from dual;' 2>/dev/null`
    if [ "$RES" = "1" ]; then
        echo 1
    else
        echo 0
    fi
    exit
elif [ "$ITEM" = "slave_running" ]; then
    # Check for running slave
    RES=`HOME=~zabbix mysql -h $SERVICEHOST -P $SERVICEPORT -u$USERNAME -p$PASSWORD -e 'SHOW SLAVE STATUS\G' | egrep '(Slave_IO_Running|Slave_SQL_Running):' | awk -F: '{print $2}' | tr '\n' ','`
    if [ "$RES" = " Yes, Yes," ]; then
        echo 1
    else
        echo 0
    fi
    exit
elif [ -e $CACHEFILE ]; then
    # Check and run the script
    #TIMEFLM=`stat -c %Y /tmp/$SERVICEHOST-$SERVICEPORT-mysql_zabbix_stats.txt`
    TIMEFLM=`stat -c %Y $CACHEFILE`
    TIMENOW=`date +%s`
    if [ `expr $TIMENOW - $TIMEFLM` -gt 300 ]; then
        rm -f $CACHEFILE
        $CMD 2>&1 > /dev/null
    fi
else
    $CMD 2>&1 > /dev/null
fi

# Parse cache file
if [ -e $CACHEFILE ]; then
    cat $CACHEFILE | grep ' $ITEM:' | awk -F: '{print $2}'
else
    echo "ERROR: run the command manually to investigate the problem: $CMD"
fi

