// Copyright 2026 Milyonus. Licensed under the Apache License, Version 2.0.
package com.milyonus.mphone.ime

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.util.Base64
import android.util.Log
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.TextView

/**
 * A keyboard with no keys: it types exactly what mphone sends, so Turkish letters and emoji reach
 * the focused field without passing through `adb shell input text` (ASCII only, ADR-0009).
 *
 * Text arrives base64-encoded in a broadcast. The receiver requires android.permission.DUMP from
 * the sender: adb's shell user holds it, ordinary apps cannot, so no installed app can make this
 * keyboard type on its behalf.
 */
class MphoneIme : InputMethodService() {

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            // `am broadcast` is ordered and prints the result code, so the sender learns what
            // happened: 0 = nobody listened (IME not created yet), 1 = done, 2 = no focused field.
            val ic = currentInputConnection
            if (ic == null || currentInputEditorInfo == null || currentInputEditorInfo.inputType == 0) {
                Log.w(TAG, "no focused field; ${intent.action} dropped")
                if (isOrderedBroadcast) resultCode = RESULT_NO_FIELD
                return
            }
            if (isOrderedBroadcast) resultCode = RESULT_DONE
            when (intent.action) {
                ACTION_INPUT_B64 -> {
                    val b64 = intent.getStringExtra(EXTRA_MSG) ?: return
                    val text = String(Base64.decode(b64, Base64.DEFAULT), Charsets.UTF_8)
                    ic.commitText(text, 1)
                }
                ACTION_CLEAR -> {
                    val before = ic.getTextBeforeCursor(MAX_CLEAR, 0)?.length ?: 0
                    val after = ic.getTextAfterCursor(MAX_CLEAR, 0)?.length ?: 0
                    ic.deleteSurroundingText(before, after)
                }
                ACTION_ENTER -> {
                    val action = currentInputEditorInfo?.imeOptions?.and(EditorInfo.IME_MASK_ACTION)
                    if (action != null && action != EditorInfo.IME_ACTION_NONE && action != EditorInfo.IME_ACTION_UNSPECIFIED) {
                        ic.performEditorAction(action)
                    } else {
                        ic.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER))
                        ic.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER))
                    }
                }
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        val filter = IntentFilter().apply {
            addAction(ACTION_INPUT_B64)
            addAction(ACTION_CLEAR)
            addAction(ACTION_ENTER)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, filter, SENDER_PERMISSION, null, Context.RECEIVER_EXPORTED)
        } else {
            registerReceiver(receiver, filter, SENDER_PERMISSION, null)
        }
    }

    override fun onDestroy() {
        unregisterReceiver(receiver)
        super.onDestroy()
    }

    /** A thin banner instead of keys: the person holding the phone can see automation is typing. */
    override fun onCreateInputView(): View = TextView(this).apply {
        text = getString(R.string.ime_banner)
        setPadding(24, 16, 24, 16)
        setBackgroundColor(Color.rgb(37, 99, 235))
        setTextColor(Color.WHITE)
    }

    companion object {
        private const val TAG = "MphoneIme"
        const val ACTION_INPUT_B64 = "com.milyonus.mphone.ime.INPUT_B64"
        const val ACTION_CLEAR = "com.milyonus.mphone.ime.CLEAR"
        const val ACTION_ENTER = "com.milyonus.mphone.ime.ENTER"
        const val EXTRA_MSG = "msg"
        const val SENDER_PERMISSION = "android.permission.DUMP"
        private const val MAX_CLEAR = 100_000
        const val RESULT_DONE = 1
        const val RESULT_NO_FIELD = 2
    }
}
