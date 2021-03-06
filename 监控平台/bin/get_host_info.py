# -*- coding: utf-8 -*- 
from __future__ import division
import MySQLdb
import sys
import subprocess
import time
import subprocess
import os
import datetime
import random
from fabric.api import env,run,put,get,local
import getopt
import aes 
##  zhou fei 2014-07-28

reload(sys)
sys.setdefaultencoding('gbk')
os.getenv("ORACLE_HOME")
os.getenv("LD_LIBRARY_PATH")
os.getenv("NLS_LANG")
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
import cx_Oracle

#写入数据的配置，包括收集服务器的标记
ywpt_db_conf='/home/mysql/admin/bin/newbin/ywpt_db.conf'
#读取表结构的配置
tmp_ywpt_db_conf='/home/mysql/admin/bin/newbin/tmp_ywpt_db.conf'

#存储写入数据库的配置
monitor_db={}
tmp_monitor_db={}
is_completed='N'
#h_ip=''
#h_type=''
#ip_addr=''
#username=''
#password=''
#hostname=''
#host_id=''
#rootaccount=''
#rootpasswd=''

def main():
    global h_ip,h_type

    try:
        opts, args = getopt.getopt(sys.argv[1:], "Hh:i:t:", ["help", "host_ip=","host_type="])
        if len(sys.argv)==1: 
           usage()
           sys.exit(2)
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    for name,value in opts:
        if name in ("-H","--help"):
           usage()
           sys.exit()
        if name in ("-h","--help"):
           usage()
           sys.exit()
        if name in ("-i","--host_ip"):
           h_ip=value
           print "G_HOST_IP:"+h_ip
        if name in ("-t","--host_type"):
           h_type=value
           print "G_HOST_TYPE:"+h_type
    connect_ssh(h_ip)


def read_conf(conf_file,type):
    file_hand=open(conf_file)
    for line in file_hand:
        line=line.strip()
        (name,value)=line.split(':')
        if type=='ywpt':
            monitor_db[name]=value
        if type=='tmp':
            tmp_monitor_db[name]=value
    file_hand.close()

read_conf(ywpt_db_conf,'ywpt')

mysqldb = MySQLdb.connect(host=monitor_db.get('ip'), user=monitor_db.get('user'),passwd=monitor_db.get('pass'),db=monitor_db.get('db'),port=int(monitor_db.get('port')) ,charset="utf8")
mysqlcur=mysqldb.cursor()

def get_table_column(table_owner,table_name):
    global table_column
    global table_column_mysql
    global var_list
    global table_column_cnt
    read_conf(tmp_ywpt_db_conf,'tmp')
    mysqldbtmp =  MySQLdb.connect(host=tmp_monitor_db.get('ip'), user=tmp_monitor_db.get('user'),passwd=tmp_monitor_db.get('pass'),db=tmp_monitor_db.get('db'),port=int(tmp_monitor_db.get('port')), charset="utf8")
    tmpcur=mysqldbtmp.cursor()
    tmpcur.execute("set names utf8")
    tmpcur.execute("SELECT column_name FROM  COLUMNS WHERE table_name=%s ORDER BY ORDINAL_POSITION",(table_name,))
    data=tmpcur.fetchall()
    table_column=''
    table_column_mysql=''
    table_column_cnt=0
    var_list=''
    for x in data:
       table_column_cnt=table_column_cnt+1
       table_column=table_column+str(x[0])+','
       table_column_mysql=table_column_mysql+'`'+str(x[0])+'`'+','
       var_list=var_list+'%s'+','
    table_column=table_column.rstrip(',')
    table_column_mysql=table_column_mysql.rstrip(',')
    var_list=var_list.rstrip(',')


#取得机器密码
def get_server_pass(t_ip_addr):
    global ip_addr
    global username
    global password
    global hostname,host_id,rootaccount,rootpasswd
    ip_addr=t_ip_addr
    mysqlcur.execute("set names utf8")
    t_sql="select user_account,user_passwd,host_name,host_id,root_account,IFNULL(root_passwd,'GFyBYZKLwVrhDj0Sh5x9uu==') root_passwd from b_host_config where ip_addr=%s limit 1"
    mysqlcur.execute(t_sql,(ip_addr,))
    data = mysqlcur.fetchone()
        #hostname 一定要设对，不然后续获得文件名会出错
    username,password,hostname,host_id,rootaccount,rootpasswd=data
    print rootpasswd
    rootpasswd=aes.jiemi(rootpasswd)



