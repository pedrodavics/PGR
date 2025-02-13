hostname
ifconfig | grep inet | awk '{ print $2 }'
cat /etc/*release*
free -m
df -h
free -h