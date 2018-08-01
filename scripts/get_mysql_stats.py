#coding=utf-8
#encoding:utf8

import MySQLdb
import os
import re
import argparse



parser = argparse.ArgumentParser()
parser.add_argument("--servicehost", action="store", dest='servicehost', help="input the database servcie host", required=True)
parser.add_argument("--serviceport", action="store", dest='serviceport', type=int, help="input the database service port", required=True)
parser.add_argument("--username", action="store", dest='username', help="input the monitor user name for database", required=True)
parser.add_argument("--password", action="store", dest='password', help="input the user's password", required=True)
args = parser.parse_args()


SERVICEHOST=args.servicehost
SERVICEPORT=args.serviceport
USERNAME=args.username
PASSWORD=args.password


def get_mysql_status(SERVICEHOST,SERVICEPORT,querysql):
    try:
        conn = MySQLdb.connect(host=SERVICEHOST, port=SERVICEPORT, user=USERNAME, passwd=PASSWORD,db='',charset="utf8")
    except Exception, e:
        print e
        os._exit()
    try:
        cursor = conn.cursor()
        cursor.execute(querysql)
        result = cursor.fetchall()
        return result
    except Exception, e:
        print e
    cursor.close()
    conn.close()

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
 
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False

def increment(statusdic, key, howmuch):
    if (statusdic.has_key(key)):
        statusdic[key]=statusdic[key]+howmuch
        return statusdic
    else:
        statusdic[key]=howmuch
        return statusdic

def to_float(rownum):
    rownum = re.findall('[\d+\.\d]*',rownum)
    return float(rownum[0])
    
def to_int(rownum):
    rownum = re.findall('[-+?\d+\.\d]*',rownum)
    return int(float(rownum[0]))

