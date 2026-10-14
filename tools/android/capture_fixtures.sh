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
sh uia_home_tty uiautomator dump /dev/tty
sh uia_home_compressed_tty uiautomator dump --compressed /dev/tty
sh uia_home_file "uiautomator dump /sdcard/mphone_ui.xml && cat /sdcard/mphone_ui.xml"

# --- settings app ---------------------------------------------------------------
"${ADB[@]}" shell am start -W -n "$("${ADB[@]}" shell cmd package resolve-activity --brief -c android.intent.category.LAUNCHER com.android.settings | tail -1 | tr -d '\r')" >"$OUT/am_start_settings.out" 2>&1
pause 3
sh activity_settings "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity|ResumedActivity'"
sh uia_settings_tty uiautomator dump /dev/tty
cap screencap_settings_png "${ADB[@]}" exec-out screencap -p
# scroll with motionevent (no momentum) and with swipe (momentum) for comparison
sh motionevent_scroll "input motionevent DOWN 540 1600 && input motionevent MOVE 540 1300 && input motionevent MOVE 540 1000 && sleep 0.1 && input motionevent UP 540 1000"
pause
sh uia_settings_scrolled_tty uiautomator dump /dev/tty
sh swipe_fast input swipe 540 1600 540 1000 80
pause
sh uia_settings_flung_tty uiautomator dump /dev/tty

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
sh uia_notifications_tty uiautomator dump /dev/tty
sh statusbar_collapse cmd statusbar collapse-notifications

# --- asleep ------------------------------------------------------------------------
"${ADB[@]}" shell input keyevent KEYCODE_SLEEP; pause 2
sh power_asleep "dumpsys power | grep -E 'mWakefulness=|Display Power'"
sh window_asleep "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"

# --- locked with a PIN (set, observe, clear) --------------------------------------------
sh locksettings_set locksettings set-pin 1234
"${ADB[@]}" shell input keyevent KEYCODE_SLEEP; pause 2
"${ADB[@]}" shell input keyevent KEYCODE_WAKEUP; pause 2
sh power_locked "dumpsys power | grep -E 'mWakefulness=|Display Power'"
sh window_locked "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"
sh window_policy_locked "dumpsys window policy | grep -iE 'keyguard|showing'"
sh uia_locked_tty uiautomator dump /dev/tty
cap screencap_locked_png "${ADB[@]}" exec-out screencap -p
sh locksettings_clear locksettings clear --old 1234
"${ADB[@]}" shell input keyevent KEYCODE_WAKEUP; "${ADB[@]}" shell wm dismiss-keyguard; pause 2
sh window_after_clear "dumpsys window | grep -E 'isKeyguardShowing|mDreamingLockscreen|mShowingLockscreen|KeyguardShowing'"

# --- errors ----------------------------------------------------------------------------
cap error_bad_serial adb -s does-not-exist shell true
cap error_unknown_command "${ADB[@]}" shell this-command-does-not-exist

echo "captured $(ls "$OUT" | wc -l) files into $OUT"
