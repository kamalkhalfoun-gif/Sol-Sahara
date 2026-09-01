from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"Expected exactly one {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


build = Path("android/app/build.gradle.kts")
text = build.read_text()
text = replace_once(text, "versionCode = 2", "versionCode = 3", "versionCode 2")
text = replace_once(text, 'versionName = "1.0.1"', 'versionName = "1.0.2"', "versionName 1.0.1")
build.write_text(text)

policy = Path(
    "android/app/src/main/java/com/solandsahara/pos/terminal/PaymentIntentBindingPolicy.kt"
)
policy.write_text(
    '''package com.solandsahara.pos.terminal

/**
 * Validates POS identity metadata when the Terminal SDK exposes it.
 *
 * The reader still requires the exact PaymentIntent ID, amount, and currency.
 * The WordPress bridge independently validates server-side metadata before it
 * marks a WooCommerce order paid. Some Apps on Devices SDK responses omit
 * custom metadata, so absent client-side metadata is treated as unavailable.
 * Any supplied nonblank identity value must match exactly.
 */
object PaymentIntentBindingPolicy {
    fun requireValid(
        metadata: Map<String, String>?,
        expectedSaleId: String,
        expectedWooOrderId: String,
    ) {
        check(expectedSaleId.isNotBlank() && expectedWooOrderId.isNotBlank()) {
            "The approved sale is missing its WooCommerce identity."
        }

        val values = metadata.orEmpty()
        values["sale_id"]?.takeIf { it.isNotBlank() }?.let { actual ->
            check(actual == expectedSaleId) {
                "The retrieved PaymentIntent contains conflicting sale metadata."
            }
        }
        values["wc_order_id"]?.takeIf { it.isNotBlank() }?.let { actual ->
            check(actual == expectedWooOrderId) {
                "The retrieved PaymentIntent contains conflicting WooCommerce metadata."
            }
        }
        values["source"]?.takeIf { it.isNotBlank() }?.let { actual ->
            check(actual == EXPECTED_SOURCE) {
                "The retrieved PaymentIntent contains conflicting POS source metadata."
            }
        }
    }

    private const val EXPECTED_SOURCE = "sol_sahara_pos"
}
'''
)

tests = Path(
    "android/app/src/test/java/com/solandsahara/pos/terminal/PaymentIntentBindingPolicyTest.kt"
)
tests.write_text(
    '''package com.solandsahara.pos.terminal

import org.junit.Assert.assertThrows
import org.junit.Test

class PaymentIntentBindingPolicyTest {
    private val validMetadata = mapOf(
        "sale_id" to "5e025cf1-e0fe-41ad-9277-8fd3ca697dd4",
        "wc_order_id" to "42",
        "source" to "sol_sahara_pos",
    )

    @Test
    fun acceptsExactPosBinding() {
        PaymentIntentBindingPolicy.requireValid(
            validMetadata,
            validMetadata.getValue("sale_id"),
            validMetadata.getValue("wc_order_id"),
        )
    }

    @Test
    fun acceptsMetadataOmittedByTerminalSdk() {
        val saleId = validMetadata.getValue("sale_id")
        PaymentIntentBindingPolicy.requireValid(null, saleId, "42")
        PaymentIntentBindingPolicy.requireValid(emptyMap(), saleId, "42")
        PaymentIntentBindingPolicy.requireValid(mapOf("unrelated" to "value"), saleId, "42")
        PaymentIntentBindingPolicy.requireValid(mapOf("sale_id" to ""), saleId, "42")
    }

    @Test
    fun rejectsAnyConflictingIdentityValueThatIsProvided() {
        listOf("sale_id", "wc_order_id", "source").forEach { key ->
            assertThrows(IllegalStateException::class.java) {
                PaymentIntentBindingPolicy.requireValid(
                    validMetadata + (key to "wrong"),
                    validMetadata.getValue("sale_id"),
                    validMetadata.getValue("wc_order_id"),
                )
            }
        }
    }
}
'''
)

ui = Path("android/app/src/main/java/com/solandsahara/pos/ui/PosApp.kt")
ui_text = ui.read_text()
ui_text = replace_once(
    ui_text,
    'Text("RETRY SAME PAYMENT")',
    'Text("CHECK STATUS")',
    "retry button label",
)
ui.write_text(ui_text)

version = Path("VERSION")
if version.exists():
    version.write_text("1.0.2\n")

print("Applied Sol & Sahara POS 1.0.2 compatibility patch")
