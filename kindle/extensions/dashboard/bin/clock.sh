#!/bin/sh
# 窗边 · 单页墨水屏看板（三卡片：时间天气 / 日历 / 未来三天）
# 时间、电量每十分钟 · 报告及天气每晚 · 日历本机日期

DASH_DIR=${DASH_DIR:-/mnt/us/extensions/dashboard}
. "$DASH_DIR/bin/config.sh"
. "$DASH_DIR/bin/ui.sh"
. "$DASH_DIR/bin/calendar.sh"

LOG=/mnt/us/dashboard.log
PIDFILE=/tmp/dashboard.pid
BG=/mnt/us/dashboard/bg_page.png
ICONS=/mnt/us/dashboard/icons

[ -x "$FBINK" ] || { echo "$(date '+%F %T') fbink missing" >> "$LOG"; exit 1; }

trap 'exit 143' TERM
trap 'exit 130' INT
echo $$ > "$PIDFILE"
echo "$(date '+%F %T') start pid=$$" >> "$LOG"
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null

FONT=$CJK_FONT
[ -f "$FONT_BOLD" ] || FONT_BOLD=$FONT
[ -f "$FONT" ] || { echo "$(date '+%F %T') font missing" >> "$LOG"; exit 1; }

ri() { [ -n "$1" ] || { echo "--"; return; }; awk -v v="$1" 'BEGIN{printf "%.0f", v}'; }

cn_week() {
    case "$(date +%u)" in
        1) echo 星期一 ;; 2) echo 星期二 ;; 3) echo 星期三 ;;
        4) echo 星期四 ;; 5) echo 星期五 ;; 6) echo 星期六 ;;
        *) echo 星期日 ;;
    esac
}
wd_name() {
    case "$1" in
        1) echo 周一 ;; 2) echo 周二 ;; 3) echo 周三 ;;
        4) echo 周四 ;; 5) echo 周五 ;; 6) echo 周六 ;;
        *) echo 周日 ;;
    esac
}
icon_for_token() {
    case "$1" in
        clear) echo clear ;; partly) echo partly ;; cloud) echo cloud ;;
        fog) echo fog ;; snow) echo snow ;; *) echo rain ;;
    esac
}
weather_due() { [ $(( $1 - $2 )) -ge $((WEATHER_MIN * 60)) ]; }
weather_line() { "$DASH_DIR/bin/weather.sh" show 2>/dev/null; }
refresh_weather() {
    power_network_on
    r=$("$DASH_DIR/bin/weather.sh" refresh 2>/dev/null)
    echo "$(date '+%F %T') weather: $r" >> "$LOG"
    power_network_off
}

# ---- 卡片 1 ----
draw_clock_block() {
    t 34 28 66 BLACK "$CITY"
    t 18 32 390 BLACK "电源键返回"
    draw_time_digits
}

draw_today_info() { :; }

draw_weather_block() {
    w=$(weather_line)
    [ -n "$w" ] || { t 30 198 644 BLACK "天气等待联网"; return 0; }
    temp=$(echo "$w" | cut -d'|' -f2); hum=$(echo "$w" | cut -d'|' -f3)
    tx=$(echo "$w" | cut -d'|' -f5); tn=$(echo "$w" | cut -d'|' -f6)
    ic=$(echo "$w" | cut -d'|' -f8); tok=$(echo "$w" | cut -d'|' -f9)
    cn=$("$DASH_DIR/bin/weather.sh" cn "$tok")

    weather_glyph "$ic" 584 44 178
    t 88 50 794 BLACK "$(ri "$temp")°C"
    t 44 160 804 BLACK "$cn"
    t 32 238 608 BLACK "风速 $(ri "$(echo "$w" | cut -d'|' -f4)") m/s"
    t 32 308 592 BLACK "↑$(ri "$tx")°  ↓$(ri "$tn")°  ${hum}%"
    t 28 362 610 BLACK "最高     最低    湿度"
}

# ---- 卡片 2：日历 ----
draw_calendar() {
    y=$(date +%Y); m=$(nz "$(date +%m)"); d=$(nz "$(date +%d)")
    tm 48 431 BLACK "${y} 年 ${m} 月"
    
    

    col=0
    for wd in 一 二 三 四 五 六 日; do
        t 38 520 $((100 + col * 140)) BLACK "$wd"
        col=$((col + 1))
    done
    first=$(first_dow "$y" "$m")
    total=$(month_days "$y" "$m")
    day=1
    while [ $day -le $total ]; do
        idx=$((first + day - 1))
        row=$((idx / 7)); col=$((idx % 7))
        cx=$(( 44 + col * 140 + 70 ))
        cy=$(( 566 + row * 52 + 25 ))
        if [ "$day" = "$d" ]; then
            # Whole badge is pre-rendered: white numeral cannot blend into a white pen background.
            img "$ICONS/ui/day-$day.png" $((cx - 28)) $((cy - 12)) 56 56
        else
            if [ "$day" -lt 10 ]; then dx=13; else dx=26; fi
            t 44 $((cy - 23)) $((cx - dx)) BLACK "$day"
        fi
        day=$((day + 1))
    done

    # 底部：农历 / 节气
    t 36 934 78 BLACK "农历 $("$DASH_DIR/bin/lunar.sh")"
    t 30 986 78 BLACK "$("$DASH_DIR/bin/lunar.sh" gz)年"
    now_t=$("$DASH_DIR/bin/terms.sh" now)
    nxt=$("$DASH_DIR/bin/terms.sh" next)
    t 36 934 552 BLACK "节气 $now_t"
    t 30 986 552 BLACK "距${nxt%% *} ${nxt##* } 天"
}

