/**
 * Arclent Outreach Assistant — Multi-Platform Popup Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
    const sessionBadge = document.getElementById("session-badge");
    const sessionEmptyText = document.getElementById("session-empty-text");
    const sessionDetails = document.getElementById("session-details");
    const sessionPlatform = document.getElementById("session-platform");
    const sessionUsername = document.getElementById("session-username");
    const sessionStatusText = document.getElementById("session-status-text");
    const sessionMessagePreview = document.getElementById("session-message-preview");
    const btnReTrigger = document.getElementById("btn-re-trigger");

    // Fetch active session from background
    try {
        const res = await chrome.runtime.sendMessage({ type: "GET_OUTREACH_STATUS" });
        const session = res?.session;

        if (session && (session.username || session.userId)) {
            sessionEmptyText.classList.add("hidden");
            sessionDetails.classList.remove("hidden");

            const platformName = session.platformName || (session.platform ? session.platform.toUpperCase() : "Instagram");
            if (sessionPlatform) {
                sessionPlatform.textContent = platformName;
            }

            const targetDisplay = session.username ? (session.username.startsWith("@") ? session.username : `@${session.username}`) : `ID ${session.userId}`;
            sessionUsername.textContent = targetDisplay;
            sessionMessagePreview.textContent = session.message || "";

            if (session.status === "ready" || session.status === "completed") {
                sessionBadge.textContent = "READY";
                sessionBadge.className = "badge ready";
                sessionStatusText.textContent = `✓ Message Inserted in ${platformName}`;
                sessionStatusText.style.color = "#00D26A";
            } else if (session.status === "waiting_for_login") {
                sessionBadge.textContent = "LOGIN";
                sessionBadge.className = "badge pending";
                sessionStatusText.textContent = `Waiting for ${platformName} sign-in...`;
                sessionStatusText.style.color = "#F59E0B";
            } else if (session.status === "pending") {
                sessionBadge.textContent = "PENDING";
                sessionBadge.className = "badge pending";
                sessionStatusText.textContent = `Navigating to DM in ${platformName}...`;
                sessionStatusText.style.color = "#F59E0B";
            } else if (session.status === "failed") {
                sessionBadge.textContent = "FAILED";
                sessionBadge.className = "badge failed";
                sessionStatusText.textContent = session.errorReason || `Could not prepare ${platformName} DM`;
                sessionStatusText.style.color = "#EF4444";
            } else {
                sessionBadge.textContent = "ACTIVE";
                sessionBadge.className = "badge";
                sessionStatusText.textContent = session.status || "Active";
            }

            if (btnReTrigger) {
                btnReTrigger.textContent = `Fill DM in ${platformName} Tab ↗`;
                btnReTrigger.onclick = async () => {
                    const platformPatterns = {
                        instagram: ["https://*.instagram.com/*", "https://instagram.com/*"],
                        x: ["https://*.x.com/*", "https://x.com/*", "https://*.twitter.com/*", "https://twitter.com/*"],
                        discord: ["https://*.discord.com/*", "https://discord.com/*"],
                        facebook: ["https://*.facebook.com/*", "https://facebook.com/*", "https://*.messenger.com/*", "https://messenger.com/*"]
                    };
                    const normPlatform = (session.platform || "instagram").toLowerCase();
                    const platformKey = normPlatform.includes("x") || normPlatform.includes("twitter") ? "x" :
                                        (normPlatform.includes("discord") ? "discord" :
                                        (normPlatform.includes("facebook") || normPlatform.includes("messenger") ? "facebook" : "instagram"));
                    const queryUrl = platformPatterns[platformKey] || ["https://*.instagram.com/*", "https://instagram.com/*"];
                    const tabs = await chrome.tabs.query({ url: queryUrl });
                    if (tabs.length > 0) {
                        await chrome.tabs.update(tabs[0].id, { active: true });
                        if (tabs[0].windowId) {
                            await chrome.windows.update(tabs[0].windowId, { focused: true }).catch(() => {});
                        }
                        await chrome.tabs.sendMessage(tabs[0].id, { type: "TRIGGER_DM_AUTOFILL" }).catch(() => {});
                    } else if (session.targetUrl) {
                        await chrome.tabs.create({ url: session.targetUrl, active: true });
                    }
                    window.close();
                };
            }
        } else {
            sessionBadge.textContent = "IDLE";
            sessionBadge.className = "badge";
            sessionEmptyText.classList.remove("hidden");
            sessionDetails.classList.add("hidden");
        }
    } catch (err) {
        console.warn("[Arclent Popup] Could not fetch session status:", err);
    }
});
