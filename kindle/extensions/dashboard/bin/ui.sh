#!/bin/sh
# FBInk -O 保留背景；CJK 字体 ascender/descender 较大，补偿到可见字号。

FBINK=/mnt/us/libkh/bin/fbink
[ -x "$FBINK" ] || FBINK=$(command -v fbink)
SCR_W=1072
SCR_H=1448

t() { # px top left color text...
    _px=$(( $1 * 145 / 100 )); _top=$2; _left=$3; _col=$4; shift 4
    "$FBINK" -q -b -O -t regular="$FONT",bold="$FONT_BOLD",style=BOLD,px=$_px,top=$_top,left=$_left -C "$_col" "$*"
}

tm() { # px top color text...  —— 整屏水平居中
    _px=$(( $1 * 145 / 100 )); _top=$2; _col=$3; shift 3
    "$FBINK" -q -b -O -m -t regular="$FONT",bold="$FONT_BOLD",style=BOLD,px=$_px,top=$_top -C "$_col" "$*"
}

rule() { # y [x0] [x1]
    _y=$1; _x0=${2:-$M}; _x1=${3:-$((SCR_W - M))}
    "$FBINK" -q -b -k top=$_y,left=$_x0,width=$((_x1 - _x0)),height=2 -B BLACK
}

bar() { # x y w h
    "$FBINK" -q -b -k top=$2,left=$1,width=$3,height=$4 -B BLACK
}

img() { # path x y [w] [h]
    if [ -n "$4" ]; then
        "$FBINK" -q -b -g file=$1,x=$2,y=$3,w=$4,h=${5:-$4}
    else
        "$FBINK" -q -b -g file=$1,x=$2,y=$3
    fi
}

weather_glyph() { # icon_name x y px
    _icon="$ICONS/$1.png"
    [ -f "$_icon" ] || _icon="$ICONS/cloud.png"
    img "$_icon" "$2" "$3" "${4:-140}" "${4:-140}"
}

wipe() { "$FBINK" -q -c; }
