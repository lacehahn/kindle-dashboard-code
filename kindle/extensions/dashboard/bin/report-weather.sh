#!/bin/sh
# Separate fresh weather from the Mac's daily account usage snapshot.
WEATHER_CACHE=/mnt/us/dashboard/weather-current
report_weather_fetch() {
    weather_url="https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&timezone=${TZ_NAME}&forecast_days=4&wind_speed_unit=ms&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code"
    if curl -fLsS --connect-timeout 15 --max-time 40 "$weather_url" -o "$WEATHER_CACHE.json.new" 2>> "$LOG" &&
       "$DASH_DIR/bin/weatherread" "$WEATHER_CACHE.json.new" > "$WEATHER_CACHE.new"; then
        mv "$WEATHER_CACHE.new" "$WEATHER_CACHE"
        rm -f "$WEATHER_CACHE.json.new"
        return 0
    fi
    rm -f "$WEATHER_CACHE.new" "$WEATHER_CACHE.json.new"
    return 1
}
report_weather_token() {
    case "$1" in
        0) weather_icon=clear; weather_cn=晴 ;; 1|2) weather_icon=partly; weather_cn=多云 ;;
        3) weather_icon=cloud; weather_cn=阴 ;; 45|48) weather_icon=fog; weather_cn=雾 ;;
        71|73|75|77|85|86) weather_icon=snow; weather_cn=雪 ;;
        *) weather_icon=rain; weather_cn=雨 ;;
    esac
}
report_weather_number() { awk -v n="$1" 'BEGIN{printf "%.0f",n}'; }
report_weather_draw() {
    [ -s "$WEATHER_CACHE" ] || return 0
    IFS='|' read -r kind weather_time temp hum wind code high low < "$WEATHER_CACHE"
    [ "$kind" = current ] || return 0
    local_stamp=$(printf '%s' "$weather_time" | tr -cd '0-9')
    snapshot_stamp=$("$DASH_DIR/bin/reportread" "$current/report.json" --stamp 2>/dev/null)
    if [ -n "$snapshot_stamp" ] && awk -v local="$local_stamp" -v remote="$snapshot_stamp" 'BEGIN{exit !(local+0<remote+0)}'; then return 0; fi
    report_weather_token "$code"
    if [ "$SCR_W" = 1072 ]; then
        rr 40 252 990 96 255; rr 654 258 2 82 0
        img "$ICONS/$weather_icon.png" 160 254 128 104
        rt 64 256 360 "$(report_weather_number "$temp")°C"; rt 30 266 548 "$weather_cn"
        rt 27 314 360 "风速 $wind m/s"; rt 30 262 720 "↑$(report_weather_number "$high")°  ↓$(report_weather_number "$low")°"; rt 30 316 720 "湿度 $hum%"
        rr 50 812 980 150 255; rr 382 822 2 130 0; rr 722 822 2 130 0
    else
        rr 40 420 622 118 255; rr 448 432 2 90 0
        img "$ICONS/$weather_icon.png" 64 432 104 104
        rt 64 432 214 "$(report_weather_number "$temp")°C"; rt 30 440 376 "$weather_cn"
        rt 25 492 214 "风速 $wind m/s"; rt 30 436 480 "↑$(report_weather_number "$high")° ↓$(report_weather_number "$low")°"; rt 30 494 480 "湿度 $hum%"
        rr 260 590 1150 164 255; rr 622 618 2 112 0; rr 1014 618 2 112 0
    fi
    i=0
    while IFS='|' read -r kind fcdate code high low; do
        [ "$kind" = forecast ] || continue
        fy=${fcdate%%-*}; md=${fcdate#*-}; fm=$(nz "${md%-*}"); fd=$(nz "${md#*-}")
        dow=$(( ($(first_dow "$fy" "$fm") + fd - 1) % 7 )); wd=$(printf '一\n二\n三\n四\n五\n六\n日\n' | sed -n "$((dow+1))p")
        report_weather_token "$code"
        if [ "$SCR_W" = 1072 ]; then
            fx=$((70+i*340)); rt 29 826 "$fx" "${fm}月${fd}日（周${wd}）"; img "$ICONS/$weather_icon.png" "$fx" 874 88 88
            rt 30 880 "$((fx+112))" "$weather_cn"; rt 30 924 "$((fx+112))" "$(report_weather_number "$low")°~$(report_weather_number "$high")°C"
        else
            fx=$((290+i*384)); rt 29 612 "$fx" "${fm}月${fd}日（周${wd}）"; img "$ICONS/$weather_icon.png" "$fx" 664 86 86
            rt 29 688 "$((fx+98))" "$weather_cn"; rt 29 688 "$((fx+160))" "$(report_weather_number "$low")°~$(report_weather_number "$high")°C"
        fi
        i=$((i+1)); [ "$i" -lt 3 ] || break
    done < "$WEATHER_CACHE"
}