def get_host_quota_collect_day_lastval(t_host_id,quota_id):
    global host_qcdl_lastval_date
    global host_qcdl_lastval
    mysqlcur.execute("select MAX(gmt_created),count(*) from  b_host_quota_collect_day WHERE host_id= %s and quota_id=%s ",(t_host_id,quota_id))
    data=mysqlcur.fetchone()
    dt,cnt=data
    if cnt==0:
       host_qcdl_lastval=0
       host_qcdl_lastval_date='1990-01-01 00:00:00'
    else:
       mysqlcur.execute("select quota_value from b_host_quota_collect_day WHERE host_id= %s and quota_id=%s and gmt_created=%s",(t_host_id,quota_id,dt))
       data= mysqlcur.fetchone()
       host_qcdl_lastval=data[0]
       host_qcdl_lastval_date=dt
    


def insert_data(table_name,varlist):
                get_table_column('sys',table_name)
                mysqlcur.execute("replace into "+table_name+" ("+table_column_mysql+" ) values ("+var_list+")",(varlist))
                mysqldb.commit()


def open_cpu_file(filename):
      global ghc_dt,ghc_time,ghc_user_cpu,ghc_sys_cpu,ghc_io_wait,ghc_idle_cpu,ghc_load5

      conf_file=filename
      file_hand=open(conf_file)
      for line in file_hand:
             line=line.strip()
             (ghc_dt,ghc_time,ghc_user_cpu,ghc_sys_cpu,ghc_io_wait,ghc_idle_cpu,ghc_load5)=line.split(' ')
      file_hand.close()

def open_mem_file(filename):
      global ghc_dt,ghm_os,ghc_time,ghm_total,ghm_used,ghm_free,ghm_buffer,ghm_cache,ghm_s_total,ghm_s_used,ghm_s_free,ghm_s_in,ghm_s_out
      conf_file=filename
      file_hand=open(conf_file)
      for line in file_hand:
             line=line.strip()
             ghm_os=line.split(' ')[0]
             if ghm_os=='Linux':
                (ghm_os,ghc_dt,ghc_time,ghm_total,ghm_used,ghm_free,ghm_buffer,ghm_cache,ghm_s_total,ghm_s_used,ghm_s_free,ghm_s_in,ghm_s_out)=line.split(' ')
             if ghm_os=='AIX':
                (ghm_os,ghc_dt,ghc_time,ghm_total,ghm_used,ghm_free,ghm_s_total,ghm_s_used,ghm_s_free,ghm_s_in,ghm_s_out)=line.split(' ')
                
      file_hand.close()

def open_disk_file(filename):
      conf_file=filename
      file_hand=open(conf_file)
      now=datetime.datetime.now()
      table_name='b_disk_monitor_his'
      ghm_modify=now.strftime('%Y-%m-%d %H:%M:%S')
      #取得id值 传入参数表名，server_id或IP
      tmpid=0
      mysqlcur.callproc('gen_identify',('b_biz_snap',monitor_db.get('hid'),tmpid))
      mysqlcur.execute('select @_gen_identify_2')
      data=mysqlcur.fetchone()
      t_snap_id=data[0]
      g_completed='N'
      for line in file_hand:
            line=line.strip()
            (gdisk_used,gdisk_remain,gdisk_percent,gdisk_name)=line.split(' ')
            t_id=0
            #取得id值 传入参数表名，server_id或IP
            #mysqlcur.callproc('fun_identify_gen',('b_biz_snap',t_id))
            #mysqlcur.execute('select @_fun_identify_gen_2')
            t_id=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
            info=[t_id,t_snap_id,host_id,gdisk_name,gdisk_used,gdisk_remain,gdisk_percent,g_completed,ghm_modify,ghm_modify]
            insert_data(table_name,info) 
      info=[t_snap_id,host_id,'1','1',ghm_modify,ghm_modify]
      insert_data('b_biz_snap',info)


def get_host_cpu():
        put('/home/mysql/admin/bin/newbin/get_cpuinfo.sh','/tmp')
        run('chmod +x /tmp/get_cpuinfo.sh')
        run('/tmp/get_cpuinfo.sh')
        local('rm -rf '+'/tmp/'+ip_addr+'_cpu.txt')
        get('/tmp/'+hostname+'_cpu.txt','/tmp/'+ip_addr+'_cpu.txt')
        conf_file='/tmp/'+ip_addr+'_cpu.txt'
        open_cpu_file(conf_file)
        now=datetime.datetime.now()
        ghc_modify=now.strftime('%Y-%m-%d %H:%M:%S')
        table_name='b_host_quota_collect_day'
 
        get_host_quota_collect_day_lastval(host_id,'1')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'1','cpu_user',ghc_user_cpu,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'2')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'2','cpu_system',ghc_sys_cpu,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'3')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'3','cpu_idle',ghc_idle_cpu,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)
        
        get_host_quota_collect_day_lastval(host_id,'4')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'4','cpu_iowait',ghc_io_wait,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'5')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'5','load5',ghc_load5,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)
       
         
        local('rm -rf '+'/tmp/'+ip_addr+'_cpu.txt')


