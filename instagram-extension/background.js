/**
 * Arclent Instagram Outreach Assistant — Background Service Worker (Manifest V3)
 * Manages outreach sessions, Instagram tab orchestration, and messaging between Arclent and Instagram.
 */

// Helper to normalize Instagram username
function normalizeUsername(raw) {
    if (!raw) return "";
    let u = String(raw).trim();
    u = u.replace(/^https?:\/\/(www\.)?(instagram\.com|instagr\.am|ig\.me\/m)\//i, "");
    u = u.split("?")[0].split("#")[0].replace(/\/+$/, "").replace(/^@+/, "").trim();
    return u;
}

// Broadcast message to all active Arclent web app tabs
async function notifyArclentTabs(payload) {
    const arclentPatterns = [
        "http://localhost/*",
        "http://127.0.0.1/*",
        "https://*.arclent.com/*",
        "https://arclent.com/*",
        "https://*.up.railway.app/*",
        "https://ai-outreach-production-8dcc.up.railway.app/*"
    ];

    try {
        const tabs = await chrome.tabs.query({ url: arclentPatterns });
        for (const tab of tabs) {
            try {
                await chrome.tabs.sendMessage(tab.id, payload);
            } catch (err) {
                // Tab may not have content script ready yet; ignore
            }
        }
    } catch (e) {
        console.warn("[Arclent Extension] Error notifying Arclent tabs:", e);
    }
}

// Main message handler
async function handleIncomingMessage(request, sender) {
    if (!request || typeof request !== "object") {
        return { error: "Invalid request payload" };
    }

    const { type } = request;

    // 1. Handshake / Ping
    if (type === "ARCLENT_CHECK_EXTENSION" || type === "PING") {
        return {
            installed: true,
            version: chrome.runtime.getManifest().version,
            name: chrome.runtime.getManifest().name
        };
    }

    // 2. Dispatch Outreach
    if (type === "ARCLENT_INSTAGRAM_OUTREACH") {
        const username = normalizeUsername(request.username);
        const message = request.message;
        const sessionId = request.sessionId;

        if (!username || !message) {
            return { error: "Missing required fields (username, message)" };
        }

        const sessionData = {
            username: username,
            message: message,
            sessionId: sessionId || null,
            source: request.source || "arclent",
            status: "pending",
            createdAt: Date.now(),
            targetUrl: `https://www.instagram.com/${username}/`
        };

        // Persist session in chrome.storage.local
        await chrome.storage.local.set({ activeOutreachSession: sessionData });

        // Look for existing Instagram tab
        let targetTab = null;
        try {
            const existingTabs = await chrome.tabs.query({ url: "https://www.instagram.com/*" });
            if (existingTabs.length > 0) {
                targetTab = existingTabs[0];
                await chrome.tabs.update(targetTab.id, {
                    url: `https://www.instagram.com/${username}/`,
                    active: true
                });
                if (targetTab.windowId) {
                    await chrome.windows.update(targetTab.windowId, { focused: true });
                }
            } else {
                targetTab = await chrome.tabs.create({
                    url: `https://www.instagram.com/${username}/`,
                    active: true
                });
            }

            sessionData.tabId = targetTab.id;
            await chrome.storage.local.set({ activeOutreachSession: sessionData });

            return {
                success: true,
                status: "navigating",
                username: username,
                sessionId: sessionId,
                tabId: targetTab.id
            };
        } catch (err) {
            console.error("[Arclent Extension] Error opening Instagram tab:", err);
            return { error: `Failed to open Instagram tab: ${err.message}` };
        }
    }

    // 3. DM Ready confirmation from content.js
    if (type === "ARCLENT_INSTAGRAM_DM_READY") {
        const { username, sessionId } = request;
        const stored = await chrome.storage.local.get("activeOutreachSession");
        if (stored.activeOutreachSession) {
            stored.activeOutreachSession.status = "ready";
            stored.activeOutreachSession.readyAt = Date.now();
            await chrome.storage.local.set({ activeOutreachSession: stored.activeOutreachSession });
        }

        // Set green check badge
        try {
            await chrome.action.setBadgeText({ text: "✓" });
            await chrome.action.setBadgeBackgroundColor({ color: "#22C55E" });
            setTimeout(async () => {
                try {
                    await chrome.action.setBadgeText({ text: "" });
                } catch (_) {}
            }, 6000);
        } catch (_) {}

        // Notify Arclent web app
        await notifyArclentTabs({
            type: "ARCLENT_INSTAGRAM_DM_READY",
            username: username || (stored.activeOutreachSession ? stored.activeOutreachSession.username : null),
            sessionId: sessionId || (stored.activeOutreachSession ? stored.activeOutreachSession.sessionId : null),
            success: true
        });

        return { acknowledged: true };
    }

    // 4. DM Failed notification from content.js
    if (type === "ARCLENT_INSTAGRAM_DM_FAILED") {
        const { username, sessionId, reason } = request;
        const stored = await chrome.storage.local.get("activeOutreachSession");
        if (stored.activeOutreachSession) {
            stored.activeOutreachSession.status = "failed";
            stored.activeOutreachSession.errorReason = reason;
            await chrome.storage.local.set({ activeOutreachSession: stored.activeOutreachSession });
        }

        // Notify Arclent web app
        await notifyArclentTabs({
            type: "ARCLENT_INSTAGRAM_DM_FAILED",
            username: username || (stored.activeOutreachSession ? stored.activeOutreachSession.username : null),
            sessionId: sessionId || (stored.activeOutreachSession ? stored.activeOutreachSession.sessionId : null),
            reason: reason || "Could not automatically prepare Instagram DM."
        });

        return { acknowledged: true };
    }

    // 5. Get current active session status
    if (type === "GET_OUTREACH_STATUS") {
        const data = await chrome.storage.local.get("activeOutreachSession");
        return { session: data.activeOutreachSession || null };
    }

    // 6. Clear active session
    if (type === "CLEAR_OUTREACH_SESSION") {
        await chrome.storage.local.remove("activeOutreachSession");
        return { success: true };
    }

    return { error: `Unknown message type: ${type}` };
}

// Listen to internal messages (content script, popup, bridge)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    handleIncomingMessage(request, sender)
        .then((res) => sendResponse(res))
        .catch((err) => sendResponse({ error: err.message }));
    return true; // Keep channel open for async response
});

// Listen to external messages from Arclent web app
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
    handleIncomingMessage(request, sender)
        .then((res) => sendResponse(res))
        .catch((err) => sendResponse({ error: err.message }));
    return true; // Keep channel open for async response
});
