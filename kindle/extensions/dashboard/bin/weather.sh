#!/bin/sh
# 天气：优先 OpenWeather（有 key 时），失败自动退回 Open-Meteo
#   refresh  -> 拉数据写缓存，输出 ok <provider>
#   show     -> EN|temp|hum|wind|tmax|tmin|upd|icon|token
#   cn <tok> -> 该天气的中文名
#   forecast -> 两行：label|token|hi|lo

DASH_DIR=${DASH_DIR:-/mnt/us/extensions/dashboard}
. "$DASH_DIR/bin/config.sh"

CUR=/tmp/dash_weather
FC=/tmp/dash_forecast
SRC=/tmp/dash_weather_src

en_of() {
    case "$1" in
        clear) echo "CLEAR" ;;
        partly) echo "PARTLY CLOUDY" ;;
        cloud) echo "OVERCAST" ;;
        fog) echo "FOG" ;;
        drizzle) echo "DRIZZLE" ;;
        rain) echo "RAIN" ;;
        snow) echo "SNOW" ;;
        showers) echo "SHOWERS" ;;
        thunder) echo "THUNDER" ;;
        *) echo "--" ;;
    esac
}

cn_of() {
    case "$1" in
        clear) echo "晴" ;;
        partly) echo "多云" ;;
        cloud) echo "阴" ;;
        fog) echo "雾" ;;
        drizzle) echo "毛毛雨" ;;
        rain) echo "雨" ;;
        snow) echo "雪" ;;
        showers) echo "阵雨" ;;
        thunder) echo "雷雨" ;;
        *) echo "--" ;;
    esac
}

icon_of() {
    case "$1" in
        clear) echo "clear" ;;
        partly) echo "partly" ;;
        cloud) echo "cloud" ;;
        fog) echo "fog" ;;
        snow) echo "snow" ;;
        *) echo "rain" ;;
    esac
}

wmo_tok() {
    case "$1" in
        0) echo clear ;;
        1|2) echo partly ;;
        3) echo cloud ;;
        45|48) echo fog ;;
        51|53|55|56|57) echo drizzle ;;
        61|63|65|66|67) echo rain ;;
        71|73|75|77) echo snow ;;
        80|81|82) echo showers ;;
        85|86) echo snow ;;
        95|96|99) echo thunder ;;
        *) echo cloud ;;
    esac
}

ow_tok() {
    case "$1" in
        800) echo clear ;;
        801|802) echo partly ;;
        803|804) echo cloud ;;
        7*) echo fog ;;
        3*) echo drizzle ;;
        5*) echo rain ;;
        6*) echo snow ;;
        2*) echo thunder ;;
        *) echo cloud ;;
    esac
}

