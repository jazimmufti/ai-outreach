/**
 * Arclent Instagram Outreach Assistant — Content Script (Manifest V3)
 * Injected on https://www.instagram.com/*
 *
 * CRITICAL SAFETY REQUIREMENT:
 * This script will NEVER click Send, submit a form, or trigger Enter keypresses.
 * Message auto-fill stops immediately once text is placed in the composer for user review.
 */

(() => {
    // Prevent duplicate injection
    if (window.__ARCLENT_CONTENT_SCRIPT_INITIALIZED__) return;
    window.__ARCLENT_CONTENT_SCRIPT_INITIALIZED__ = true;

    console.log("[Arclent Extension] Content script initialized on Instagram.");

    // --------------------------------------------------------------------------
    // State & Helpers
    // --------------------------------------------------------------------------
    let isProcessing = false;
    let lastInsertedSessionId = null;
    let floatingBanner = null;

    function getCleanCurrentPath() {
        return window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();
    }

    function isLoginScreen() {
        const path = getCleanCurrentPath();
        if (path === "accounts/login" || path.startsWith("accounts/emailsignup")) return true;
        const passwordInput = document.querySelector('input[type="password"], input[name="password"]');
        const loginBtn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => {
            const t = (b.textContent || "").trim().toLowerCase();
            return t === "log in" || t === "sign up";
        });
        return Boolean(passwordInput && loginBtn);
    }

    function normalizeText(str) {
        return (str || "").replace(/\s+/g, " ").trim();
    }

    // --------------------------------------------------------------------------
    // In-Page Notification UI (Non-intrusive Floating Card)
    // --------------------------------------------------------------------------
    function removeFloatingBanner() {
        if (floatingBanner && floatingBanner.parentNode) {
            floatingBanner.parentNode.removeChild(floatingBanner);
            floatingBanner = null;
        }
    }

    function showFloatingBanner({ title, message, type = "success", showCopyBtn = false, copyText = "" }) {
        removeFloatingBanner();

        const banner = document.createElement("div");
        banner.id = "arclent-floating-banner";
        banner.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999999;
            background: #0E3929;
            color: #FFFFFF;
            border: 2px solid #00D26A;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 380px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            animation: arclentSlideIn 0.3s ease-out;
        `;

        const styleEl = document.createElement("style");
        styleEl.textContent = `
            @keyframes arclentSlideIn {
                from { transform: translateY(20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styleEl);

        const icon = type === "success" ? "✓" : type === "warning" ? "!" : "✕";
        const iconColor = type === "success" ? "#00D26A" : type === "warning" ? "#F59E0B" : "#EF4444";

        banner.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: ${iconColor}; color: #000; font-weight: 800; font-size: 13px;">${icon}</span>
                    <strong style="font-size: 14px; color: #FFFFFF; letter-spacing: -0.2px;">${title}</strong>
                </div>
                <button id="arclent-banner-close" style="background: transparent; border: none; color: #9CA3AF; cursor: pointer; font-size: 16px; padding: 0 4px; line-height: 1;">✕</button>
            </div>
            <p style="margin: 0; font-size: 13px; line-height: 1.45; color: #D1D5DB;">
                ${message}
            </p>
            ${showCopyBtn ? `
                <div style="margin-top: 6px; display: flex; gap: 8px;">
                    <button id="arclent-banner-copy-btn" style="background: #00D26A; color: #000; border: none; border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: 700; cursor: pointer;">
                        📋 Copy Message to Clipboard
                    </button>
                </div>
            ` : ""}
        `;

        document.body.appendChild(banner);
        floatingBanner = banner;

        const closeBtn = banner.querySelector("#arclent-banner-close");
        if (closeBtn) closeBtn.onclick = removeFloatingBanner;

        if (showCopyBtn && copyText) {
            const copyBtn = banner.querySelector("#arclent-banner-copy-btn");
            if (copyBtn) {
                copyBtn.onclick = async () => {
                    try {
                        await navigator.clipboard.writeText(copyText);
                        copyBtn.textContent = "✓ Copied to Clipboard!";
                        setTimeout(() => { if (copyBtn) copyBtn.textContent = "📋 Copy Message to Clipboard"; }, 2500);
                    } catch (_) {}
                };
            }
        }
    }

    // --------------------------------------------------------------------------
    // Resilient Element Search (No Fragile Obfuscated CSS Classes)
    // --------------------------------------------------------------------------
    function waitForElement(selectorFn, timeoutMs = 15000, intervalMs = 250) {
        return new Promise((resolve) => {
            const existing = selectorFn();
            if (existing) {
                resolve(existing);
                return;
            }

            const startTime = Date.now();
            const interval = setInterval(() => {
                const el = selectorFn();
                if (el) {
                    clearInterval(interval);
                    resolve(el);
                } else if (Date.now() - startTime >= timeoutMs) {
                    clearInterval(interval);
                    resolve(null);
                }
            }, intervalMs);
        });
    }

    // 1. Locate the Profile "Message" Button
    function findInstagramMessageButton() {
        const candidates = Array.from(document.querySelectorAll('button, div[role="button"], a[role="button"], a[href*="/direct/t/"], a[href*="/direct/new/"]'));
        
        for (const el of candidates) {
            const text = (el.textContent || "").trim().toLowerCase();
            const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
            const title = (el.getAttribute("title") || "").toLowerCase();

            if (text === "message" || text === "send message" || ariaLabel === "message" || ariaLabel === "send message" || title === "message") {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return el;
                }
            }
        }

        const header = document.querySelector("header, main header");
        if (header) {
            const headerBtns = Array.from(header.querySelectorAll('button, div[role="button"]'));
            for (const b of headerBtns) {
                const text = (b.innerText || b.textContent || "").trim().toLowerCase();
                if (text.includes("message")) {
                    return b;
                }
            }
        }

        const svgs = Array.from(document.querySelectorAll('svg[aria-label="Message"], svg[aria-label="Direct"], svg[aria-label="Share Post"]'));
        for (const svg of svgs) {
            const btn = svg.closest('button, div[role="button"], a');
            if (btn) return btn;
        }

        return null;
    }

    // 2. Locate the DM Message Composer
    function findInstagramComposer() {
        // Strategy A: Modern Lexical / Contenteditable textbox
        const editables = Array.from(document.querySelectorAll('div[contenteditable="true"], p[contenteditable="true"], span[contenteditable="true"]'));
        for (const el of editables) {
            const role = el.getAttribute("role");
            const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
            const placeholder = (el.getAttribute("aria-placeholder") || el.getAttribute("data-placeholder") || "").toLowerCase();

            if (role === "textbox" || ariaLabel.includes("message") || placeholder.includes("message") || el.hasAttribute("data-lexical-editor")) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return el;
                }
            }
        }

        // Strategy B: Any visible contenteditable in main / section / direct area
        for (const el of editables) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 15) {
                return el;
            }
        }

        // Strategy C: Textarea in DM container
        const textareas = Array.from(document.querySelectorAll('textarea'));
        for (const ta of textareas) {
            const placeholder = (ta.getAttribute("placeholder") || "").toLowerCase();
            if (placeholder.includes("message") || placeholder.includes("reply") || ta.closest('section, main, form')) {
                const rect = ta.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return ta;
                }
            }
        }

        return null;
    }

    // 3. Insert Text Correctly (React & Lexical State Compatible Without Duplication)
    function clearAndInsertLexicalText(composer, text) {
        if (!composer || !text) return false;

        const currentVal = (composer.innerText || composer.textContent || composer.value || "").trim();
        const targetVal = text.trim();

        // 1. If composer already contains exact target message, do nothing and return success
        if (normalizeText(currentVal) === normalizeText(targetVal)) {
            console.log("[Arclent Extension] Composer already contains the exact message.");
            return true;
        }

        composer.focus();

        // 2. Select and delete everything inside the composer
        try {
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(composer);
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand("delete", false, null);
        } catch (e) {
            console.warn("[Arclent Extension] Selection delete failed:", e);
        }

        // 3. Clear any remaining text content or child elements
        try {
            if ((composer.innerText || composer.textContent || "").trim().length > 0) {
                composer.innerHTML = "";
                composer.textContent = "";
            }
        } catch (_) {}

        // 4. Try insertion via DataTransfer ClipboardEvent (standard Lexical paste handler)
        let inserted = false;
        try {
            composer.focus();
            const dt = new DataTransfer();
            dt.setData("text/plain", targetVal);
            const pasteEv = new ClipboardEvent("paste", {
                clipboardData: dt,
                bubbles: true,
                cancelable: true
            });
            composer.dispatchEvent(pasteEv);

            const postPasteVal = (composer.innerText || composer.textContent || composer.value || "").trim();
            if (normalizeText(postPasteVal).includes(normalizeText(targetVal).substring(0, 30))) {
                inserted = true;
            }
        } catch (e) {
            console.warn("[Arclent Extension] Paste event failed:", e);
        }

        // 5. Fallback to execCommand("insertText") if paste did not insert
        if (!inserted) {
            try {
                composer.focus();
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(composer);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand("delete", false, null);
                const execOk = document.execCommand("insertText", false, targetVal);
                if (execOk) inserted = true;
            } catch (e) {
                console.warn("[Arclent Extension] execCommand insertText failed:", e);
            }
        }

        // 6. Direct value set if it's an input/textarea
        if (!inserted && (composer.tagName.toLowerCase() === "textarea" || composer.tagName.toLowerCase() === "input")) {
            composer.value = targetVal;
            inserted = true;
        }

        // 7. Dispatch input/change events for React state reconciliation
        try {
            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
        } catch (_) {}

        // 8. Deduplication safety check: if message appears multiple times in composer, wipe and re-insert once
        const checkVal = (composer.innerText || composer.textContent || composer.value || "").trim();
        const snippet = targetVal.substring(0, 30);
        let occurrences = 0;
        let pos = checkVal.indexOf(snippet);
        while (pos !== -1) {
            occurrences++;
            pos = checkVal.indexOf(snippet, pos + snippet.length);
        }

        if (occurrences > 1) {
            console.warn("[Arclent Extension] Duplicate message detected in composer. Wiping and re-inserting once...");
            try {
                composer.focus();
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(composer);
                selection.removeAllRanges();
                selection.addRange(range);
                document.execCommand("delete", false, null);
                document.execCommand("insertText", false, targetVal);
            } catch (_) {}
        }

        return true;
    }

    // 4. Verify Message Was Inserted
    function verifyMessageContent(composer, expectedText) {
        if (!composer || !expectedText) return false;
        const currentText = composer.innerText || composer.textContent || composer.value || "";
        const sample = normalizeText(expectedText).substring(0, Math.min(30, expectedText.length));
        return normalizeText(currentText).includes(sample);
    }

    // 5. Auto-Detect Logged-In User Handle on Instagram
    function extractLoggedInUsername() {
        const systemPages = new Set([
            "direct", "explore", "reels", "stories", "accounts", "p", "reel",
            "your_activity", "saved", "settings", "messages", "inbox", "api",
            "about", "developer", "legal", "terms", "privacy", "help", "requests",
            "home", "search", "notifications", "create", "profile", "more", "threads",
            "meta", "graphql", "feed", ""
        ]);

        // Method 1: Top-left header of Direct conversation / inbox sidebar (e.g. "jazimmufti" with chevron)
        const headerElements = Array.from(document.querySelectorAll('header span, header h1, header h2, div[role="button"] span, nav span'));
        for (const el of headerElements) {
            const text = (el.textContent || "").trim();
            if (text && /^[a-zA-Z0-9._]{2,30}$/.test(text)) {
                const lower = text.toLowerCase();
                if (!systemPages.has(lower) && !["messages", "requests", "primary", "general"].includes(lower)) {
                    const container = el.closest('header, div[role="button"], div[role="heading"]');
                    if (container) {
                        return text;
                    }
                }
            }
        }

        // Method 2: Avatar image alt attribute ("jazimmufti's profile picture")
        const avatarImgs = Array.from(document.querySelectorAll('img[alt*="profile picture"]'));
        for (const img of avatarImgs) {
            const alt = img.getAttribute("alt") || "";
            const match = alt.match(/^([^']+)'s profile picture/i);
            if (match && match[1]) {
                const u = match[1].replace(/^@+/, "").trim();
                if (u && !systemPages.has(u.toLowerCase())) {
                    return u;
                }
            }
        }

        // Method 3: Left navigation profile link with avatar or profile icon / text
        const navLinks = Array.from(document.querySelectorAll('nav a[href^="/"], div[role="navigation"] a[href^="/"], a[href^="/"][role="link"]'));
        for (const link of navLinks) {
            const href = link.getAttribute("href") || "";
            const clean = href.replace(/^\/+|\/+$/g, "").split("?")[0].split("#")[0].trim();
            if (clean && !clean.includes("/") && !systemPages.has(clean.toLowerCase())) {
                if (link.querySelector('img[alt*="profile picture"]') ||
                    link.querySelector('svg[aria-label="Profile"], svg[aria-label="Your profile"]') ||
                    (link.textContent || "").toLowerCase().includes("profile")) {
                    return clean;
                }
            }
        }

        // Method 4: Any user profile anchor in navigation
        for (const link of navLinks) {
            const href = link.getAttribute("href") || "";
            const clean = href.replace(/^\/+|\/+$/g, "").split("?")[0].split("#")[0].trim();
            if (clean && !clean.includes("/") && !systemPages.has(clean.toLowerCase())) {
                return clean;
            }
        }

        return null;
    }

    // --------------------------------------------------------------------------
    // Main Orchestration Flow
    // --------------------------------------------------------------------------
    async function processPendingOutreach() {
        if (isProcessing) return;

        let sessionData = null;
        try {
            const data = await chrome.storage.local.get("activeOutreachSession");
            sessionData = data.activeOutreachSession;
        } catch (e) {
            return;
        }

        if (!sessionData || sessionData.status !== "pending") {
            return;
        }

        if (lastInsertedSessionId === sessionData.sessionId) {
            return;
        }

        isProcessing = true;
        console.log("[Arclent Extension] Processing pending outreach for:", sessionData.username);

        try {
            // 1. Check Login State
            if (isLoginScreen()) {
                showFloatingBanner({
                    title: "Instagram Login Required",
                    message: `Please log into your Instagram account in this tab. Your Arclent message for @${sessionData.username} will be prepared as soon as you log in.`,
                    type: "warning"
                });
                isProcessing = false;
                return;
            }

            const currentPath = getCleanCurrentPath();
            const targetUser = (sessionData.username || "").toLowerCase().replace(/^@+/, "");

            // 2. Are we already in a direct message composer or profile?
            const isDirectPage = currentPath.startsWith("direct/");
            const isProfilePage = currentPath === targetUser || currentPath.startsWith(`${targetUser}/`);

            // Step A: If on profile page, locate Message button and click it once
            if (isProfilePage && !isDirectPage) {
                console.log("[Arclent Extension] On creator profile page. Finding Message button...");
                const messageBtn = await waitForElement(findInstagramMessageButton, 10000);

                if (messageBtn) {
                    console.log("[Arclent Extension] Found Message button. Clicking to open DM...");
                    messageBtn.click();
                    // Let navigation to /direct/t/... occur and trigger next step cleanly
                    isProcessing = false;
                    return;
                } else {
                    console.warn("[Arclent Extension] Message button not found on profile. Attempting direct navigation...");
                    window.location.href = `https://ig.me/m/${encodeURIComponent(targetUser)}`;
                    isProcessing = false;
                    return;
                }
            }

            // Step B: Wait for DM message composer to appear
            console.log("[Arclent Extension] Locating message composer...");
            const composer = await waitForElement(findInstagramComposer, 15000);

            if (!composer) {
                console.error("[Arclent Extension] Could not locate message composer.");
                showFloatingBanner({
                    title: "Composer Not Detected",
                    message: `We opened @${sessionData.username}'s conversation, but couldn't detect the composer. Click the message box below to paste your message.`,
                    type: "warning",
                    showCopyBtn: true,
                    copyText: sessionData.message
                });

                await chrome.runtime.sendMessage({
                    type: "ARCLENT_INSTAGRAM_DM_FAILED",
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    reason: "Message composer element not found."
                }).catch(() => {});

                sessionData.status = "failed";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});
                isProcessing = false;
                return;
            }

            // Step C: Insert the Message cleanly (clears existing draft first)
            console.log("[Arclent Extension] Composer found. Inserting message draft cleanly...");
            const inserted = clearAndInsertLexicalText(composer, sessionData.message);
            await new Promise(r => setTimeout(r, 400));
            const verified = verifyMessageContent(composer, sessionData.message);

            if (verified || inserted) {
                console.log("[Arclent Extension] ✓ Message successfully inserted into composer. STOPPING (user must click send).");

                // Mark session as completed and remember session ID
                lastInsertedSessionId = sessionData.sessionId;
                sessionData.status = "completed";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});

                // Auto-detect logged-in user handle on Instagram
                const loggedInUser = extractLoggedInUsername();
                if (loggedInUser) {
                    console.log("[Arclent Extension] Detected logged-in username:", loggedInUser);
                }

                // If backend origin is present, directly update the session backend as well
                const backendOrigin = sessionData.backendOrigin || (sessionData.source === "arclent" ? "https://ai-outreach-production-8dcc.up.railway.app" : null);
                if (loggedInUser && backendOrigin && sessionData.sessionId) {
                    try {
                        fetch(`${backendOrigin}/api/outreach/record-social-outreach`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                session_id: sessionData.sessionId,
                                platform: "Instagram",
                                sender_handle: loggedInUser,
                                sender_identity: `${loggedInUser} on Arclent`
                            })
                        }).catch(() => {});
                    } catch (_) {}
                }

                // Show clear success banner guiding user to review and click Send manually
                showFloatingBanner({
                    title: "✓ Message Ready",
                    message: `Your outreach message has been inserted for <strong>@${sessionData.username}</strong>.<br><br><strong>Please review the message and click Send in Instagram.</strong>`,
                    type: "success"
                });

                // Notify background service worker & Arclent web app
                await chrome.runtime.sendMessage({
                    type: "ARCLENT_INSTAGRAM_DM_READY",
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    senderHandle: loggedInUser,
                    success: true
                }).catch(() => {});

            } else {
                console.warn("[Arclent Extension] Verification failed after insertion.");
                showFloatingBanner({
                    title: "Message Copied",
                    message: `We couldn't automatically write into the box. Your message has been copied to the clipboard — please paste and send.`,
                    type: "warning",
                    showCopyBtn: true,
                    copyText: sessionData.message
                });

                await chrome.runtime.sendMessage({
                    type: "ARCLENT_INSTAGRAM_DM_FAILED",
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    reason: "Verification failed after DOM insertion."
                }).catch(() => {});
            }

        } catch (err) {
            console.error("[Arclent Extension] Error during outreach processing:", err);
        } finally {
            isProcessing = false;
        }
    }

    // --------------------------------------------------------------------------
    // URL Change & SPA Observer
    // --------------------------------------------------------------------------
    let lastUrl = window.location.href;
    const observer = new MutationObserver(() => {
        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            console.log("[Arclent Extension] Detected SPA URL navigation to:", lastUrl);
            setTimeout(processPendingOutreach, 800);
        }
    });

    observer.observe(document, { subtree: true, childList: true });

    // Initial check on load
    setTimeout(processPendingOutreach, 1000);

    // Listen for manual trigger from popup or background
    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
        if (msg && msg.type === "TRIGGER_DM_AUTOFILL") {
            processPendingOutreach();
            sendResponse({ status: "processing" });
        }
        return true;
    });

})();
