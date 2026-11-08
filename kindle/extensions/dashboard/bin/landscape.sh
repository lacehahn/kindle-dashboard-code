#!/bin/sh
# 1448×1072: time/weather left, calendar right, forecast across the bottom.
SCR_W=1448
SCR_H=1072
BG=/mnt/us/dashboard/bg_landscape.png

draw_clock_block() {
    t 38 32 58 BLACK "$CITY"
    t 18 38 564 BLACK "电源键返回"
    draw_time_digits
}
draw_time_digits() { t 200 110 54 BLACK "${CLOCK_TEXT:-$(date +%H:%M)}"; }
CLOCK_RECT='top=156,left=40,width=640,height=244'
draw_today_info() { :; }
draw_weather_block() {
    w=$(weather_line)
    [ -n "$w" ] || { t 34 480 80 BLACK "天气等待联网"; return; }
    temp=$(echo "$w" | cut -d'|' -f2); hum=$(echo "$w" | cut -d'|' -f3)
    tx=$(echo "$w" | cut -d'|' -f5); tn=$(echo "$w" | cut -d'|' -f6)
    ic=$(echo "$w" | cut -d'|' -f8); tok=$(echo "$w" | cut -d'|' -f9)
    cn=$("$DASH_DIR/bin/weather.sh" cn "$tok")
    weather_glyph "$ic" 64 444 146
    t 86 440 250 BLACK "$(ri "$temp")°C"
    t 38 464 476 BLACK "$cn"
    t 28 540 260 BLACK "风速 $(ri "$(echo "$w" | cut -d'|' -f4)") m/s"
    t 34 610 64 BLACK "↑$(ri "$tx")°  ↓$(ri "$tn")°  湿度 ${hum}%"
}
draw_calendar() {
    y=$(date +%Y); m=$(nz "$(date +%m)"); d=$(nz "$(date +%d)")
    t 44 32 958 BLACK "${y}年${m}月"
    col=0
    for wd in 一 二 三 四 五 六 日; do
        t 32 112 $((766 + col * 94)) BLACK "$wd"
        col=$((col + 1))
    done
    first=$(first_dow "$y" "$m"); total=$(month_days "$y" "$m")
    day=1
    while [ "$day" -le "$total" ]; do
        idx=$((first + day - 1)); row=$((idx / 7)); col=$((idx % 7))
        cx=$((782 + col * 94)); cy=$((204 + row * 54))
        if [ "$day" = "$d" ]; then
            img "$ICONS/ui/day-$day.png" $((cx - 28)) $((cy - 12)) 56 56
        else
            if [ "$day" -lt 10 ]; then dx=13; else dx=26; fi
            t 42 $((cy - 23)) $((cx - dx)) BLACK "$day"
        fi
        day=$((day + 1))
    done
    t 32 564 758 BLACK "农历 $("$DASH_DIR/bin/lunar.sh")"
    t 28 624 758 BLACK "$("$DASH_DIR/bin/lunar.sh" gz)年"
    now_t=$("$DASH_DIR/bin/terms.sh" now); nxt=$("$DASH_DIR/bin/terms.sh" next)
    t 32 564 1100 BLACK "节气 $now_t"
    t 26 624 1100 BLACK "距${nxt%% *} ${nxt##* }天"
}
draw_forecast() {
    t 38 736 54 BLACK "未来3天预报"
    u=$(date +%u); i=1
    "$DASH_DIR/bin/weather.sh" forecast 2>/dev/null | head -3 | while IFS='|' read -r label tok hi lo; do
        x=$((62 + (i - 1) * 466))
        md=$(echo "$label" | awk '{print $NF}'); mm=${md%%/*}; dd=${md##*/}; dd=${dd#0}
        d=$(( (u + i - 1) % 7 + 1 ))
        icn=$(icon_for_token "$tok"); cn=$("$DASH_DIR/bin/weather.sh" cn "$tok")
        t 32 806 $x BLACK "${mm}月${dd}日（$(wd_name "$d")）"
        weather_glyph "$icn" $x 882 118
        t 36 874 $((x + 156)) BLACK "$cn"
        t 32 946 $((x + 156)) BLACK "$(ri "$lo")°~$(ri "$hi")°C"
        i=$((i + 1))
    done
}
