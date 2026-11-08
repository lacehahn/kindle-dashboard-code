#!/bin/sh
# 日历：给定年、月，算出 1 号是星期几（周一=0）与该月天数

# Zeller 同余 -> 周一为 0 的列号
first_dow() { # year month
    awk -v y="$1" -v m="$2" 'BEGIN{
        if (m < 3) { m += 12; y -= 1 }
        K = y % 100; J = int(y / 100)
        h = (1 + int(13 * (m + 1) / 5) + K + int(K / 4) + int(J / 4) + 5 * J) % 7
        print (h + 5) % 7
    }'
}

month_days() { # year month
    case "$2" in
        1|3|5|7|8|10|12) echo 31 ;;
        4|6|9|11) echo 30 ;;
        2)
            y=$1
            if [ $((y % 4)) -eq 0 ] && [ $((y % 100)) -ne 0 ] || [ $((y % 400)) -eq 0 ]; then
                echo 29
            else
                echo 28
            fi
            ;;
        *) echo 30 ;;
    esac
}

# 数字去前导零
nz() { _v=$1; echo "${_v#0}"; }
