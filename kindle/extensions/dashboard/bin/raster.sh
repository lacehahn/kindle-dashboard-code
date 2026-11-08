#!/bin/sh
# Same drawing calls, but render offscreen and rotate the image in software.
RENDER="$DASH_DIR/bin/render"
COMMANDS=/tmp/dashboard-draw.txt
FRAME=/tmp/dashboard-frame.pgm
render_begin() { : > "$COMMANDS"; }
t() { # visible em size, top, left, color, text
    _size=$1; _y=$2; _x=$3; _color=0; [ "$4" = WHITE ] && _color=255; shift 4
    printf 'T|%s|%s|%s|%s|%s\n' "$_size" "$_y" "$_x" "$_color" "$*" >> "$COMMANDS"
}
tm() {
    _size=$1; _y=$2; _color=0; [ "$3" = WHITE ] && _color=255; shift 3
    printf 'M|%s|%s|0|%s|%s\n' "$_size" "$_y" "$_color" "$*" >> "$COMMANDS"
}
img() { printf 'I|%s|%s|%s|%s|%s\n' "$2" "$3" "${4:-0}" "${5:-${4:-0}}" "$1" >> "$COMMANDS"; }
wipe() { :; }
render_present() {
    _partial=${1:-0}
    _rotate=0; case "${DASH_LAYOUT:-portrait}" in landscape|report) _rotate=1 ;; esac
    if ! "$RENDER" "$SCR_W" "$SCR_H" "$_rotate" "$FONT_BOLD" "$COMMANDS" "$FRAME" "$_partial"; then
        echo "$(date '+%F %T') raster render failed" >> "$LOG"
        return 1
    fi
    if [ "$_partial" = 1 ]; then
        # Counterclockwise raster mapping: (x,y) -> (y, width-1-x).
        if [ "$_rotate" = 1 ]; then _x=156; _y=768; else _x=40; _y=138; fi
    else
        _x=0; _y=0
    fi
    if ! "$FBINK" -q -g "file=$FRAME,x=$_x,y=$_y"; then
        echo "$(date '+%F %T') framebuffer image failed" >> "$LOG"
        return 1
    fi
}
