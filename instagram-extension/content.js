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
        // Strategy A: Standard button/link with text "Message" or "Send message"
        const candidates = Array.from(document.querySelectorAll('button, div[role="button"], a[role="button"], a[href*="/direct/t/"], a[href*="/direct/new/"]'));
        
        for (const el of candidates) {
            // Check visible text
            const text = (el.textContent || "").trim().toLowerCase();
            const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
            const title = (el.getAttribute("title") || "").toLowerCase();

            if (text === "message" || text === "send message" || ariaLabel === "message" || ariaLabel === "send message" || title === "message") {
                // Check if element is visible
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    return el;
                }
            }
        }

        // Strategy B: Header section buttons
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

        // Strategy C: Direct message icon / svg
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

    // 3. Insert Text Correctly (React & Lexical State Compatible)
    function insertMessageIntoComposer(composer, text) {
        if (!composer || !text) return false;

        composer.focus();

        if (composer.tagName.toLowerCase() === "textarea" || composer.tagName.toLowerCase() === "input") {
            composer.value = text;
            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
            return true;
        }

        // For contenteditable / Lexical:
        try {
            // Select all existing content
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(composer);
            selection.removeAllRanges();
            selection.addRange(range);

            // Execute insertText command (triggers React & DOM sync)
            const success = document.execCommand("insertText", false, text);

            // Dispatch synthetic InputEvents
            composer.dispatchEvent(
                new InputEvent("input", {
                    bubbles: true,
                    cancelable: true,
                    inputType: "insertText",
                    data: text
                })
            );
            composer.dispatchEvent(new Event("change", { bubbles: true }));

            return true;
        } catch (err) {
            console.warn("[Arclent Extension] execCommand insertText failed, falling back to innerText:", err);
            try {
                composer.innerText = text;
                composer.dispatchEvent(new InputEvent("input", { bubbles: true, data: text }));
                return true;
            } catch (_) {
                return false;
            }
        }
    }

    // 4. Verify Message Was Inserted
    function verifyMessageContent(composer, expectedText) {
        if (!composer || !expectedText) return false;
        const currentText = (composer.innerText || composer.textContent || composer.value || "").trim();
        // Check if a substantial part of the message is present
        const sample = expectedText.trim().substring(0, Math.min(30, expectedText.length));
        return currentText.includes(sample);
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

            // Step A: If on profile page, locate Message button and click it
            if (isProfilePage && !isDirectPage) {
                console.log("[Arclent Extension] On creator profile page. Finding Message button...");
                const messageBtn = await waitForElement(findInstagramMessageButton, 10000);

                if (messageBtn) {
                    console.log("[Arclent Extension] Found Message button. Clicking to open DM...");
                    messageBtn.click();
                    // Allow navigation to begin
                    await new Promise(r => setTimeout(r, 1200));
                } else {
                    console.warn("[Arclent Extension] Message button not found on profile. Attempting direct navigation...");
                    // Try direct shortlink or direct inbox fallback
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

                isProcessing = false;
                return;
            }

            // Step C: Insert the Message
            console.log("[Arclent Extension] Composer found. Inserting message draft...");
            const inserted = insertMessageIntoComposer(composer, sessionData.message);
            await new Promise(r => setTimeout(r, 400));
            const verified = verifyMessageContent(composer, sessionData.message);

            if (verified || inserted) {
                console.log("[Arclent Extension] ✓ Message successfully inserted into composer. STOPPING (user must click send).");

                // Auto-detect logged-in user handle on Instagram if available
                let loggedInUser = null;
                try {
                    const profileLinks = Array.from(document.querySelectorAll('a[href^="/"][role="link"], nav a[href^="/"]'));
                    for (const link of profileLinks) {
                        const href = link.getAttribute("href") || "";
                        const cleanHref = href.replace(/^\/+|\/+$/g, "").split("/")[0];
                        const systemPages = ["direct", "explore", "reels", "stories", "accounts", "p", "reel", "your_activity", "saved", "settings", "messages"];
                        if (cleanHref && !systemPages.includes(cleanHref.toLowerCase()) && !cleanHref.includes("?")) {
                            if (link.querySelector('img[alt*="profile picture"]') || (link.textContent || "").toLowerCase().includes("profile")) {
                                loggedInUser = cleanHref;
                                break;
                            }
                        }
                    }
                    if (!loggedInUser) {
                        const avatarImgs = Array.from(document.querySelectorAll('img[alt*="profile picture"]'));
                        for (const img of avatarImgs) {
                            const alt = img.getAttribute("alt") || "";
                            const match = alt.match(/^([^']+)'s profile picture/i);
                            if (match && match[1]) {
                                loggedInUser = match[1];
                                break;
                            }
                        }
                    }
                } catch (e) {
                    console.warn("[Arclent Extension] Could not detect logged-in username:", e);
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
