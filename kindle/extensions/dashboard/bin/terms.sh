#!/bin/sh
# 节气查询（数据表 2024-2040）
DATA=/mnt/us/dashboard/terms.dat
today=$(date +%Y%m%d)

case "$1" in
    now)
        awk -F'|' -v t="$today" '$1<=t{n=$2} END{print n}' "$DATA"
        ;;
    next)
        awk -F'|' -v t="$today" '
        function ord(s, y,m,d, era,yoe,doy,doe){
            y=int(s/10000); m=int(s/100)%100; d=s%100;
            y -= (m<=2);
            era = int(y/400); yoe = y - era*400;
            doy = int((153*(m + (m>2 ? -3 : 9)) + 2)/5) + d - 1;
            doe = yoe*365 + int(yoe/4) - int(yoe/100) + doy;
            return era*146097 + doe - 719468;
        }
        $1>t { printf "%s %d\n", $2, ord($1)-ord(t); exit }
        ' "$DATA"
        ;;
esac
