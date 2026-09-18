/**
 * Arclent Outreach Assistant — Bridge Script (Manifest V3)
 * Injected into Arclent web app origins (localhost, 127.0.0.1, up.railway.app, arclent.com)
 * Enables seamless, bidirectional communication between the Arclent web application and the multi-platform extension.
 */

(() => {
    function markAndAnnouncePresence() {
        if (document.documentElement) {
            document.documentElement.setAttribute("data-arclent-extension", "installed");
            document.documentElement.setAttribute("data-arclent-instagram-extension", "installed");
            document.documentElement.dataset.arclentExtension = "installed";
            document.documentElement.dataset.arclentInstagramExtension = "installed";
            document.documentElement.dataset.arclentPlatforms = "instagram,x,discord,facebook";
            document.documentElement.dataset.arclentExtensionVersion = "1.2.1";
        }

        // Post announcement to main window
        window.postMessage({
            type: "ARCLENT_EXTENSION_PONG",
            installed: true,
            version: "1.2.1",
            name: "Arclent Outreach Assistant",
            platforms: ["instagram", "x", "discord", "facebook"]
        }, "*");

        // Dispatch DOM CustomEvents
        window.dispatchEvent(new CustomEvent("ARCLENT_EXTENSION_READY", {
            detail: {
                installed: true,
                version: "1.2.1",
                name: "Arclent Outreach Assistant",
                platforms: ["instagram", "x", "discord", "facebook"]
            }
        }));

        // Backwards compatibility event
        window.dispatchEvent(new CustomEvent("ARCLENT_INSTAGRAM_EXTENSION_READY", {
            detail: {
                installed: true,
                version: "1.2.1",
                name: "Arclent Outreach Assistant",
                platforms: ["instagram", "x", "discord", "facebook"]
            }
        }));
    }

    // Mark immediately
    markAndAnnouncePresence();

    // Re-announce on DOM ready and window load to guarantee detection
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", markAndAnnouncePresence);
    }
    window.addEventListener("load", markAndAnnouncePresence);

    // Listen for window postMessages from Arclent web app
    window.addEventListener("message", async (event) => {
        if (event.source !== window || !event.data || typeof event.data !== "object") {
            return;
        }

        const { type } = event.data;

        // A. Handshake Ping
        if (type === "ARCLENT_CHECK_EXTENSION" || type === "ARCLENT_PING") {
            markAndAnnouncePresence();
            return;
        }

        // B. Dispatch Outreach Request (Multi-platform or Instagram legacy)
        if (type === "ARCLENT_SOCIAL_OUTREACH" || type === "ARCLENT_INSTAGRAM_OUTREACH") {
            try {
                chrome.runtime.sendMessage(event.data, (response) => {
                    const lastError = chrome.runtime.lastError;
                    window.postMessage({
                        type: type === "ARCLENT_SOCIAL_OUTREACH" ? "ARCLENT_SOCIAL_OUTREACH_ACK" : "ARCLENT_INSTAGRAM_OUTREACH_ACK",
                        sessionId: event.data.sessionId,
                        platform: event.data.platform || "instagram",
                        username: event.data.username || event.data.handle,
                        response: response || null,
                        error: lastError ? lastError.message : null
                    }, "*");
                });
            } catch (err) {
                window.postMessage({
                    type: type === "ARCLENT_SOCIAL_OUTREACH" ? "ARCLENT_SOCIAL_OUTREACH_ACK" : "ARCLENT_INSTAGRAM_OUTREACH_ACK",
                    sessionId: event.data.sessionId,
                    error: err.message
                }, "*");
            }
        }
    });

    // Relay background service worker messages to the web page
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message && typeof message === "object") {
            window.postMessage(message, "*");
            sendResponse({ relayed: true });
        }
        return true;
    });

    console.log("[Arclent Extension] Multi-platform bridge connected with Arclent web app.");
})();