def get_resaultdic():
    txn_seen=False
    prev_line=''
    resaultdic={}
 
    resaults=get_mysql_status(SERVICEHOST,SERVICEPORT,'show slave status;')
    # Scale slave_running and slave_stopped relative to the slave lag.
    for resault in resaults:
        if(resault[0]=='Slave_IO_Running' and resault[1]=='Yes'):
            resaultdic[u'Slave_IO_Running']=1
        else:
            resaultdic[u'Slave_IO_Running']=0
        
        if(resault[0]=='Slave_SQL_Running' and resault[1]=='Yes'):
            resaultdic[u'Slave_SQL_Running']=1
        else:
            resaultdic[u'Slave_SQL_Running']=0
        
        if (resault[0]=='Seconds_Behind_Master' and resaultdic[u'Slave_IO_Running']==1 and resaultdic[u'Slave_SQL_Running']==1):
            resaultdic[u'slave_lag']=resault[1]
        else:
            resaultdic[u'slave_lag']=-1

    resaults=get_mysql_status(SERVICEHOST,SERVICEPORT,'show variables;')
    for resault in resaults:
        if(resault[0]=='max_connections'):
            resaultdic[u'max_connections']=resault[1]    
        if(resault[0]=='innodb_log_buffer_size'):
            resaultdic[u'innodb_log_buffer_size']=resault[1]
        if(resault[0]=='key_buffer_size'):
            resaultdic[u'key_buffer_size']=resault[1]            
        if(resault[0]=='key_cache_block_size'):
            resaultdic[u'key_cache_block_size']=resault[1]    
        if(resault[0]=='query_cache_size'):
            resaultdic[u'query_cache_size']=resault[1] 
        if(resault[0]=='table_open_cache'):
            resaultdic[u'table_open_cache']=resault[1]  
        if(resault[0]=='thread_cache_size'):
            resaultdic[u'thread_cache_size']=resault[1] 
                            
    resaults=get_mysql_status(SERVICEHOST,SERVICEPORT,'show global status;')
    for resault in resaults:
        if ( is_number(resault[1])):
            resaultdic[resault[0]]=to_int(resault[1])
    
    resaults2=get_mysql_status(SERVICEHOST,SERVICEPORT,'show engine innodb status;')
    lines=resaults2[0][2].split("\n")
    for line in lines:
        line=line.strip()
        row=' '.join(line.split())
        row= row.split()
        if (line.find("Mutex spin waits") == 0):
            # Mutex spin waits 79626940, rounds 157459864, OS waits 698719
            resaultdic[u'Mutex-spin_waits']=to_int(row[3])
            resaultdic[u'Mutex-spin_rounds']=to_int(row[5])
            resaultdic[u'Mutex-os_waits']=to_int(row[8])
        elif (line.find("RW-shared spins") == 0 and line.find(";") > 0):
            # RW-shared spins 3859028, OS waits 2100750; RW-excl spins 4641946, OS waits 1530310
            resaultdic[u'RW-shared-spin_waits']=to_int(row[2])
            resaultdic[u'RW-shared-os_waits']=to_int(row[5])
            resaultdic[u'RW-excl-spin_waits']=to_int(row[8])
            resaultdic[u'RW-excl-os_waits']=to_int(row[11])
        elif (line.find("RW-shared spins") == 0 and line.find("; RW-excl spins") < 0):
            # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
            # RW-shared spins 604733, rounds 8107431, OS waits 241268
            resaultdic[u'RW-shared-spin_waits']=to_int(row[2])
            resaultdic[u'RW-shared-spin_rounds']=to_int(row[4])
            resaultdic[u'RW-shared-os_waits']=to_int(row[7])
        elif (line.find("RW-excl spins") == 0):
            # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
            # RW-excl spins 604733, rounds 8107431, OS waits 241268
            resaultdic[u'RW-excl-spin_waits']=to_int(row[2])
            resaultdic[u'RW-excl-spin_rounds']=to_int(row[4])
            resaultdic[u'RW-excl-os_waits']=to_int(row[7])
        elif (line.find("seconds the semaphore:") > 0):
            # --Thread 907205 has waited at handler/ha_innodb.cc line 7156 for 1.00 seconds the semaphore:
            resaultdic=increment(resaultdic,u'innodb_sem_waits',1)
            resaultdic=increment(resaultdic,u'innodb_sem_wait_time_ms',to_int(str(to_float(row[9])*1000)))
        elif (line.find("Trx id counter") == 0):
            # --Thread 907205 has waited at handler/ha_innodb.cc line 7156 for 1.00 seconds the semaphore:
            resaultdic[u'innodb_transactions']=to_int(row[3])
            txn_seen=True
        elif(line.find("Purge done for trx") == 0):
            #Purge done for trx's n:o < 2807498 undo n:o < 0 state: running but idle
            resaultdic[u'purged_txns']=to_int(row[6])
            resaultdic[u'unpurged_txns']=to_int(row[10])
        elif(line.find("History list length") == 0):
            # History list length 132
            resaultdic[u'history_list']=to_int(row[3])
        elif( txn_seen and line.find("---TRANSACTION") == 0):
            resaultdic=increment(resaultdic,u'current_transactions',1)
            if(line.find("ACTIVE") > 0):
                resaultdic=increment(resaultdic,u'active_transactions',1)
        elif( txn_seen and line.find("------- TRX HAS BEEN") == 0):
            # ------- TRX HAS BEEN WAITING 32 SEC FOR THIS LOCK TO BE GRANTED:
            resaultdic=increment(resaultdic,u'innodb_lock_wait_secs',to_int(row[5]))
        elif( line.find("read views open inside InnoDB") > 0 ):
            # 1 read views open inside InnoDB
            resaultdic[u'read_views']=to_int(row[0])
        elif( line.find("mysql tables in use") == 0 ):
            # mysql tables in use 2, locked 2
            resaultdic[u'innodb_tables_in_use']=to_int(row[4])
            resaultdic[u'innodb_locked_tables']=to_int(row[6])
        elif( txn_seen and line.find("lock struct(s)") > 0):
            # 23 lock struct(s), heap size 3024, undo log entries 27
            # LOCK WAIT 12 lock struct(s), heap size 3024, undo log entries 5
            # LOCK WAIT 2 lock struct(s), heap size 368
            if(line.find("LOCK WAIT")==0):
                resaultdic=increment(resaultdic,u'innodb_lock_structs',to_int(row[2]))
                resaultdic=increment(resaultdic,u'locked_transactions',1)
            else:
                resaultdic=increment(resaultdic,u'locked_transactions',to_int(row[0]))
        elif(line.find(" OS file reads, ")>0):
            # 8782182 OS file reads, 15635445 OS file writes, 947800 OS fsyncs
            resaultdic[u'file_reads']=to_int(row[0])
            resaultdic[u'file_writes']=to_int(row[4])
            resaultdic[u'file_fsyncs']=to_int(row[8])
        elif(line.find("Pending normal aio reads:")==0):
            # Pending normal aio reads: 0, aio writes: 0,
            resaultdic[u'pending_normal_aio_reads']=to_int(row[4])
            resaultdic[u'pending_normal_aio_writes']=to_int(row[7])
        elif(line.find("ibuf aio reads")==0):
            #  ibuf aio reads: 0, log i/o's: 0, sync i/o's: 0
            resaultdic[u'pending_ibuf_aio_reads']=to_int(row[3])
            resaultdic[u'pending_aio_log_ios']=to_int(row[6])
            resaultdic[u'pending_aio_sync_ios']=to_int(row[9])  
        elif(line.find("Pending flushes (fsync)")==0):
            # Pending flushes (fsync) log: 0; buffer pool: 0
            resaultdic[u'pending_log_flushes']=to_int(row[4])
            resaultdic[u'pending_buf_pool_flushes']=to_int(row[7])
        # INSERT BUFFER AND ADAPTIVE HASH INDEX
        elif(line.find("Ibuf for space 0: size ")==0):
            # Older InnoDB code seemed to be ready for an ibuf per tablespace.  It
            # had two lines in the output.  Newer has just one line, see below.
            # Ibuf for space 0: size 1, free list len 887, seg size 889, is not empty
            # Ibuf for space 0: size 1, free list len 887, seg size 889,
            resaultdic[u'ibuf_used_cells']=to_int(row[5])
            resaultdic[u'ibuf_free_cells']=to_int(row[9])
            resaultdic[u'ibuf_cell_count']=to_int(row[12])
        elif(line.find("Ibuf: size ")==0):
            # Ibuf: size 1, free list len 4634, seg size 4636,
            resaultdic[u'ibuf_used_cells']=to_int(row[2])
            resaultdic[u'ibuf_free_cells']=to_int(row[6])
            resaultdic[u'ibuf_cell_count']=to_int(row[9])
            if(line.find("merges")):
                resaultdic[u'ibuf_merges']=to_int(row[10])
        elif(line.find(", delete mark ")>0 and prev_line.find("merged operations:")==0):
            # Output of show engine innodb status has changed in 5.5
            # merged operations:
            # insert 593983, delete mark 387006, delete 73092
            resaultdic[u'ibuf_inserts']=to_int(row[1])
            resaultdic[u'ibuf_merged']=to_int(row[1]) + to_int(row[4]) + to_int(row[6]) 
        elif(line.find(" merged recs, ")==0):
            # 19817685 inserts, 19817684 merged recs, 3552620 merges
            resaultdic[u'ibuf_inserts']=to_int(row[0])
            resaultdic[u'ibuf_merged']=to_int(row[2])
            resaultdic[u'ibuf_merges']=to_int(row[5])
        elif(line.find("Hash table size ")==0):
            # In some versions of InnoDB, the used cells is omitted.
            # Hash table size 4425293, used cells 4229064, ....
            # Hash table size 57374437, node heap has 72964 buffer(s) <-- no used cells
            resaultdic[u'hash_index_cells_total']=to_int(row[3])
            if(line.find("used cells")>0):
                resaultdic[u'hash_index_cells_used']=to_int(row[6])
            else:
                resaultdic[u'hash_index_cells_used']=0
        # LOG
        elif(line.find(" log i/o's done, ")>0):
            # 3430041 log i/o's done, 17.44 log i/o's/second
            # 520835887 log i/o's done, 17.28 log i/o's/second, 518724686 syncs, 2980893 checkpoints
            # TODO: graph syncs and checkpoints
            resaultdic[u'log_writes']=to_int(row[0])
        elif(line.find(" pending log writes, ")>0):
            # 0 pending log writes, 0 pending chkp writes
            resaultdic[u'pending_log_writes']=to_int(row[0])
            resaultdic[u'pending_log_writes']=to_int(row[4])
        elif(line.find("Log sequence number")==0):
            # This number is NOT printed in hex in InnoDB plugin.
            # Log sequence number 13093949495856 //plugin
            # Log sequence number 125 3934414864 //normal
            try:
                row[4]
                resaultdic[u'log_bytes_written']=to_int(row[3]) + to_int(row[4])
            except IndexError:
                resaultdic[u'log_bytes_written']=to_int(row[3])
        elif(line.find("Log flushed up to")==0):
            # This number is NOT printed in hex in InnoDB plugin.
            # Log flushed up to   13093948219327
            # Log flushed up to   125 3934414864
            try:
                row[5]
                resaultdic[u'log_bytes_flushed']=to_int(row[4]) + to_int(row[5])
            except IndexError:
                resaultdic[u'log_bytes_flushed']=to_int(row[4])
        elif(line.find("Last checkpoint at")==0):
            # Last checkpoint at  125 3934293461
            try:
                row[4]
                resaultdic[u'last_checkpoint']=to_int(row[3]) + to_int(row[4])
            except IndexError:
                resaultdic[u'last_checkpoint']=to_int(row[3])
        # BUFFER POOL AND MEMORY
        elif(line.find("Total memory allocated")==0 and line.find("in additional pool allocated")>0):
            # Total memory allocated 29642194944; in additional pool allocated 0
            # Total memory allocated by read views 96
            resaultdic[u'total_mem_alloc']=to_int(row[3])
            resaultdic[u'additional_pool_alloc']=to_int(row[8])
        elif(line.find("Adaptive hash index ")==0):
            #   Adaptive hash index 1538240664     (186998824 + 1351241840)
            resaultdic[u'adaptive_hash_memory']=to_int(row[3])
        elif(line.find("Page hash           ")==0):
            #   Page hash           11688584
            resaultdic[u'page_hash_memory']=to_int(row[2])
        elif(line.find("Dictionary cache    ")==0):
            #   Dictionary cache    145525560     (140250984 + 5274576)
            resaultdic[u'dictionary_cache_memory']=to_int(row[2])
        elif(line.find("File system         ")==0):
            #   File system         313848     (82672 + 231176)
            resaultdic[u'file_system_memory']=to_int(row[2])
        elif(line.find("Lock system         ")==0):
            #   Lock system         29232616     (29219368 + 13248)
            resaultdic[u'lock_system_memory']=to_int(row[2])
        elif(line.find("Recovery system     ")==0):
            #   Recovery system     0     (0 + 0)
            resaultdic[u'recovery_system_memory']=to_int(row[2])        
        elif(line.find("Threads            ")==0):
            #   Threads             409336     (406936 + 2400)
            resaultdic[u'thread_hash_memory']=to_int(row[1])  
        elif(line.find("innodb_io_pattern   ")==0):
            #   innodb_io_pattern   0     (0 + 0)
            resaultdic[u'innodb_io_pattern_memory']=to_int(row[1])
        elif(line.find(" queries inside InnoDB, ")>0):
            # 0 queries inside InnoDB, 0 queries in queue
            resaultdic[u'queries_inside']=to_int(row[0])
            resaultdic[u'queries_queued']=to_int(row[4])
        prev_line = line
    
    resaultdic[u'unflushed_log']=resaultdic[u'log_bytes_written']+resaultdic[u'log_bytes_flushed']
    resaultdic[u'uncheckpointed_bytes']=resaultdic[u'log_bytes_written']+resaultdic[u'last_checkpoint']
    
    return resaultdic
    """
        elif(line.find("Buffer pool size   ")==0):
            # The " " after size is necessary to avoid matching the wrong line:
            # Buffer pool size        1769471
            # Buffer pool size, bytes 28991012864
            if(not resaultdic.has_key('pool_size')):
                resaultdic[u'pool_size']=to_int(row[3])
        elif(line.find("Free buffers")==0):
            # Free buffers            0
            if(not resaultdic.has_key('free_pages')):
                resaultdic[u'free_pages']=to_int(row[2])         
        elif(line.find("Database pages")==0):
            # Database pages          1696503
            if(not resaultdic.has_key('database_pages')):
                resaultdic[u'database_pages']=to_int(row[2])
        elif(line.find("Modified db pages")==0):
            # Modified db pages       160602
            if(not resaultdic.has_key('modified_pages')):
                resaultdic[u'modified_pages']=to_int(row[3])
        elif(line.find("Pages read ahead")==0):
            # Must do this BEFORE the next test, otherwise it'll get fooled by this
            # line from the new plugin (see samples/innodb-015.txt):
            #Pages read ahead 0.00/s, evicted without access 0.00/s, Random read ahead 0.00/s
            # TODO: No-op for now, see issue 134.
            continue
        elif(line.find("Pages read")==0):
            # Pages read 15240822, created 1770238, written 21705836
            if(not resaultdic.has_key('pages_read')):
                resaultdic[u'pages_read']=to_int(row[2])
                resaultdic[u'pages_created']=to_int(row[4])
                resaultdic[u'pages_written']=to_int(row[6])
        # ROW OPERATIONS
        elif(line.find("Number of rows inserted")==0):
            # Number of rows inserted 50678311, updated 66425915, deleted 20605903, read 454561562
            resaultdic[u'rows_inserted']=to_int(row[4])
            resaultdic[u'rows_updated']=to_int(row[6])
            resaultdic[u'rows_deleted']=to_int(row[8])
            resaultdic[u'rows_read']=to_int(row[10])
    """

def writetofile(resaultdic):
    f1 = open('D:/'+SERVICEHOST+'-'+str(SERVICEPORT)+'-status.txt', 'w')
    for key in resaultdic.keys():
        f1.writelines( ' '+key +':'+ str(resaultdic[key])+'\n')
    
 
def main():
    resaultdic=get_resaultdic()
    writetofile(resaultdic)
    
    
    
if __name__=='__main__':
    main()   
