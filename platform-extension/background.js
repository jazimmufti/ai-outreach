/**
 * Arclent Outreach Assistant — Background Service Worker (Manifest V3)
 * Manages outreach sessions, tab orchestration, and messaging across Instagram, X, Discord, and Facebook.
 */

// Helper to normalize platform key
function normalizePlatform(raw) {
    const p = String(raw || "").trim().toLowerCase();
    if (p.includes("instagram") || p === "ig") return "instagram";
    if (p.includes("twitter") || p.includes("x") || p === "x.com") return "x";
    if (p.includes("discord")) return "discord";
    if (p.includes("facebook") || p.includes("messenger") || p === "fb") return "facebook";
    return "instagram";
}

// Helper to normalize username / handle
function normalizeUsername(raw, platform = "instagram") {
    if (!raw) return "";
    let u = String(raw).trim();
    if (platform === "instagram") {
        u = u.replace(/^https?:\/\/(www\.)?(instagram\.com|instagr\.am|ig\.me\/m)\//i, "");
    } else if (platform === "x") {
        u = u.replace(/^https?:\/\/(www\.)?(x\.com|twitter\.com)\//i, "");
    } else if (platform === "facebook") {
        u = u.replace(/^https?:\/\/(www\.)?(facebook\.com|m\.me|messenger\.com)\//i, "");
    } else if (platform === "discord") {
        u = u.replace(/^https?:\/\/(www\.)?discord\.com\/users\//i, "");
    }
    u = u.split("?")[0].split("#")[0].replace(/\/+$/, "").replace(/^@+/, "").trim();
    return u;
}

// Get initial target URL and tab match patterns per platform
function getPlatformConfig(platform, username, userId) {
    const p = normalizePlatform(platform);
    const cleanUser = normalizeUsername(username, p);
    const cleanId = String(userId || cleanUser).trim().replace(/^@+/, "");

    switch (p) {
        case "x":
            return {
                platform: "x",
                displayName: "X (Twitter)",
                targetUrl: cleanUser ? `https://x.com/${cleanUser}` : "https://x.com/home",
                loginUrl: "https://x.com/i/flow/login",
                urlPatterns: ["https://*.x.com/*", "https://x.com/*", "https://*.twitter.com/*", "https://twitter.com/*"]
            };
        case "discord":
            return {
                platform: "discord",
                displayName: "Discord",
                targetUrl: cleanId && /^\d{17,20}$/.test(cleanId) ? `https://discord.com/users/${cleanId}` : "https://discord.com/channels/@me",
                loginUrl: "https://discord.com/login",
                urlPatterns: ["https://*.discord.com/*", "https://discord.com/*"]
            };
        case "facebook":
            return {
                platform: "facebook",
                displayName: "Facebook",
                targetUrl: cleanUser ? `https://www.facebook.com/${cleanUser}` : "https://www.facebook.com/messages",
                loginUrl: "https://www.facebook.com/login.php",
                urlPatterns: ["https://*.facebook.com/*", "https://facebook.com/*", "https://*.messenger.com/*", "https://messenger.com/*"]
            };
        case "instagram":
        default:
            return {
                platform: "instagram",
                displayName: "Instagram",
                targetUrl: cleanUser ? `https://www.instagram.com/${cleanUser}/` : "https://www.instagram.com/direct/inbox/",
                loginUrl: "https://www.instagram.com/accounts/login/",
                urlPatterns: ["https://*.instagram.com/*", "https://instagram.com/*"]
            };
    }
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
    if (type === "ARCLENT_CHECK_EXTENSION" || type === "PING" || type === "ARCLENT_PING") {
        return {
            installed: true,
            version: chrome.runtime.getManifest().version,
            name: chrome.runtime.getManifest().name,
            platforms: ["instagram", "x", "discord", "facebook"]
        };
    }

    // 2. Dispatch Multi-Platform Outreach
    if (type === "ARCLENT_SOCIAL_OUTREACH" || type === "ARCLENT_INSTAGRAM_OUTREACH") {
        const platform = normalizePlatform(request.platform || (type === "ARCLENT_INSTAGRAM_OUTREACH" ? "instagram" : ""));
        const username = normalizeUsername(request.username || request.handle, platform);
        const userId = request.userId || request.snowflakeId || (platform === "discord" ? username : null);
        const message = request.message || request.text;
        const sessionId = request.sessionId;

        if (!message) {
            return { error: "Missing required message content." };
        }

        const config = getPlatformConfig(platform, username, userId);

        const sessionData = {
            platform: config.platform,
            platformName: config.displayName,
            username: username,
            userId: userId,
            message: message,
            sessionId: sessionId || null,
            source: request.source || "arclent",
            backendOrigin: request.backendOrigin || null,
            senderHandle: request.senderHandle || null,
            status: "pending",
            createdAt: Date.now(),
            targetUrl: config.targetUrl,
            loginUrl: config.loginUrl
        };

        // Persist session in chrome.storage.local
        await chrome.storage.local.set({ activeOutreachSession: sessionData });

        // Find existing tab for this platform or open a new one
        let targetTab = null;
        try {
            const existingTabs = await chrome.tabs.query({ url: config.urlPatterns });
            if (existingTabs.length > 0) {
                targetTab = existingTabs[0];
                await chrome.tabs.update(targetTab.id, {
                    url: config.targetUrl,
                    active: true
                });
                if (targetTab.windowId) {
                    await chrome.windows.update(targetTab.windowId, { focused: true });
                }
            } else {
                targetTab = await chrome.tabs.create({
                    url: config.targetUrl,
                    active: true
                });
            }

            sessionData.tabId = targetTab.id;
            await chrome.storage.local.set({ activeOutreachSession: sessionData });

            return {
                success: true,
                status: "navigating",
                platform: config.platform,
                username: username,
                sessionId: sessionId,
                tabId: targetTab.id
            };
        } catch (err) {
            console.error(`[Arclent Extension] Error opening ${config.displayName} tab:`, err);
            return { error: `Failed to open ${config.displayName} tab: ${err.message}` };
        }
    }

    // 3. DM Ready confirmation from content.js
    if (type === "ARCLENT_SOCIAL_DM_READY" || type === "ARCLENT_INSTAGRAM_DM_READY") {
        const { username, sessionId, senderHandle, platform } = request;
        const stored = await chrome.storage.local.get("activeOutreachSession");
        const active = stored.activeOutreachSession || {};

        active.status = "ready";
        active.readyAt = Date.now();
        if (senderHandle) {
            active.senderHandle = senderHandle;
        }
        await chrome.storage.local.set({ activeOutreachSession: active });

        // Set green check badge
        try {
            await chrome.action.setBadgeText({ text: "✓" });
            await chrome.action.setBadgeBackgroundColor({ color: "#00D26A" });
            setTimeout(async () => {
                try {
                    await chrome.action.setBadgeText({ text: "" });
                } catch (_) {}
            }, 7000);
        } catch (_) {}

        // Notify Arclent web app
        const currentPlatform = platform || active.platform || "instagram";
        await notifyArclentTabs({
            type: "ARCLENT_SOCIAL_DM_READY",
            platform: currentPlatform,
            username: username || active.username,
            sessionId: sessionId || active.sessionId,
            senderHandle: senderHandle || active.senderHandle,
            success: true
        });

        // Also notify legacy listener if instagram
        if (currentPlatform === "instagram") {
            await notifyArclentTabs({
                type: "ARCLENT_INSTAGRAM_DM_READY",
                username: username || active.username,
                sessionId: sessionId || active.sessionId,
                senderHandle: senderHandle || active.senderHandle,
                success: true
            });
        }

        return { acknowledged: true };
    }

    // 4. DM Failed notification from content.js
    if (type === "ARCLENT_SOCIAL_DM_FAILED" || type === "ARCLENT_INSTAGRAM_DM_FAILED") {
        const { username, sessionId, reason, platform } = request;
        const stored = await chrome.storage.local.get("activeOutreachSession");
        const active = stored.activeOutreachSession || {};

        active.status = "failed";
        active.errorReason = reason;
        await chrome.storage.local.set({ activeOutreachSession: active });

        const currentPlatform = platform || active.platform || "instagram";

        // Notify Arclent web app
        const profUrl = request.profileUrl || (active.username && currentPlatform === "x" ? `https://x.com/${active.username}` : null);
        await notifyArclentTabs({
            type: "ARCLENT_SOCIAL_DM_FAILED",
            platform: currentPlatform,
            username: username || active.username,
            sessionId: sessionId || active.sessionId,
            profileUrl: profUrl,
            reason: reason || `Could not automatically prepare ${currentPlatform} DM.`
        });

        if (currentPlatform === "instagram") {
            await notifyArclentTabs({
                type: "ARCLENT_INSTAGRAM_DM_FAILED",
                username: username || active.username,
                sessionId: sessionId || active.sessionId,
                reason: reason || "Could not automatically prepare Instagram DM."
            });
        }

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
