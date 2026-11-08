#!/bin/sh
# Private nightly report; local clock, battery and calendar remain device-owned.
SCR_W=1448; SCR_H=1072; REPORT_READ_ARG=
if [ "${DASH_LAYOUT:-report}" = report-portrait ]; then
    SCR_W=1072; SCR_H=1448; REPORT_READ_ARG=--portrait
fi
REPORT_MODE=1
REPORT_COMMANDS=/tmp/dashboard-report-commands
if [ -f /mnt/us/dashboard/report.conf ]; then . /mnt/us/dashboard/report.conf; fi
. "$DASH_DIR/bin/report-download.sh"
. "$DASH_DIR/bin/report-weather.sh"
weather_due() {
    [ "${REPORT_RETRY_AT:-0}" -le "$1" ] || return 1
    [ "$(date +%H%M)" -ge 100 ] || return 1
    today=$(date +%Y%m%d)
    [ "$(cat /mnt/us/dashboard/report-day 2>/dev/null)" != "$today" ] ||
    [ "$(cat /mnt/us/dashboard/weather-day 2>/dev/null)" != "$today" ]
}
refresh_weather() {
    REPORT_RETRY_AT=$(($(date +%s)+3600))
    power_network_on
    if report_weather_fetch; then
        if [ "$(date +%H%M)" -ge 100 ]; then date +%Y%m%d > /mnt/us/dashboard/weather-day; fi
        echo "$(date '+%F %T') nightly fresh weather verified" >> "$LOG"
    else echo "$(date '+%F %T') weather download rejected; retaining cache" >> "$LOG"; fi
    if [ -n "$REPORT_REPOSITORY" ] && report_download; then
        current=/mnt/us/dashboard/report-cache/$(cat /mnt/us/dashboard/report-current)
        epoch=$("$DASH_DIR/bin/reportread" "$current/report.json" --epoch)
        h=$(date +%H); m=$(date +%M); sec=$(date +%S)
        expected=$(($(date +%s) - ${h#0}*3600 - ${m#0}*60 - ${sec#0} - 14400))
        # At 01:00, the expected usage snapshot is from the previous evening 20:00.
        if [ "$(date +%H%M)" -ge 100 ] && [ -n "$epoch" ] && [ "$epoch" -ge "$expected" ]; then
            date +%Y%m%d > /mnt/us/dashboard/report-day
        fi
        echo "$(date '+%F %T') nightly private report verified epoch=$epoch" >> "$LOG"
    else echo "$(date '+%F %T') private report unavailable; retaining cache" >> "$LOG"; fi
    today=$(date +%Y%m%d)
    if [ "$(cat /mnt/us/dashboard/report-day 2>/dev/null)" = "$today" ] && [ "$(cat /mnt/us/dashboard/weather-day 2>/dev/null)" = "$today" ]; then REPORT_RETRY_AT=0; fi
    power_network_off
}
report_update_local() {
    # Called only on the initial display and each ten-minute clock boundary.
    BATTERY_LEVEL=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
    case "$BATTERY_LEVEL" in ''|*[!0-9]*) BATTERY_LEVEL= ;;
        *) [ "$BATTERY_LEVEL" -le 100 ] || BATTERY_LEVEL= ;;
    esac
}
report_battery() {
    if [ "$SCR_W" = 1072 ]; then size=28; top=24; left=800; x=964; y=34; w=52; h=28
    else size=24; top=34; left=482; x=612; y=42; w=40; h=24; fi
    t "$size" "$top" "$left" BLACK "电量 ${BATTERY_LEVEL:---}%"
    printf 'R|%s|%s|%s|%s|0\nR|%s|%s|%s|%s|255\nR|%s|%s|4|10|0\n' "$x" "$y" "$w" "$h" "$((x+3))" "$((y+3))" "$((w-6))" "$((h-6))" "$((x+w))" "$((y+h/2-5))" >> "$COMMANDS"
    if [ -n "$BATTERY_LEVEL" ]; then printf 'R|%s|%s|%s|%s|0\n' "$((x+5))" "$((y+5))" "$(((w-10)*BATTERY_LEVEL/100))" "$((h-10))" >> "$COMMANDS"; fi
}
# These coordinates use visible text tops, then compensate for the font ascent.
rt() { size=$1; y=$2; x=$3; shift 3; t "$size" "$((y-size*45/100))" "$x" BLACK "$*"; }
rr() { printf 'R|%s|%s|%s|%s|%s\n' "$1" "$2" "$3" "$4" "$5" >> "$COMMANDS"; }
report_calendar() {
    year=$(date +%Y); month=$(nz "$(date +%m)"); today=$(nz "$(date +%d)")
    if [ "$SCR_W" = 1072 ]; then
        rr 30 390 1012 320 255
        rr 58 442 624 2 0; rr 728 420 2 278 0; rr 766 504 244 2 0; rr 766 582 244 2 0
        rt 44 398 74 "${year}年${month}月"; start=125; step=84; weektop=454; firsttop=500; rowstep=37; side=766
    else
        rr 708 30 710 506 255
        rr 720 100 470 2 0; rr 1218 76 2 444 0; rr 1240 232 162 2 0; rr 1240 358 162 2 0
        rt 44 42 880 "${year}年${month}月"; start=735; step=70; weektop=124; firsttop=184; rowstep=58; side=1240
    fi
    col=0
    for wd in 一 二 三 四 五 六 日; do rt 28 "$weektop" "$((start+col*step-14))" "$wd"; col=$((col+1)); done
    first=$(first_dow "$year" "$month"); total=$(month_days "$year" "$month"); day=1
    while [ "$day" -le "$total" ]; do
        idx=$((first+day-1)); x=$((start+idx%7*step)); y=$((firsttop+idx/7*rowstep))
        if [ "$day" = "$today" ]; then img "$ICONS/ui/day-$day.png" "$((x-22))" "$((y-8))" 44 44
        else [ "$SCR_W" = 1072 ] && ds=30 || ds=34; [ "$day" -lt 10 ] && dx=$((ds*3/10)) || dx=$((ds*6/10)); rt "$ds" "$y" "$((x-dx))" "$day"; fi
        day=$((day+1))
    done
    lunar=$("$DASH_DIR/bin/lunar.sh"); gz=$("$DASH_DIR/bin/lunar.sh" gz); term=$("$DASH_DIR/bin/terms.sh" now); next=$("$DASH_DIR/bin/terms.sh" next)
    if [ "$SCR_W" = 1072 ]; then
        rt 28 408 "$side" 农历; rt 36 454 "$side" "$lunar"; rt 30 534 "$side" "${gz}年"; rt 29 606 "$side" "节气 $term"; rt 27 658 "$side" "距${next%% *} ${next##* }天"
    else
        rt 25 92 "$side" 农历; rt 30 152 "$side" "$lunar"; rt 30 280 "$side" "${gz}年"; rt 26 390 "$side" "节气 $term"; rt 24 466 "$side" "距${next%% *} ${next##* }天"
    fi
}
draw_page() {
    render_begin
    id=$(cat /mnt/us/dashboard/report-current 2>/dev/null)
    case "$id" in *[!0-9a-f]*|'') id=none ;; esac
    current=/mnt/us/dashboard/report-cache/$id
    if [ -f "$current/report.json" ] && "$DASH_DIR/bin/reportread" "$current/report.json" $REPORT_READ_ARG > "$REPORT_COMMANDS.new"; then
        sed "s|/mnt/us/dashboard/icons/|$current/assets/|g;s|/mnt/us/dashboard/bg_report.png|$current/assets/bg_report.png|g" "$REPORT_COMMANDS.new" >> "$COMMANDS"
        report_calendar
        report_weather_draw
    else t 34 350 110 BLACK "私有报告未配置或尚未下载"; fi
    if [ "$SCR_W" = 1072 ]; then t 190 0 280 BLACK "${CLOCK_TEXT:-$(date +%H:%M)}"
    else t 220 68 58 BLACK "${CLOCK_TEXT:-$(date +%H:%M)}"; fi
    report_battery
    render_present 0
}
