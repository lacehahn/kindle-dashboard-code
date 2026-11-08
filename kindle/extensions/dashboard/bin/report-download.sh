#!/bin/sh
# Authenticated GitHub raw downloads. Credentials stay in curl's local config.
REPORT_ROOT=${REPORT_ROOT:-/mnt/us/dashboard}
report_hash() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then openssl dgst -sha256 "$1" | awk '{print $NF}'
    else return 1; fi
}
report_download() {
    case "$REPORT_REPOSITORY" in *[!a-zA-Z0-9_./-]*|''|/*|*..*) return 1 ;; esac
    owner=${REPORT_REPOSITORY%%/*}; repo=${REPORT_REPOSITORY#*/}
    [ "$owner" != "$repo" ] || return 1
    case "$repo" in */*|'') return 1 ;; esac
    case "${REPORT_REF:-reports}" in *[!a-zA-Z0-9_-]*|'') return 1 ;; esac
    [ -f "$REPORT_ROOT/report-auth.conf" ] || return 1
    stage=/tmp/dashboard-report-stage.$$
    mkdir -p "$stage/assets" || return 1
    api="https://api.github.com/repos/$REPORT_REPOSITORY/contents"
    # No redirect following: the authorization header is only sent to api.github.com.
    if ! curl -fSs -K "$REPORT_ROOT/report-auth.conf" --connect-timeout 10 --max-time 30 --max-filesize 500000 "$api/report.json?ref=${REPORT_REF:-reports}" -o "$stage/report.json"; then rm -rf "$stage"; return 1; fi
    if ! "$DASH_DIR/bin/reportread" "$stage/report.json" > "$stage/commands" || ! "$DASH_DIR/bin/reportread" "$stage/report.json" --assets > "$stage/manifest"; then rm -rf "$stage"; return 1; fi
    if ! "$DASH_DIR/bin/reportread" "$stage/report.json" --portrait > "$stage/portrait-commands"; then rm -rf "$stage"; return 1; fi
    cat "$stage/portrait-commands" >> "$stage/commands"
    bundle=$("$DASH_DIR/bin/reportread" "$stage/report.json" --bundle) || { rm -rf "$stage"; return 1; }
    [ -s "$stage/manifest" ] || { rm -rf "$stage"; return 1; }
    while IFS='|' read -r name expected; do
        case "$name" in clear.png|partly.png|cloud.png|rain.png|snow.png|fog.png|today.png|bg_report.png|bg_portrait.png|codex.png|deepseek.png|quota_landscape.png|quota_portrait.png) ;; *) rm -rf "$stage"; return 1 ;; esac
        if ! curl -fSs -K "$REPORT_ROOT/report-auth.conf" --connect-timeout 10 --max-time 20 --max-filesize 200000 "$api/bundles/$bundle/$name?ref=${REPORT_REF:-reports}" -o "$stage/assets/$name"; then rm -rf "$stage"; return 1; fi
        actual=$(report_hash "$stage/assets/$name") || { rm -rf "$stage"; return 1; }
        [ "$actual" = "$expected" ] || { rm -rf "$stage"; return 1; }
    done < "$stage/manifest"
    while IFS='|' read -r kind x y w h path; do
        [ "$kind" = I ] || continue
        case "$path" in /mnt/us/dashboard/bg_report.png) name=bg_report.png ;;
            /mnt/us/dashboard/icons/*.png) name=${path#/mnt/us/dashboard/icons/}; case "$name" in */*) rm -rf "$stage"; return 1 ;; esac ;;
            *) rm -rf "$stage"; return 1 ;;
        esac
        [ -s "$stage/assets/$name" ] || { rm -rf "$stage"; return 1; }
    done < "$stage/commands"
    id=$(report_hash "$stage/report.json") || { rm -rf "$stage"; return 1; }
    case "$id" in *[!0-9a-f]*|'') rm -rf "$stage"; return 1 ;; esac
    cache=$REPORT_ROOT/report-cache
    mkdir -p "$cache" || { rm -rf "$stage"; return 1; }
    # Copy complete immutable generation before atomically changing the pointer.
    if [ ! -d "$cache/$id" ]; then
        rm -rf "$cache/$id.tmp"
        if ! cp -R "$stage" "$cache/$id.tmp" || ! mv "$cache/$id.tmp" "$cache/$id"; then rm -rf "$stage" "$cache/$id.tmp"; return 1; fi
    fi
    echo "$id" > "$REPORT_ROOT/report-current.new"
    mv "$REPORT_ROOT/report-current.new" "$REPORT_ROOT/report-current" || { rm -rf "$stage"; return 1; }
    rm -rf "$stage"
    # Keep only the newly selected generation; failed downloads never reach this step.
    for old in "$cache"/*; do [ "$old" = "$cache/$id" ] || rm -rf "$old"; done
}