# ---- 卡片 3：未来三天 ----
draw_forecast() {
    t 42 1078 52 BLACK "未来3天预报"
    u=$(date +%u)
    i=1
    "$DASH_DIR/bin/weather.sh" forecast 2>/dev/null | head -3 | while IFS='|' read -r label tok hi lo; do
        x=$(( 72 + (i - 1) * 332 ))
        md=$(echo "$label" | awk '{print $NF}')
        mm=${md%%/*}; dd=${md##*/}; dd=${dd#0}
        d=$(( (u + i - 1) % 7 + 1 ))
        icn=$(icon_for_token "$tok")
        cn=$("$DASH_DIR/bin/weather.sh" cn "$tok")
        t 30 1144 $x BLACK "${mm}月${dd}日（$(wd_name "$d")）"
        weather_glyph "$icn" $((x + 60)) 1190 110
        t 38 1300 $((x + 90)) BLACK "$cn"
        t 36 1354 $x BLACK "$(ri "$lo")°C ~ $(ri "$hi")°C"
        i=$((i + 1))
    done
}

draw_page() {
    render_begin
    img "$BG" 0 0
    draw_clock_block
    draw_weather_block
    draw_calendar
    draw_forecast
    render_present 0 || return 1
    echo "$(date '+%F %T') page drawn layout=${DASH_LAYOUT:-portrait}" >> "$LOG"
}

# Shared refresh loop; each layout supplies its own clock rectangle.
draw_time_digits() { t 176 96 60 BLACK "${CLOCK_TEXT:-$(date +%H:%M)}"; }
CLOCK_RECT='top=138,left=40,width=508,height=222'
if [ "${DASH_LAYOUT:-portrait}" = landscape ]; then
    . "$DASH_DIR/bin/landscape.sh"
fi

if [ "${DASH_LAYOUT:-portrait}" = report ] || [ "${DASH_LAYOUT:-portrait}" = report-portrait ]; then
    . "$DASH_DIR/bin/report-layout.sh"
fi
# Render both layouts with an independent raster backend. No framebuffer text
# calls or state-dump API are used on this firmware.
. "$DASH_DIR/bin/raster.sh"
[ -x "$RENDER" ] || { echo "$(date '+%F %T') renderer missing" >> "$LOG"; exit 1; }
trap 'rc=$?; echo "$(date "+%F %T") clock exited rc=$rc" >> "$LOG"' 0
# Let KUAL close before the first framebuffer draw.
sleep 2
. "$DASH_DIR/bin/power.sh"
power_init
CLOCK_TEXT=$(date +%H:%M)
if [ "${REPORT_MODE:-0}" = 1 ]; then report_update_local; fi
NEXT_REFRESH=$(next_refresh_epoch "$(date +%s)")
# Show a page before network I/O, then fill in the latest weather.
draw_page || exit 1
refresh_weather
if [ "$(date +%s)" -ge "$NEXT_REFRESH" ]; then
    CLOCK_TEXT=$(date +%H:%M)
    if [ "${REPORT_MODE:-0}" = 1 ]; then report_update_local; fi
fi
draw_page || exit 1

last_day="$(date +%Y%m%d)"
wlast=$(date +%s)
power_tick_done
power_enter_sleep

while :; do
    # RTC may wake a few seconds early; do not redraw the clock until the boundary.
    power_wait
    now=$(date +%s)
    if [ "${POWER_REPAINT:-0}" = 1 ]; then
        draw_page || exit 1
        POWER_REPAINT=0
    fi
    if [ "$POWER_ACTIVE" = 1 ] && [ -f "$POWER_DIR/last-event" ] && grep -q redraw "$POWER_DIR/last-event"; then
        draw_page || exit 1
    fi
    [ "$now" -ge "$NEXT_REFRESH" ] || continue
    CLOCK_TEXT=$(date +%H:%M)
    if [ "${REPORT_MODE:-0}" = 1 ]; then report_update_local; fi
    cur_day="$(date +%Y%m%d)"
    if weather_due "$now" "$wlast"; then
        refresh_weather
        CLOCK_TEXT=$(date +%H:%M)
        draw_page || exit 1
        wlast=$(date +%s)
        last_day=$(date +%Y%m%d)
        power_tick_done
        power_enter_sleep
    elif [ "$cur_day" != "$last_day" ]; then
        last_day=$cur_day
        draw_page || exit 1
        power_tick_done
    else
        if [ "${REPORT_MODE:-0}" = 1 ]; then
            draw_page || exit 1
        else
            render_begin
            draw_time_digits
            render_present 1 || exit 1
        fi
        power_tick_done
    fi
done
