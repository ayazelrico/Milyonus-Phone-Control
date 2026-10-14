// Copyright 2026 Milyonus. Licensed under the Apache License, Version 2.0.
package com.milyonus.mphone.ime

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.TextView

/**
 * Deterministic E2E screen (debug APK only): a text field, a password field, a "Gönder" button
 * that echoes the field into a label, and a 200-row list. Resource ids are stable so tests can
 * select them: mphone_text, mphone_password, mphone_send, mphone_echo, mphone_list.
 */
class TestFieldsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(32, 32, 32, 32) }
        val text = EditText(this).apply { hint = "Metin" }
        val password = EditText(this).apply {
            hint = "PIN"
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_VARIATION_PASSWORD
        }
        val echo = TextView(this).apply { text = "—" }
        val send = Button(this).apply {
            setText("Gönder")
            setOnClickListener { echo.text = "Gönderildi: " + text.text }
        }
        val list = ListView(this).apply {
            adapter = ArrayAdapter(this@TestFieldsActivity, android.R.layout.simple_list_item_1, (1..200).map { "Öğe $it" })
        }
        // resource-ids in the uiautomator dump come from entry names, so use real ids from resources.
        text.id = R.id.mphone_text
        password.id = R.id.mphone_password
        send.id = R.id.mphone_send
        echo.id = R.id.mphone_echo
        list.id = R.id.mphone_list
        listOf(text, password, send, echo).forEach { root.addView(it) }
        root.addView(list, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
    }
}
