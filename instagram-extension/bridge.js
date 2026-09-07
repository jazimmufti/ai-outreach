/**
 * Arclent Instagram Outreach Assistant — Bridge Script (Manifest V3)
 * Injected into Arclent web app origins (localhost, 127.0.0.1, arclent.com)
 * Enables seamless, secure detection and bidirectional communication with the Arclent web app.
 */

(() => {
    // 1. Mark presence in the DOM
    document.documentElement.setAttribute("data-arclent-instagram-extension", "installed");
    document.documentElement.dataset.arclentExtensionVersion = "1.0.0";

    // 2. Dispatch custom event for immediate script listeners
    window.dispatchEvent(new CustomEvent("ARCLENT_INSTAGRAM_EXTENSION_READY", {
        detail: {
            installed: true,
            version: "1.0.0",
            name: "Arclent Instagram Assistant"
        }
    }));

    // 3. Listen for window postMessages from Arclent web app
    window.addEventListener("message", async (event) => {
        // Only accept messages from same origin or trusted sources
        if (event.source !== window || !event.data || typeof event.data !== "object") {
            return;
        }

        const { type } = event.data;

        // A. Handshake Ping
        if (type === "ARCLENT_CHECK_EXTENSION" || type === "ARCLENT_PING") {
            window.postMessage({
                type: "ARCLENT_EXTENSION_PONG",
                installed: true,
                version: "1.0.0",
                name: "Arclent Instagram Assistant"
            }, "*");
            return;
        }

        // B. Dispatch Outreach Request
        if (type === "ARCLENT_INSTAGRAM_OUTREACH") {
            try {
                chrome.runtime.sendMessage(event.data, (response) => {
                    const lastError = chrome.runtime.lastError;
                    window.postMessage({
                        type: "ARCLENT_INSTAGRAM_OUTREACH_ACK",
                        sessionId: event.data.sessionId,
                        username: event.data.username,
                        response: response || null,
                        error: lastError ? lastError.message : null
                    }, "*");
                });
            } catch (err) {
                window.postMessage({
                    type: "ARCLENT_INSTAGRAM_OUTREACH_ACK",
                    sessionId: event.data.sessionId,
                    error: err.message
                }, "*");
            }
        }
    });

    // 4. Relay background service worker messages to the web page
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message && typeof message === "object") {
            window.postMessage(message, "*");
            sendResponse({ relayed: true });
        }
        return true;
    });

    console.log("[Arclent Extension] Bridge connected with Arclent web app.");
})();
