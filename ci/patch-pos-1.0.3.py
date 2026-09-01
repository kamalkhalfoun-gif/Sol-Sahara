from pathlib import Path

ROOT = Path('.')


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file = ROOT / path
    text = file.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} in {path}; found {count}")
    file.write_text(text.replace(old, new, 1))


def write(path: str, content: str) -> None:
    file = ROOT / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content)


# Version the app as an in-place update to 1.0.2.
replace_once(
    'android/app/build.gradle.kts',
    'versionCode = 3',
    'versionCode = 4',
    'versionCode 3',
)
replace_once(
    'android/app/build.gradle.kts',
    'versionName = "1.0.2"',
    'versionName = "1.0.3"',
    'versionName 1.0.2',
)
write('VERSION', '1.0.3\n')

write(
    'android/app/src/main/java/com/solandsahara/pos/model/ReceiptEmail.kt',
    r'''package com.solandsahara.pos.model

/**
 * Conservative validation for a customer-entered receipt address.
 *
 * The WordPress bridge performs the authoritative validation with WordPress'
 * is_email() before it stores or sends anything. This client-side check blocks
 * obvious typing mistakes without attempting to implement every email RFC.
 */
object ReceiptEmail {
    private val localPart = Regex("^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
    private val domainLabel = Regex("^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

    fun normalize(raw: String): String = raw.trim()

    fun validationError(raw: String): String? {
        val email = normalize(raw)
        if (email.isEmpty()) return null
        if (email.length > 254 || email.any { it.isWhitespace() || it.code < 33 }) {
            return "Enter a valid email address."
        }

        val at = email.indexOf('@')
        if (at <= 0 || at != email.lastIndexOf('@') || at >= email.lastIndex) {
            return "Enter a valid email address."
        }

        val local = email.substring(0, at)
        val domain = email.substring(at + 1)
        if (
            local.length > 64 || local.startsWith('.') || local.endsWith('.') ||
            local.contains("..") || !localPart.matches(local)
        ) {
            return "Enter a valid email address."
        }

        val labels = domain.split('.')
        if (labels.size < 2 || labels.any { it.length !in 1..63 || !domainLabel.matches(it) }) {
            return "Enter a valid email address."
        }
        if (labels.last().length !in 2..63 || labels.last().any { !it.isLetter() }) {
            return "Enter a valid email address."
        }

        return null
    }

    fun isValidOrBlank(raw: String): Boolean = validationError(raw) == null
}
''',
)

write(
    'android/app/src/test/java/com/solandsahara/pos/model/ReceiptEmailTest.kt',
    r'''package com.solandsahara.pos.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ReceiptEmailTest {
    @Test
    fun acceptsBlankAndCommonCustomerAddresses() {
        assertNull(ReceiptEmail.validationError(""))
        assertNull(ReceiptEmail.validationError("  customer@example.com  "))
        assertNull(ReceiptEmail.validationError("laura+farm.stand@sub.example.co.uk"))
        assertTrue(ReceiptEmail.isValidOrBlank("orders@solandsahara.com"))
    }

    @Test
    fun rejectsAddressesThatAreLikelyTypingErrors() {
        listOf(
            "customer",
            "@example.com",
            "customer@",
            "customer@@example.com",
            ".customer@example.com",
            "customer..name@example.com",
            "customer@example",
            "customer@-example.com",
            "customer@example.c",
            "customer @example.com",
        ).forEach { address ->
            assertFalse(address, ReceiptEmail.isValidOrBlank(address))
        }
    }

    @Test
    fun normalizationOnlyTrimsOuterWhitespace() {
        assertEquals(
            "Customer+Receipt@Example.com",
            ReceiptEmail.normalize("  Customer+Receipt@Example.com  "),
        )
    }
}
''',
)

