#!/usr/bin/env bash
# Capture raw adb output from a device/emulator as test fixtures (A2.01–A2.12).
#
#   tools/android/capture_fixtures.sh OUT_DIR [SERIAL]
#
# Every command's stdout, stderr and exit code land in OUT_DIR/<name>.{out,err,code}, so parsers
# are written against what Android really prints, not what we remember it printing (CLAUDE.md §6.3).
# Run it on throwaway devices only: it sets and clears a lock-screen PIN and changes the screen state.
set -u
OUT=${1:?usage: capture_fixtures.sh OUT_DIR [SERIAL]}
SERIAL=${2:-}
mkdir -p "$OUT"
ADB=(adb)
[ -n "$SERIAL" ] && ADB=(adb -s "$SERIAL")

cap() {  # cap NAME CMD...   — host-side command
  local name=$1; shift
  "$@" >"$OUT/$name.out" 2>"$OUT/$name.err"
  echo $? >"$OUT/$name.code"
}
sh() {  # sh NAME 'device shell command'
  local name=$1; shift
  cap "$name" "${ADB[@]}" shell "$@"
}
pause() { sleep "${1:-2}"; }
# `uiautomator dump /dev/tty` prints only "UI hierchary dumped to: /dev/tty" under a
# non-interactive adb shell (no tty): the XML never arrives. Dump to a file and read it back.
uia() { sh "$1" "uiautomator dump /sdcard/mphone_ui.xml >/dev/null && cat /sdcard/mphone_ui.xml"; }

# --- identity and transport -------------------------------------------------
cap adb_version adb version
cap devices_l adb devices -l
cap mdns_services adb mdns services
cap mdns_check adb mdns check
for p in ro.build.version.release ro.build.version.sdk ro.product.model ro.product.manufacturer \
         ro.serialno ro.product.locale persist.sys.locale persist.sys.timezone; do
  sh "getprop_$p" getprop "$p"
done
sh dumpsys_battery dumpsys battery

# --- awake / locked: unlocked & awake ----------------------------------------
"${ADB[@]}" shell input keyevent KEYCODE_WAKEUP; "${ADB[@]}" shell wm dismiss-keyguard; pause
sh power_awake "dumpsys power | grep -E 'mWakefulness=|Display Power|mHoldingDisplaySuspendBlocker'"
sh window_unlocked "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"
sh window_policy_unlocked "dumpsys window policy | grep -iE 'keyguard|showing'"
sh dumpsys_power_full dumpsys power
sh dumpsys_window_policy_full dumpsys window policy

# --- screen geometry ----------------------------------------------------------
sh wm_size wm size
sh wm_density wm density
sh input_orientation "dumpsys input | grep -E 'SurfaceOrientation|orientation'"
sh display_rotation "dumpsys display | grep -E 'mCurrentOrientation|rotation'"
cap screencap_png "${ADB[@]}" exec-out screencap -p

# --- input capabilities ---------------------------------------------------------
sh input_help input
sh input_motionevent_probe input motionevent
sh ime_list ime list -s
sh ime_current settings get secure default_input_method

# --- apps -----------------------------------------------------------------------
sh pm_list_3 pm list packages -3
sh pm_list_all pm list packages
sh pm_list_3_f pm list packages -3 -f
sh resolve_settings cmd package resolve-activity --brief -c android.intent.category.LAUNCHER com.android.settings
sh dumpsys_package_settings "dumpsys package com.android.settings | head -80"
sh query_launchers "cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"

# --- home screen + tree ----------------------------------------------------------
"${ADB[@]}" shell input keyevent KEYCODE_HOME; pause
sh activity_home "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'"
sh window_focus_home "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
sh uia_home_tty uiautomator dump /dev/tty   # kept as evidence of the /dev/tty pitfall
uia uia_home
sh uia_home_compressed "uiautomator dump --compressed /sdcard/mphone_ui.xml >/dev/null && cat /sdcard/mphone_ui.xml"

# --- settings app ---------------------------------------------------------------
"${ADB[@]}" shell am start -W -n "$("${ADB[@]}" shell cmd package resolve-activity --brief -c android.intent.category.LAUNCHER com.android.settings | tail -1 | tr -d '\r')" >"$OUT/am_start_settings.out" 2>&1
pause 3
sh activity_settings "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'"
uia uia_settings
cap screencap_settings_png "${ADB[@]}" exec-out screencap -p
# scroll with motionevent (no momentum) and with swipe (momentum) for comparison
sh motionevent_scroll "input motionevent DOWN 540 1600 && input motionevent MOVE 540 1300 && input motionevent MOVE 540 1000 && sleep 0.1 && input motionevent UP 540 1000"
pause
uia uia_settings_scrolled
sh swipe_fast input swipe 540 1600 540 1000 80
pause
uia uia_settings_flung

# --- text input -------------------------------------------------------------------
"${ADB[@]}" shell input keyevent KEYCODE_HOME; pause
"${ADB[@]}" shell am start -a android.intent.action.SEARCH >/dev/null 2>&1 || true
"${ADB[@]}" shell am start -a android.settings.SETTINGS >/dev/null 2>&1; pause 2
sh input_text_ascii input text 'hello%sworld'
sh input_text_turkish input text 'çağrı'
sh input_text_specials "input text 'a&b'"
sh keyevent_enter input keyevent KEYCODE_ENTER

# --- notifications / statusbar ----------------------------------------------------
sh notifications_noredact "dumpsys notification --noredact | head -400"
sh statusbar_expand cmd statusbar expand-notifications
pause
uia uia_notifications
sh statusbar_collapse cmd statusbar collapse-notifications

