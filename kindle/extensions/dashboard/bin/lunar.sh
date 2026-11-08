#!/bin/sh
# 农历查询：数据表预生成（2024-2035），按日期直接查
DATA=/mnt/us/dashboard/lunar.dat
today=$(date +%Y%m%d)
line=$(grep "^$today" "$DATA" 2>/dev/null)
[ -n "$line" ] || { echo "--"; exit 0; }
case "$1" in
    gz) cut -d'|' -f3 <<EOF
$line
EOF
    ;;
    *) cut -d'|' -f2 <<EOF
$line
EOF
    ;;
esac