# Model fields remain backward-compatible because every new field has a default.
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/model/Models.kt',
    '''    val serverTimeUnix: Long? = null,\n)\n\ndata class PosSettings''',
    '''    val serverTimeUnix: Long? = null,\n    val receiptEmail: String = "",\n    val receiptRequested: Boolean? = null,\n    val receiptSent: Boolean? = null,\n)\n\ndata class PosSettings''',
    'Sale receipt fields',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/model/Models.kt',
    '''    val serverTimeUnix: Long? = null,\n) {\n    /**''',
    '''    val serverTimeUnix: Long? = null,\n    val receiptEmailSupported: Boolean = false,\n) {\n    /**''',
    'BridgeHealth receipt capability',
)

# Bridge API capability, optional email payload, and server receipt outcome.
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/data/BridgeApi.kt',
    '''            readinessIssues = readinessIssues,\n            serverTimeUnix = root.optLongOrNull("server_time_unix"),\n        )''',
    '''            readinessIssues = readinessIssues,\n            serverTimeUnix = root.optLongOrNull("server_time_unix"),\n            receiptEmailSupported = root.optBoolean("receipt_email_supported", false),\n        )''',
    'health receipt capability',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/data/BridgeApi.kt',
    '''    suspend fun createSale(\n        saleId: String,\n        cart: CartSnapshot,\n        configuration: PosSettings = settings(),\n    ): Sale {''',
    '''    suspend fun createSale(\n        saleId: String,\n        cart: CartSnapshot,\n        receiptEmail: String = "",\n        configuration: PosSettings = settings(),\n    ): Sale {''',
    'createSale signature',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/data/BridgeApi.kt',
    '''            .put("sale_id", saleId)\n            .put("device_id", configuration.deviceId)\n            .put(\n                "items",''',
    '''            .put("sale_id", saleId)\n            .put("device_id", configuration.deviceId)\n            .apply {\n                receiptEmail.trim().takeIf { it.isNotBlank() }?.let { put("receipt_email", it) }\n            }\n            .put(\n                "items",''',
    'receipt email request body',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/data/BridgeApi.kt',
    '''            serverTimeUnix = root.optLongOrNull("server_time_unix"),\n        )\n    }\n\n    private fun JSONObject.optLongOrNull''',
    '''            serverTimeUnix = root.optLongOrNull("server_time_unix"),\n            receiptRequested = root.optBooleanOrNull("receipt_requested"),\n            receiptSent = root.optBooleanOrNull("receipt_sent"),\n        )\n    }\n\n    private fun JSONObject.optBooleanOrNull(name: String): Boolean? =\n        if (has(name) && !isNull(name)) optBoolean(name) else null\n\n    private fun JSONObject.optLongOrNull''',
    'receipt result decoding',
)

# Persist the requested address only inside the existing encrypted pending-sale
# envelope. It is cleared with the sale after confirmed payment.
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/settings/SecureSettingsStore.kt',
    '''            .put("reservation_expires_at", sale.reservationExpiresAt)\n            .put("server_time", sale.serverTime)\n            .apply {''',
    '''            .put("reservation_expires_at", sale.reservationExpiresAt)\n            .put("server_time", sale.serverTime)\n            .put("receipt_email", sale.receiptEmail)\n            .apply {''',
    'pending receipt email storage',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/settings/SecureSettingsStore.kt',
    '''                sale.reservationExpiresAtUnix?.let { put("reservation_expires_at_unix", it) }\n                sale.serverTimeUnix?.let { put("server_time_unix", it) }\n            }''',
    '''                sale.reservationExpiresAtUnix?.let { put("reservation_expires_at_unix", it) }\n                sale.serverTimeUnix?.let { put("server_time_unix", it) }\n                sale.receiptRequested?.let { put("receipt_requested", it) }\n                sale.receiptSent?.let { put("receipt_sent", it) }\n            }''',
    'pending receipt outcome storage',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/settings/SecureSettingsStore.kt',
    '''                reservationExpiresAtUnix = root.optLongOrNull("reservation_expires_at_unix"),\n                serverTimeUnix = root.optLongOrNull("server_time_unix"),\n            )''',
    '''                reservationExpiresAtUnix = root.optLongOrNull("reservation_expires_at_unix"),\n                serverTimeUnix = root.optLongOrNull("server_time_unix"),\n                receiptEmail = root.optString("receipt_email"),\n                receiptRequested = root.optBooleanOrNull("receipt_requested"),\n                receiptSent = root.optBooleanOrNull("receipt_sent"),\n            )''',
    'pending receipt outcome decoding',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/settings/SecureSettingsStore.kt',
    '''    private fun JSONObject.optLongOrNull(name: String): Long? =\n        if (has(name) && !isNull(name)) {\n            opt(name)?.toString()?.trim()?.toLongOrNull()\n        } else {\n            null\n        }\n''',
    '''    private fun JSONObject.optLongOrNull(name: String): Long? =\n        if (has(name) && !isNull(name)) {\n            opt(name)?.toString()?.trim()?.toLongOrNull()\n        } else {\n            null\n        }\n\n    private fun JSONObject.optBooleanOrNull(name: String): Boolean? =\n        if (has(name) && !isNull(name)) optBoolean(name) else null\n''',
    'nullable boolean helper',
)