# ---------- OpenWeather ----------
fetch_ow() {
    base="https://api.openweathermap.org/data/2.5"
    q="lat=${LAT}&lon=${LON}&units=metric&appid=${OW_KEY}"

    cur=$(curl -s --max-time 10 "${base}/weather?${q}")
    echo "$cur" | grep -q '"cod":200' || return 1

    temp=$(echo "$cur" | grep -oE '"temp":[-0-9.]+' | head -1 | cut -d: -f2)
    hum=$(echo "$cur"  | grep -oE '"humidity":[0-9]+' | head -1 | cut -d: -f2)
    wind=$(echo "$cur" | grep -oE '"speed":[-0-9.]+' | head -1 | cut -d: -f2)
    wid=$(echo "$cur"  | grep -oE '"id":[0-9]+' | head -1 | cut -d: -f2)
    tmax=$(echo "$cur" | grep -oE '"temp_max":[-0-9.]+' | head -1 | cut -d: -f2)
    tmin=$(echo "$cur" | grep -oE '"temp_min":[-0-9.]+' | head -1 | cut -d: -f2)
    [ -n "$temp" ] || return 1

    tok=$(ow_tok "${wid:-800}")
    printf '%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$tok" "$temp" "${hum:-0}" "${wind:-0}" "${tmax:-$temp}" "${tmin:-$temp}" \
        "$(date +%H:%M)" "$(icon_of "$tok")" > "$CUR"

    fc=$(curl -s --max-time 12 "${base}/forecast?${q}")
    : > "$FC"
    if echo "$fc" | grep -q '"cod":"200"'; then
        echo "$fc" | sed 's/},{/}\n{/g' | awk -F',' '
        {
            date=""; tmin=""; tmax=""; id="";
            for (i = 1; i <= NF; i++) {
                if ($i ~ /"dt_txt":"/) {
                    s = $i; sub(/.*"dt_txt":"/, "", s); split(s, a, " "); date = a[1];
                }
                if ($i ~ /"temp_min":/) { s = $i; gsub(/[^0-9.\-]/, "", s); if (tmin == "" || s + 0 < tmin + 0) tmin = s }
                if ($i ~ /"temp_max":/) { s = $i; gsub(/[^0-9.\-]/, "", s); if (tmax == "" || s + 0 > tmax + 0) tmax = s }
                if ($i ~ /"id":/ && id == "") { s = $i; gsub(/[^0-9]/, "", s); id = s }
            }
            if (date != "") {
                if (!(date in dmin)) { dmin[date] = tmin; dmax[date] = tmax; did[date] = id; order[++n] = date }
                else {
                    if (tmin + 0 < dmin[date] + 0) dmin[date] = tmin;
                    if (tmax + 0 > dmax[date] + 0) dmax[date] = tmax;
                }
            }
        }
        END {
            c = 0;
            for (i = 1; i <= n; i++) {
                d = order[i];
                if (d == today) continue;
                c++;
                if (c > 3) break;
                split(d, p, "-");
                if (c == 1) label = "明天 " p[2] "/" p[3];
                else if (c == 2) label = "后天 " p[2] "/" p[3];
                else label = "大后天 " p[2] "/" p[3];
                print label "|" did[d] "|" dmax[d] "|" dmin[d];
            }
        }' today="$(date +%Y-%m-%d)" > "$FC.raw"
        # OpenWeather 给的是数字 id，转成统一 token
        : > "$FC"
        while IFS='|' read -r label id hi lo; do
            [ -n "$label" ] || continue
            echo "$label|$(ow_tok "$id")|$hi|$lo" >> "$FC"
        done < "$FC.raw"
        rm -f "$FC.raw"
    fi

    echo "openweather" > "$SRC"
    return 0
}

# ---------- Open-Meteo ----------
fetch_om() {
    url="https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}"
    url="${url}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
    url="${url}&daily=temperature_2m_max,temperature_2m_min,weather_code"
    url="${url}&timezone=${TZ_NAME}&forecast_days=5&wind_speed_unit=ms"

    json=$(curl -s --max-time 12 "$url")
    [ -n "$json" ] || return 1

    code=$(echo "$json" | grep -oE '"weather_code":-?[0-9]+' | head -1 | cut -d: -f2)
    temp=$(echo "$json" | grep -oE '"temperature_2m":-?[0-9.]+' | head -1 | cut -d: -f2)
    hum=$(echo "$json"  | grep -oE '"relative_humidity_2m":-?[0-9]+' | head -1 | cut -d: -f2)
    wind=$(echo "$json" | grep -oE '"wind_speed_10m":-?[0-9.]+' | head -1 | cut -d: -f2)
    [ -n "$temp" ] || return 1

    amax=$(echo "$json" | sed -n 's/.*"temperature_2m_max":\[\([^]]*\)\].*/\1/p')
    amin=$(echo "$json" | sed -n 's/.*"temperature_2m_min":\[\([^]]*\)\].*/\1/p')
    acode=$(echo "$json" | sed -n 's/.*"weather_code":\[\([^]]*\)\].*/\1/p')
    adate=$(echo "$json" | sed -n 's/.*"time":\[\([^]]*\)\].*/\1/p' | tr -d '"')

    tok=$(wmo_tok "${code:-3}")
    printf '%s|%s|%s|%s|%s|%s|%s|%s\n' \
        "$tok" "$temp" "${hum:-0}" "${wind:-0}" \
        "$(echo "$amax" | cut -d, -f1)" "$(echo "$amin" | cut -d, -f1)" \
        "$(date +%H:%M)" "$(icon_of "$tok")" > "$CUR"

    : > "$FC"
    i=2
    while [ $i -le 4 ]; do
        c=$(echo "$acode" | cut -d, -f$i)
        hi=$(echo "$amax" | cut -d, -f$i)
        lo=$(echo "$amin" | cut -d, -f$i)
        d=$(echo "$adate" | cut -d, -f$i)
        mm=$(echo "$d" | cut -d- -f2)
        dd=$(echo "$d" | cut -d- -f3)
        case $i in
            2) label="明天 $mm/$dd" ;;
            3) label="后天 $mm/$dd" ;;
            *) label="大后天 $mm/$dd" ;;
        esac
        echo "$label|$(wmo_tok "${c:-3}")|$hi|$lo" >> "$FC"
        i=$((i + 1))
    done

    echo "open-meteo" > "$SRC"
    return 0
}

do_refresh() {
    [ -n "$OW_KEY" ] && fetch_ow && return 0
    fetch_om && return 0
    echo "fail" > "$SRC"
    return 1
}

case "$1" in
    refresh)
        do_refresh && echo "ok $(cat "$SRC" 2>/dev/null)" || echo "fail"
        ;;
    show)
        if [ -f "$CUR" ]; then
            IFS='|' read -r tok t h w tx tn up ic < "$CUR"
            printf '%s|%s|%s|%s|%s|%s|%s|%s|%s\n' \
                "$(en_of "$tok")" "$t" "$h" "$w" "$tx" "$tn" "$up" "$ic" "$tok"
        fi
        ;;
    cn)
        cn_of "$2"
        ;;
    forecast)
        [ -f "$FC" ] && cat "$FC"
        ;;
esac
