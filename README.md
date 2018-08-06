# zabbix-mysql-multi Template and Scripts for zabbix 3.x

require：
python 2+

mysql 所在服务器 只需要安装zabbix-agent 只需要安装相关监控脚本及python 运行环境 即可，无需其他配置。记得修改get_mysql_stats_wrapper.sh里面的用户名及密码

/etc/zabbix/zabbix_agentd.d/userparameter_mysql.conf


/etc/zabbix/scripts/get_mysql_stats_wrapper.sh


/etc/zabbix/scripts/get_mysql_stats.py

测试方法：

zabbix_get -s agent服务ip -p 10050 -k "MySQL[mysql服务ip,3306,Threads_connected]"