# View-model state, validation, idempotent replay, and customer-facing result.
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    'import com.solandsahara.pos.model.ReaderConnectionState\n',
    'import com.solandsahara.pos.model.ReaderConnectionState\nimport com.solandsahara.pos.model.ReceiptEmail\n',
    'ReceiptEmail import',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''    val cartOriginMismatch: Boolean = false,\n    val pendingSaleRecoveryRequired: Boolean = false,\n    val message: String? = null,''',
    '''    val cartOriginMismatch: Boolean = false,\n    val pendingSaleRecoveryRequired: Boolean = false,\n    val receiptEmail: String = "",\n    val message: String? = null,''',
    'receiptEmail UI state',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''    val checkoutEnabled: Boolean\n        get() = !settingsBusy && !cartOriginMismatch && !pendingSaleRecoveryRequired &&\n            !demoMode && settings.isConfigured &&\n            bridgeHealth?.readyForPayments == true && online &&\n            readerState == ReaderConnectionState.CONNECTED && !cart.isEmpty &&\n            checkoutStage == CheckoutStage.IDLE\n}''',
    '''    val receiptEmailIssue: String? get() = ReceiptEmail.validationError(receiptEmail)\n    val receiptCapabilityIssue: String?\n        get() = if (receiptEmail.trim().isNotEmpty() && bridgeHealth?.receiptEmailSupported != true) {\n            "Update the Sol & Sahara POS Bridge before requesting email receipts."\n        } else {\n            null\n        }\n    val checkoutEnabled: Boolean\n        get() = !settingsBusy && !cartOriginMismatch && !pendingSaleRecoveryRequired &&\n            !demoMode && settings.isConfigured && receiptEmailIssue == null &&\n            receiptCapabilityIssue == null &&\n            bridgeHealth?.readyForPayments == true && online &&\n            readerState == ReaderConnectionState.CONNECTED && !cart.isEmpty &&\n            checkoutStage == CheckoutStage.IDLE\n}''',
    'receipt-aware checkout enabled',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''            activeSale = (initialPendingSaleResult as? PendingSaleLoadResult.Available)?.sale,\n            cart = app.cartPersistence.restoreFrozen(initialSettings.backendUrl),''',
    '''            activeSale = (initialPendingSaleResult as? PendingSaleLoadResult.Available)?.sale,\n            receiptEmail = (initialPendingSaleResult as? PendingSaleLoadResult.Available)\n                ?.sale?.receiptEmail.orEmpty(),\n            cart = app.cartPersistence.restoreFrozen(initialSettings.backendUrl),''',
    'restore receipt email',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''    fun setCategory(category: String) {\n        if (!mutableState.value.settingsBusy) update { it.copy(category = category) }\n    }\n\n    fun selectProduct''',
    '''    fun setCategory(category: String) {\n        if (!mutableState.value.settingsBusy) update { it.copy(category = category) }\n    }\n\n    fun setReceiptEmail(value: String) {\n        val current = mutableState.value\n        if (current.cartLocked) return\n        update { it.copy(receiptEmail = value.take(254), error = null) }\n    }\n\n    fun selectProduct''',
    'receipt email setter',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        app.cartPersistence.save(next, mutableState.value.settings.backendUrl)\n        update { it.copy(cart = next) }\n    }\n\n    fun clearCart''',
    '''        app.cartPersistence.save(next, mutableState.value.settings.backendUrl)\n        update {\n            it.copy(\n                cart = next,\n                receiptEmail = if (next.isEmpty) "" else it.receiptEmail,\n            )\n        }\n    }\n\n    fun clearCart''',
    'clear email when last item removed',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        app.cartPersistence.clear()\n        update { it.copy(cart = CartSnapshot(), cartOriginMismatch = false) }''',
    '''        app.cartPersistence.clear()\n        update {\n            it.copy(\n                cart = CartSnapshot(),\n                cartOriginMismatch = false,\n                receiptEmail = "",\n            )\n        }''',
    'clear email with cart',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        if (current.activeSale != null) {\n            refreshPendingSale(resumePaymentOnPending = true)\n            return\n        }\n\n        // Stop a previously-started catalog reconciliation''',
    '''        if (current.activeSale != null) {\n            refreshPendingSale(resumePaymentOnPending = true)\n            return\n        }\n\n        val receiptEmail = ReceiptEmail.normalize(current.receiptEmail)\n        ReceiptEmail.validationError(receiptEmail)?.let { issue ->\n            update { it.copy(error = issue) }\n            return\n        }\n        if (receiptEmail.isNotEmpty() && current.bridgeHealth?.receiptEmailSupported != true) {\n            update { it.copy(error = "Update the Sol & Sahara POS Bridge before requesting email receipts.") }\n            return\n        }\n\n        // Stop a previously-started catalog reconciliation''',
    'checkout email validation',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''                    expiresAt = "",\n                    items = emptyList(),\n                )''',
    '''                    expiresAt = "",\n                    items = emptyList(),\n                    receiptEmail = receiptEmail,\n                    receiptRequested = receiptEmail.isNotEmpty(),\n                )''',
    'placeholder receipt identity',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''                    app.bridgeApi.createSale(saleId, current.cart)''',
    '''                    app.bridgeApi.createSale(\n                        saleId = saleId,\n                        cart = current.cart,\n                        receiptEmail = receiptEmail,\n                        configuration = settingsSnapshot,\n                    )''',
    'create sale with receipt email',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''            app.bridgeApi.createSale(\n                placeholder.saleId,\n                frozenCart,\n                configuration,\n            )''',
    '''            app.bridgeApi.createSale(\n                saleId = placeholder.saleId,\n                cart = frozenCart,\n                receiptEmail = placeholder.receiptEmail,\n                configuration = configuration,\n            )''',
    'replay sale with receipt email',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        app.cartPersistence.clear()\n        app.settingsStore.clearPendingSale()\n        saleOperationGeneration++\n        update {\n            it.copy(\n                cart = CartSnapshot(),\n                cartOriginMismatch = false,\n                activeSale = null,\n                checkoutStage = CheckoutStage.SUCCEEDED,\n                message = "Paid · WooCommerce order #${sale.orderId}",''',
    '''        app.cartPersistence.clear()\n        app.settingsStore.clearPendingSale()\n        saleOperationGeneration++\n        val paidMessage = when {\n            sale.receiptEmail.isBlank() -> "Paid · WooCommerce order #${sale.orderId}"\n            sale.receiptSent == true -> "Paid · Receipt sent to ${sale.receiptEmail}"\n            else -> "Paid · Order #${sale.orderId}; receipt delivery was not confirmed"\n        }\n        update {\n            it.copy(\n                cart = CartSnapshot(),\n                cartOriginMismatch = false,\n                receiptEmail = "",\n                activeSale = null,\n                checkoutStage = CheckoutStage.SUCCEEDED,\n                message = paidMessage,''',
    'paid receipt result',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        serverTimeUnix = fetched.serverTimeUnix ?: previous.serverTimeUnix,\n    )''',
    '''        serverTimeUnix = fetched.serverTimeUnix ?: previous.serverTimeUnix,\n        receiptEmail = fetched.receiptEmail.ifBlank { previous.receiptEmail },\n        receiptRequested = fetched.receiptRequested ?: previous.receiptRequested,\n        receiptSent = fetched.receiptSent ?: previous.receiptSent,\n    )''',
    'merge receipt state',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/PosViewModel.kt',
    '''        !state.settings.isConfigured -> "Configure the live WooCommerce bridge."\n        state.bridgeHealth == null -> "Verify the POS bridge before checkout."''',
    '''        !state.settings.isConfigured -> "Configure the live WooCommerce bridge."\n        state.receiptEmailIssue != null -> state.receiptEmailIssue ?: "Enter a valid email address."\n        state.receiptCapabilityIssue != null -> state.receiptCapabilityIssue ?: "Email receipts are unavailable."\n        state.bridgeHealth == null -> "Verify the POS bridge before checkout."''',
    'receipt checkout block reason',
)

# Add the optional receipt field to the cart and disclose the address in the
# final server-authoritative total review before a card is presented.
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/ui/PosApp.kt',
    '''        Spacer(Modifier.height(12.dp))\n        if (state.readerState != ReaderConnectionState.CONNECTED && !state.demoMode) {''',
    '''        Spacer(Modifier.height(12.dp))\n        if (!state.cart.isEmpty) {\n            val receiptIssue = state.receiptEmailIssue ?: state.receiptCapabilityIssue\n            OutlinedTextField(\n                value = state.receiptEmail,\n                onValueChange = viewModel::setReceiptEmail,\n                modifier = Modifier.fillMaxWidth(),\n                label = { Text("Email receipt (optional)") },\n                placeholder = { Text("customer@example.com") },\n                supportingText = {\n                    Text(\n                        receiptIssue ?: if (state.receiptEmail.isBlank()) {\n                            "Includes the order number, items, tax, and total."\n                        } else {\n                            "Receipt will be emailed after payment is confirmed."\n                        },\n                    )\n                },\n                isError = receiptIssue != null,\n                enabled = !state.cartLocked,\n                singleLine = true,\n                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),\n            )\n            Spacer(Modifier.height(8.dp))\n        }\n        if (state.readerState != ReaderConnectionState.CONNECTED && !state.demoMode) {''',
    'cart receipt field',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/ui/PosApp.kt',
    '''                            Text("WooCommerce verified current prices, tax, and inventory.")\n                            Row(Modifier.fillMaxWidth()) {''',
    '''                            Text("WooCommerce verified current prices, tax, and inventory.")\n                            Text(\n                                if (sale.receiptEmail.isBlank()) {\n                                    "No email receipt requested."\n                                } else {\n                                    "Email receipt: ${sale.receiptEmail}"\n                                },\n                                style = MaterialTheme.typography.bodyMedium,\n                                color = MaterialTheme.colorScheme.onSurfaceVariant,\n                            )\n                            Row(Modifier.fillMaxWidth()) {''',
    'review receipt address',
)
replace_once(
    'android/app/src/main/java/com/solandsahara/pos/ui/PosApp.kt',
    '''            text = { Text("WooCommerce received the order and will update inventory.") },''',
    '''            text = { Text("WooCommerce received the order, updated inventory, and processed any requested email receipt.") },''',
    'success receipt text',
)

print('Applied Sol & Sahara POS 1.0.3 email receipt patch')