def get_host_mem():
        put('/home/mysql/admin/bin/newbin/get_meminfo.sh','/tmp') 
        run('chmod +x /tmp/get_meminfo.sh')
        run('/tmp/get_meminfo.sh')
        local('rm -rf '+'/tmp/'+ip_addr+'_mem.txt')
        get('/tmp/'+hostname+'_mem.txt','/tmp/'+ip_addr+'_mem.txt')
        conf_file='/tmp/'+ip_addr+'_mem.txt'
        open_mem_file(conf_file)
        now=datetime.datetime.now()
        ghc_modify=now.strftime('%Y-%m-%d %H:%M:%S')
        table_name='b_host_quota_collect_day'
        get_host_quota_collect_day_lastval(host_id,'6')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'6','mem_total',ghm_total,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'7')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'7','mem_used',ghm_used,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'8')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'8','mem_free',ghm_free,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'100')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'100','mem used per',float(ghm_used)/float(ghm_total),host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)



        get_host_quota_collect_day_lastval(host_id,'9')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'9','swap_total',ghm_s_total,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'10')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'10','swap_used',ghm_s_used,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'11')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'11','swap_free',ghm_s_free,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'101')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'101','swap used per',float(ghm_s_used)/float(ghm_s_total),host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'12')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'12','swap_in',ghm_s_in,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'13')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'13','swap_out',ghm_s_out,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)
    
        if ghm_os=='Linux':
            


             get_host_quota_collect_day_lastval(host_id,'14')
             tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
             info=[tid,host_id,'14','mem_buffer',ghm_buffer,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
             insert_data(table_name,info)

             get_host_quota_collect_day_lastval(host_id,'15')
             tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
             info=[tid,host_id,'15','mem_cached',ghm_cache,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
             insert_data(table_name,info)
        
        local('rm -rf '+'/tmp/'+ip_addr+'_mem.txt')





def open_net_file(filename):
      global ghc_dt,ghc_time,ghc_net_recive,ghc_net_send

      conf_file=filename
      file_hand=open(conf_file)
      for line in file_hand:
             line=line.strip()
             (ghc_dt,ghc_time,ghc_net_recive,ghc_net_send)=line.split(' ')
      file_hand.close()

def get_host_disk():
        put('/home/mysql/admin/bin/newbin/get_diskinfo.sh','/tmp')
        run('chmod +x /tmp/get_diskinfo.sh')
        run('/tmp/get_diskinfo.sh')
        local('rm -rf '+'/tmp/'+ip_addr+'_disk.txt')
        get('/tmp/'+hostname+'_disk.txt','/tmp/'+ip_addr+'_disk.txt')
        conf_file='/tmp/'+ip_addr+'_disk.txt'
        open_disk_file(conf_file)

        local('rm -rf '+'/tmp/'+ip_addr+'_disk.txt')

def  get_host_net():
        put('/home/mysql/admin/bin/newbin/get_netinfo.sh','/tmp')
        run('chmod +x /tmp/get_netinfo.sh')
        run('/tmp/get_netinfo.sh')
        local('rm -rf '+'/tmp/'+ip_addr+'_net.txt')
        get('/tmp/'+hostname+'_net.txt','/tmp/'+ip_addr+'_net.txt')
        conf_file='/tmp/'+ip_addr+'_net.txt'
        open_net_file(conf_file)    
            
        now=datetime.datetime.now()
        ghc_modify=now.strftime('%Y-%m-%d %H:%M:%S')
        table_name='b_host_quota_collect_day'

        get_host_quota_collect_day_lastval(host_id,'16')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'16','net_receive',ghc_net_recive,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        get_host_quota_collect_day_lastval(host_id,'17')
        tid=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
        info=[tid,host_id,'17','net_send',ghc_net_send,host_qcdl_lastval,is_completed,ghc_dt+' '+ghc_time,ghc_modify,host_qcdl_lastval_date]
        insert_data(table_name,info)

        local('rm -rf '+'/tmp/'+ip_addr+'_net.txt')

def get_host_summary():
        hosttype=run("uname -a |awk '{print $1}'")
        hostname=run("hostname")
        hostip=ip_addr
        if hosttype=='AIX':
           memtotal=run("svmon -G -O unit=MB|grep memory|awk '{print $2}'")
           run("prtconf|grep 'Processor'>/tmp/cputt.txt")
           cpunum=run("cat /tmp/cputt.txt|grep 'Number Of Processors'|awk '{print $4}'")
           cpulgnum=run("pmcycles -m|wc -l")
           cpuhz=run("cat /tmp/cputt.txt|egrep 'Processor Clock Speed'|awk '{print $4$5}'")
           cpumode=run("cat /tmp/cputt.txt|egrep 'Processor Type'|awk '{print $3}'")
           osnh=run("lsattr -El sys0|grep  modelname|awk '{print $2}'")

           print "tyydjk:Mem Total:"+memtotal+"MB"
           print "tyydjk:Host Type:"+hosttype
           print "tyydjk:Host Name:"+hostname
           print "tyydjk:Host Ip:"+hostip
           print "tyydjk:Cpu num:"+cpunum
           print "tyydjk:cpu lg num:"+cpulgnum
           print "tyydjk:cpu hz:"+cpuhz
           print "tyydjk:cpu mode:"+cpumode
           print "tyydjk:os nh:"+osnh
           run("rm -rf /tmp/cputt.txt")  
        if hosttype=='Linux':   
           memtotal=run("cat /proc/meminfo |grep MemTotal|awk '{print $2$3}'")
           cpunum=run("cat /proc/cpuinfo |grep 'physical id'|sort|uniq|wc -l")
           cpulgnum=run("cat /proc/cpuinfo |grep 'processor'|wc -l ")
           cpuhz=run("cat /proc/cpuinfo|grep 'cpu MHz'|uniq|awk '{print $4}'")+"Mhz"
           cpumode=run("cat /proc/cpuinfo |grep 'model name'|uniq|awk '{print $4 $5 $6 $7 $8}'")
           osnh=run("uname -a|awk '{print $3}'")
           print "tyydjk:Mem Total:"+memtotal
           print "tyydjk:Host Type:"+hosttype
           print "tyydjk:Host Name:"+hostname
           print "tyydjk:Host Ip:"+hostip
           print "tyydjk:Cpu num:"+cpunum
           print "tyydjk:cpu lg num:"+cpulgnum
           print "tyydjk:cpu hz:"+cpuhz
           print "tyydjk:cpu mode:"+cpumode
           print "tyydjk:os nh:"+osnh

def open_ssd_file(filename):
      conf_file=filename
      file_hand=open(conf_file)
      now=datetime.datetime.now()
      table_name='b_disk_ssd_info'
      ghm_modify=now.strftime('%Y-%m-%d %H:%M:%S')
      #取得id值 传入参数表名，server_id或IP
      g_completed='N'
      for line in file_hand:
            line=line.strip()
            (tdisk_type,tdisk_path,t_device_id,t_disk_stat)=line.split('|')
            t_id=monitor_db.get('hid')+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+str(random.randint(10000,90000))
            (tt,tdisk_path)=tdisk_path.split(':')
            (tt,t_device_id)=t_device_id.split(':')
            (tt,tdisk_type)=tdisk_type.split(':')
            (tt,t_disk_stat)=t_disk_stat.split(':')

            info=[t_id,host_id,tdisk_path,t_device_id,tdisk_type,t_disk_stat,g_completed,ghm_modify,ghm_modify]
            insert_data(table_name,info)

def  get_host_ssd():
        put('/home/mysql/admin/bin/newbin/get_ssd_stat.sh','/tmp')
        run('chmod +x /tmp/get_ssd_stat.sh')
        run('/tmp/get_ssd_stat.sh')
        local('rm -rf '+'/tmp/'+ip_addr+'_ssd.txt')
        get('/tmp/'+hostname+'_ssd.txt','/tmp/'+ip_addr+'_ssd.txt')
        conf_file='/tmp/'+ip_addr+'_ssd.txt'
        open_ssd_file(conf_file)


        local('rm -rf '+'/tmp/'+ip_addr+'_ssd.txt')


def connect_ssh(g_ip):
    host_ip=g_ip
    #根据传入IP取得对应服务器访问的账号等信息
    get_server_pass(host_ip)
    if h_type=='ssd':
       env.user=rootaccount
       env.password = rootpasswd
    else:
       env.user=username
       env.password = password

    env.host_string=ip_addr+':22'
    if h_type=='cpu':
            get_host_cpu() 
    if h_type=='mem':
            get_host_mem() 
    if h_type=='disk':
            get_host_disk()
    if h_type=='net':
            get_host_net()
    if h_type=='summary':
            get_host_summary()
    if h_type=='ssd':
            get_host_ssd()

#if __name__=="__main__":
#       h_ip=sys.argv[1]   #访问主机ip
#       h_type=sys.argv[2]  #主机上要获得的数据类型 'cpu','mem','net','disk'等
#
#       connect_ssh(h_ip)


def usage():
    print '''
---------------usage:------------------
python get_host_info_new.py -i ip -t type (cpu,mem,disk,net,summary)
or
python get_host_info_new.py --host_ip=ip --host_type=(cpu,mem,disk,net,summary)
---------------------------------------
'''

if __name__=="__main__":
   main()