# --- asleep ------------------------------------------------------------------------
"${ADB[@]}" shell input keyevent KEYCODE_SLEEP; pause 2
sh power_asleep "dumpsys power | grep -E 'mWakefulness=|Display Power'"
sh window_asleep "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"

# --- locked with a PIN (set, observe, clear) --------------------------------------------
# Android locks a secure device only after lock_screen_lock_after_timeout (default 5 s) once the
# screen is off; capturing sooner records an UNLOCKED phone. Force 0 and wait anyway.
# Emulator images usually ship with the lock screen disabled outright (lockscreen.disabled), so
# a PIN alone never shows a keyguard: enable it first, and record what the image had.
sh lockscreen_disabled_before settings get secure lockscreen.disabled
sh prop_lockscreen_disable_default getprop ro.lockscreen.disable.default
sh lock_timeout_before settings get secure lock_screen_lock_after_timeout
sh locksettings_enable locksettings set-disabled false
"${ADB[@]}" shell settings put secure lock_screen_lock_after_timeout 0
sh locksettings_set locksettings set-pin 1234
"${ADB[@]}" shell input keyevent KEYCODE_SLEEP; pause 7
"${ADB[@]}" shell input keyevent KEYCODE_WAKEUP
for _ in 1 2 3 4 5 6 7 8 9 10; do
  "${ADB[@]}" shell dumpsys window | grep -q 'isKeyguardShowing=true' && break
  sleep 1
done
pause 1
sh power_locked "dumpsys power | grep -E 'mWakefulness=|Display Power'"
sh window_locked "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"
sh window_policy_locked "dumpsys window policy | grep -iE 'keyguard|showing'"
uia uia_locked
cap screencap_locked_png "${ADB[@]}" exec-out screencap -p
sh window_locked_full "dumpsys window | grep -iE 'keyguard|lockscreen|dream'"
sh activity_locked "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'"
sh tap_while_locked input tap 540 1200
sh locksettings_clear locksettings clear --old 1234
BEFORE=$(tr -d '\r' < "$OUT/lock_timeout_before.out")
if [ "$BEFORE" = "null" ] || [ -z "$BEFORE" ]; then
  "${ADB[@]}" shell settings delete secure lock_screen_lock_after_timeout
else
  "${ADB[@]}" shell settings put secure lock_screen_lock_after_timeout "$BEFORE"
fi
"${ADB[@]}" shell input keyevent KEYCODE_WAKEUP; "${ADB[@]}" shell wm dismiss-keyguard; pause 2
sh window_after_clear "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"


# --- mphone IME: Turkish text into a real field (needs IME_APK, the debug build) ------------
if [ -n "${IME_APK:-}" ] && [ -f "$IME_APK" ]; then
  cap ime_install "${ADB[@]}" install -r -g "$IME_APK"
  # The input method service scans a new package asynchronously: `ime enable` right after install
  # answers "Unknown input method". Wait until the IME is listed.
  WAITED=0
  until "${ADB[@]}" shell ime list -a -s | grep -q 'com.milyonus.mphone.ime/'; do
    sleep 1; WAITED=$((WAITED + 1)); [ $WAITED -ge 30 ] && break
  done
  echo "$WAITED" > "$OUT/ime_wait_seconds.out"
  sh ime_enable ime enable com.milyonus.mphone.ime/.MphoneIme
  sh ime_list_all ime list -a -s
  sh ime_before settings get secure default_input_method
  sh test_activity_start am start -W -n com.milyonus.mphone.ime/.TestFieldsActivity
  pause 2
  uia uia_testfields
  # centre of the text field from its bounds="[l,t][r,b]"
  B=$(tr '>' '\n' < "$OUT/uia_testfields.out" | grep 'mphone_text' | grep -o 'bounds="[^"]*"' | head -1 | tr -dc '0-9,[]' | tr '[],' '   ')
  set -- $B; X=$(( ($1 + $3) / 2 )); Y=$(( ($2 + $4) / 2 ))
  echo "$X $Y" > "$OUT/testfields_text_centre.out"
  "${ADB[@]}" shell input tap "$X" "$Y"; pause 1
  sh ime_set ime set com.milyonus.mphone.ime/.MphoneIme
  pause 2
  MSG=$(printf '%s' "Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀" | base64 | tr -d '\n')
  sh ime_broadcast_turkish am broadcast -a com.milyonus.mphone.ime.INPUT_B64 --es msg "$MSG"
  pause 1
  uia uia_testfields_typed
  sh ime_broadcast_clear am broadcast -a com.milyonus.mphone.ime.CLEAR
  pause 1
  uia uia_testfields_cleared
  sh ime_broadcast_turkish2 am broadcast -a com.milyonus.mphone.ime.INPUT_B64 --es msg "$(printf '%s' 'Şule Öztürk' | base64)"
  pause 1
  uia uia_testfields_typed2
  sh ime_restore ime set "$(tr -d '\r' < "$OUT/ime_before.out")"
  sh ime_after settings get secure default_input_method
else
  echo "IME_APK not set; skipping IME capture" > "$OUT/ime_skipped.out"
fi

# --- errors ----------------------------------------------------------------------------
cap error_bad_serial adb -s does-not-exist shell true
cap error_unknown_command "${ADB[@]}" shell this-command-does-not-exist

echo "captured $(ls "$OUT" | wc -l) files into $OUT"
