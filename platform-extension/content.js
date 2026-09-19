/**
 * Arclent Outreach Assistant — Multi-Platform Content Script (Manifest V3)
 * Supports: Instagram, X (Twitter), Discord (Web), and Facebook (Messenger).
 *
 * CRITICAL SAFETY REQUIREMENT:
 * This script will NEVER click Send, submit a form, or trigger Enter keypresses.
 * Message auto-fill stops immediately once text is placed in the composer for user review.
 */

(() => {
    // Prevent duplicate injection
    if (window.__ARCLENT_MULTI_CONTENT_SCRIPT_INITIALIZED__) return;
    window.__ARCLENT_MULTI_CONTENT_SCRIPT_INITIALIZED__ = true;

    // Detect current platform
    const host = window.location.hostname.toLowerCase();
    let currentPlatform = "unknown";
    if (host.includes("instagram.com") || host.includes("instagr.am")) {
        currentPlatform = "instagram";
    } else if (host.includes("x.com") || host.includes("twitter.com")) {
        currentPlatform = "x";
    } else if (host.includes("discord.com")) {
        currentPlatform = "discord";
    } else if (host.includes("facebook.com") || host.includes("messenger.com")) {
        currentPlatform = "facebook";
    }

    console.log(`[Arclent Extension] Content script initialized on platform: ${currentPlatform}`);

    // --------------------------------------------------------------------------
    // State & UI Helpers
    // --------------------------------------------------------------------------
    let isProcessing = false;
    let floatingBanner = null;
    let bannerDismissTimer = null;

    function removeFloatingBanner() {
        if (bannerDismissTimer) {
            clearTimeout(bannerDismissTimer);
            bannerDismissTimer = null;
        }
        if (floatingBanner && floatingBanner.parentNode) {
            floatingBanner.style.animation = "arclentFadeOut 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards";
            setTimeout(() => {
                if (floatingBanner && floatingBanner.parentNode) {
                    floatingBanner.parentNode.removeChild(floatingBanner);
                }
                floatingBanner = null;
            }, 350);
        }
    }

    async function copyTextToClipboard(text) {
        if (!text) return false;
        let success = false;
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                success = true;
            }
        } catch (_) {}

        if (!success) {
            try {
                const ta = document.createElement("textarea");
                ta.value = text;
                ta.style.position = "fixed";
                ta.style.left = "-9999px";
                ta.style.top = "-9999px";
                ta.style.opacity = "0";
                ta.setAttribute("readonly", "");
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                success = document.execCommand("copy");
                document.body.removeChild(ta);
            } catch (_) {}
        }
        return success;
    }

    function showFloatingBanner({ title, message, type = "success", showCopyBtn = false, copyText = "", autoDismiss = false, durationMs = 6000, buttonLabel = null }) {
        removeFloatingBanner();

        const borderColor = type === "warning" ? "#F59E0B" : type === "info" ? "#38BDF8" : type === "error" ? "#EF4444" : "#00D26A";
        const iconColor = type === "success" ? "#00D26A" : type === "warning" ? "#F59E0B" : type === "info" ? "#38BDF8" : "#EF4444";
        const icon = type === "success" ? "✓" : type === "warning" ? "⚠️" : type === "info" ? "ℹ" : "✕";
        const initialBtnText = buttonLabel || "📋 Copy Message to Clipboard";

        const banner = document.createElement("div");
        banner.id = "arclent-floating-banner";
        banner.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 2147483647;
            background: #0B2518;
            color: #FFFFFF;
            border: 2px solid ${borderColor};
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 400px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            animation: arclentSlideIn 0.3s ease-out forwards;
            transition: opacity 0.35s ease, transform 0.35s ease;
        `;

        if (!document.getElementById("arclent-banner-keyframes")) {
            const styleEl = document.createElement("style");
            styleEl.id = "arclent-banner-keyframes";
            styleEl.textContent = `
                @keyframes arclentSlideIn {
                    from { transform: translateY(24px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes arclentFadeOut {
                    from { transform: translateY(0); opacity: 1; }
                    to { transform: translateY(24px); opacity: 0; }
                }
            `;
            document.head.appendChild(styleEl);
        }

        banner.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: ${iconColor}; color: #000; font-weight: 800; font-size: 13px;">${icon}</span>
                    <strong style="font-size: 14px; color: #FFFFFF; letter-spacing: -0.2px;">${title}</strong>
                </div>
                <button id="arclent-banner-close" style="background: transparent; border: none; color: #9CA3AF; cursor: pointer; font-size: 16px; padding: 0 4px; line-height: 1;">✕</button>
            </div>
            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #D1D5DB;">
                ${message}
            </p>
            ${showCopyBtn ? `
                <div style="margin-top: 4px; display: flex; gap: 8px;">
                    <button id="arclent-banner-copy-btn" style="background: #00D26A; color: #000; border: none; border-radius: 6px; padding: 7px 14px; font-size: 12px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: background 0.2s ease;">
                        ${initialBtnText}
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
                    await copyTextToClipboard(copyText);
                    copyBtn.textContent = "✓ Copied to Clipboard!";
                    setTimeout(() => {
                        if (copyBtn) copyBtn.textContent = initialBtnText;
                    }, 2500);
                };
            }
        }

        if (autoDismiss) {
            bannerDismissTimer = setTimeout(() => {
                removeFloatingBanner();
            }, durationMs);
        }
    }

    // --------------------------------------------------------------------------
    // Resilient DOM Query Helper
    // --------------------------------------------------------------------------
    function waitForElement(selectorFn, timeoutMs = 12000, intervalMs = 250) {
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

    function normalizeText(str) {
        return (str || "").replace(/\s+/g, " ").trim();
    }

    function safeClick(el) {
        if (!el) return;
        try {
            el.focus();
            const opts = { bubbles: true, cancelable: true, view: window };
            el.dispatchEvent(new MouseEvent("pointerdown", opts));
            el.dispatchEvent(new MouseEvent("mousedown", opts));
            el.dispatchEvent(new MouseEvent("pointerup", opts));
            el.dispatchEvent(new MouseEvent("mouseup", opts));
            el.click();
        } catch (_) {
            try { el.click(); } catch (e) {}
        }
    }

    // --------------------------------------------------------------------------
    // Public Comment & Post Filter (Strict Non-DM Detector)
    // --------------------------------------------------------------------------
    function isCommentOrPostBox(el) {
        if (!el) return false;

        const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
        const placeholder = (el.getAttribute("placeholder") || el.getAttribute("aria-placeholder") || el.getAttribute("data-placeholder") || "").toLowerCase();
        const dataTestId = (el.getAttribute("data-testid") || "").toLowerCase();
        const title = (el.getAttribute("title") || "").toLowerCase();
        const name = (el.getAttribute("name") || "").toLowerCase();

        // Specific comment and post triggers
        const nonDmPhrases = [
            "comment", "write a comment", "write a public comment", "add a comment",
            "leave a comment", "post a comment", "comment as", "write an answer",
            "reply to", "post your reply", "tweet your reply",
            "what's on your mind", "whats on your mind", "create a post", "create post",
            "share a thought", "search facebook", "search messages", "search",
            "add a response", "post a response"
        ];

        for (const phrase of nonDmPhrases) {
            if (ariaLabel.includes(phrase) || placeholder.includes(phrase) || title.includes(phrase) || dataTestId.includes(phrase) || name.includes(phrase)) {
                return true;
            }
        }

        // Parent container selectors indicating comments, feeds, timelines, or search bars
        if (el.closest) {
            const forbiddenContainer = el.closest(
                'form[class*="comment" i], ' +
                'div[data-pagelet*="Comment" i], ' +
                'div[data-pagelet*="Feed" i], ' +
                'div[data-testid*="comment" i], ' +
                'div[data-testid*="UFI" i], ' +
                'div[data-testid="tweetTextarea_0"], ' +
                'div[data-testid*="reply" i], ' +
                'form[role="search"], ' +
                '[data-testid="SearchBox_Search_Input"], ' +
                'div[aria-label*="Create a post" i], ' +
                'div[aria-label*="What\'s on your mind" i], ' +
                'div[aria-label*="Comments" i]'
            );
            if (forbiddenContainer) return true;
        }

        return false;
    }

    // --------------------------------------------------------------------------
    // Universal Safe Composer Text Inserter
    // (Compatible with standard textarea, contenteditable, Lexical, and Slate.js)
    // --------------------------------------------------------------------------
    function insertMessageIntoComposer(composer, text) {
        if (!composer || !text) return false;

        // Strict guard: refuse to insert if element is a comment box or public post
        if (isCommentOrPostBox(composer)) {
            console.warn("[Arclent Extension] Rejected candidate: Element is a public comment or post box, not a DM composer.");
            return false;
        }

        // Immediately ensure the text is on the system clipboard as a reliable backup
        try {
            copyTextToClipboard(text);
        } catch (_) {}

        // If composer is a container wrapper, resolve the actual editable child
        if (composer.getAttribute && 
            composer.getAttribute("contenteditable") !== "true" && 
            composer.tagName.toLowerCase() !== "textarea" && 
            composer.tagName.toLowerCase() !== "input") {
            const innerEditable = composer.querySelector('[contenteditable="true"], textarea, input');
            if (innerEditable && !isCommentOrPostBox(innerEditable)) {
                composer = innerEditable;
            }
        }

        if (isCommentOrPostBox(composer)) {
            console.warn("[Arclent Extension] Rejected candidate: Resolved inner element is a public comment or post box.");
            return false;
        }

        // Prevent duplicate insertion into the same composer instance
        if (composer.dataset.arclentInserted === "true") {
            console.log("[Arclent Extension] Message already inserted in this composer instance.");
            return true;
        }

        // Check if composer already contains the exact message cleanly (e.g. user re-focused)
        const currentVal = normalizeText(composer.innerText || composer.textContent || composer.value || "");
        const sample = normalizeText(text).substring(0, Math.min(30, text.length));
        if (sample.length > 0 && currentVal.includes(sample) && currentVal.indexOf(sample) === currentVal.lastIndexOf(sample)) {
            console.log("[Arclent Extension] Message already populated cleanly in composer. Skipping re-insertion.");
            composer.dataset.arclentInserted = "true";
            return true;
        }

        composer.focus();
        try {
            composer.click();
        } catch (_) {}

        // 1. Textarea or Input elements
        if (composer.tagName.toLowerCase() === "textarea" || composer.tagName.toLowerCase() === "input") {
            composer.value = text;
            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
            composer.dataset.arclentInserted = "true";
            return true;
        }

        // 2. Contenteditable (Facebook Lexical, Discord Slate, X Draft.js, Instagram)
        // Ensure any previous contents (or old duplicates) are fully selected so insertion cleanly replaces them
        try {
            document.execCommand("selectAll", false, null);
        } catch (_) {}
        try {
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(composer);
            selection.removeAllRanges();
            selection.addRange(range);
        } catch (_) {}

        // ----------------------------------------------------------------------
        // 2a. FACEBOOK MESSENGER (Meta Lexical Editor)
        // ----------------------------------------------------------------------
        // Meta's Lexical editor listens to beforeinput / execCommand("insertText") natively.
        // DO NOT dispatch a synthetic ClipboardEvent("paste") on Facebook, because Lexical's
        // paste listener and its beforeinput listener BOTH execute, inserting the message TWICE!
        if (currentPlatform === "facebook") {
            let fbSuccess = false;
            try {
                fbSuccess = document.execCommand("insertText", false, text);
            } catch (err) {
                console.warn("[Arclent Extension] Facebook execCommand failed:", err);
            }

            if (!fbSuccess) {
                try {
                    composer.innerText = text;
                } catch (_) {}
            }

            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
            composer.dataset.arclentInserted = "true";
            console.log("[Arclent Extension] Facebook message inserted via execCommand (paste dispatch prevented).");
            return true;
        }

        // ----------------------------------------------------------------------
        // 2b. OTHER PLATFORMS (Instagram, Discord, X)
        // ----------------------------------------------------------------------
        // Strategy A: Synthetic ClipboardEvent
        let pasteHandled = false;
        try {
            const dt = new DataTransfer();
            dt.setData("text/plain", text);
            const pasteEvt = new ClipboardEvent("paste", {
                bubbles: true,
                cancelable: true,
                clipboardData: dt
            });
            const dispatchResult = composer.dispatchEvent(pasteEvt);
            // If defaultPrevented or dispatchResult is false, an editor listener handled the paste
            if (pasteEvt.defaultPrevented || dispatchResult === false) {
                pasteHandled = true;
            }
        } catch (e) {
            console.warn("[Arclent Extension] ClipboardEvent paste dispatch failed:", e);
        }

        // If the paste event was consumed/handled by the editor framework, do NOT run execCommand
        if (pasteHandled) {
            console.log("[Arclent Extension] Message inserted via handled paste event.");
            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
            composer.dataset.arclentInserted = "true";
            return true;
        }

        // Strategy B: execCommand insertText fallback (ONLY if Strategy A was not handled)
        try {
            document.execCommand("insertText", false, text);
        } catch (err) {
            console.warn("[Arclent Extension] execCommand failed:", err);
        }

        const valAfterB = normalizeText(composer.innerText || composer.textContent || composer.value || "");
        if (sample.length > 0 && valAfterB.includes(sample)) {
            console.log("[Arclent Extension] Message successfully inserted via execCommand.");
            composer.dispatchEvent(new Event("input", { bubbles: true }));
            composer.dispatchEvent(new Event("change", { bubbles: true }));
            composer.dataset.arclentInserted = "true";
            return true;
        }

        // Strategy C: Direct innerText fallback (last resort)
        try {
            composer.innerText = text;
        } catch (_) {}

        composer.dispatchEvent(new Event("input", { bubbles: true }));
        composer.dispatchEvent(new Event("change", { bubbles: true }));
        composer.dataset.arclentInserted = "true";
        return true;
    }

    function verifyMessageContent(composer, expectedText) {
        if (!composer || !expectedText) return false;
        if (isCommentOrPostBox(composer)) return false;
        const currentText = composer.innerText || composer.textContent || composer.value || "";
        const sample = normalizeText(expectedText).substring(0, Math.min(30, expectedText.length));
        return normalizeText(currentText).includes(sample);
    }

    // --------------------------------------------------------------------------
    // Platform Drivers: Login Detection, Profile Navigation, Composer Finders
    // --------------------------------------------------------------------------

    const PlatformDrivers = {
        // ======================================================================
        // 1. INSTAGRAM
        // ======================================================================
        instagram: {
            loginUrl: "https://www.instagram.com/accounts/login/",
            isLoggedOut() {
                const path = window.location.pathname.toLowerCase();
                if (path.includes("accounts/login") || path.includes("accounts/emailsignup")) return true;
                const pwd = document.querySelector('input[type="password"], input[name="password"]');
                const loginBtn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => {
                    const t = (b.textContent || "").trim().toLowerCase();
                    return t === "log in" || t === "sign up";
                });
                return Boolean(pwd && loginBtn);
            },
            getCreatorTargetUrl(session) {
                const u = (session.username || "").toLowerCase().replace(/^@+/, "");
                return u ? `https://www.instagram.com/${u}/` : "https://www.instagram.com/direct/inbox/";
            },
            findMessageButton() {
                const candidates = Array.from(document.querySelectorAll('button, div[role="button"], a[role="button"], a[href*="/direct/t/"], a[href*="/direct/new/"]'));
                for (const el of candidates) {
                    const text = (el.textContent || "").trim().toLowerCase();
                    const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
                    if (text === "message" || text === "send message" || ariaLabel === "message" || ariaLabel === "send message") {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) return el;
                    }
                }
                const header = document.querySelector("header, main header");
                if (header) {
                    const btns = Array.from(header.querySelectorAll('button, div[role="button"]'));
                    for (const b of btns) {
                        if ((b.textContent || "").toLowerCase().includes("message")) return b;
                    }
                }
                return null;
            },
            findComposer() {
                const editables = Array.from(document.querySelectorAll('div[contenteditable="true"], p[contenteditable="true"], span[contenteditable="true"]'));
                for (const el of editables) {
                    if (isCommentOrPostBox(el)) continue;
                    const role = el.getAttribute("role");
                    const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
                    const placeholder = (el.getAttribute("aria-placeholder") || el.getAttribute("data-placeholder") || "").toLowerCase();
                    if ((role === "textbox" || el.hasAttribute("data-lexical-editor")) && 
                        (ariaLabel.includes("message") || placeholder.includes("message") || window.location.pathname.includes("/direct/"))) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) return el;
                    }
                }
                const textareas = Array.from(document.querySelectorAll('textarea'));
                for (const ta of textareas) {
                    if (isCommentOrPostBox(ta)) continue;
                    const placeholder = (ta.getAttribute("placeholder") || "").toLowerCase();
                    if (placeholder.includes("message") || (window.location.pathname.includes("/direct/") && !ta.closest('form[role="search"]'))) {
                        return ta;
                    }
                }
                return null;
            },
            detectLoggedInUser() {
                try {
                    const profileLink = document.querySelector('svg[aria-label="Profile"], svg[aria-label="Your profile"]')?.closest('a');
                    if (profileLink) {
                        const href = profileLink.getAttribute("href") || "";
                        const clean = href.replace(/^\/+|\/+$/g, "").split("/")[0].replace(/^@+/, "").trim();
                        if (clean && !clean.includes("?")) return clean;
                    }
                    const avatarImgs = Array.from(document.querySelectorAll('img[alt*="profile picture"]'));
                    for (const img of avatarImgs) {
                        const alt = img.getAttribute("alt") || "";
                        const match = alt.match(/^([^']+)'s profile picture/i);
                        if (match && match[1]) return match[1].replace(/^@+/, "").trim();
                    }
                } catch (_) {}
                return null;
            }
        },

        // ======================================================================
        // 2. X (TWITTER)
        // ======================================================================
        x: {
            loginUrl: "https://x.com/i/flow/login",
            isLoggedOut() {
                const path = window.location.pathname.toLowerCase();
                if (path.startsWith("/login") || path.startsWith("/i/flow/login")) return true;
                const loginBtn = document.querySelector('a[href="/login"], a[data-testid="loginButton"]');
                const signupBtn = document.querySelector('a[href="/i/flow/signup"], a[data-testid="signupButton"]');
                const hasAppTabBar = document.querySelector('nav[aria-label="Primary Navigation"], a[data-testid="AppTabBar_Profile_Link"]');
                return Boolean((loginBtn || signupBtn) && !hasAppTabBar);
            },
            getCreatorTargetUrl(session) {
                const u = (session.username || "").toLowerCase().replace(/^@+/, "");
                return u ? `https://x.com/${u}` : "https://x.com/messages";
            },
            findMessageButton() {
                // X Profile Message Button (envelope icon)
                const dmBtn = document.querySelector('button[data-testid="sendDMFromProfile"], div[data-testid="sendDMFromProfile"], a[data-testid="sendDMFromProfile"]');
                if (dmBtn) return dmBtn;

                const btns = Array.from(document.querySelectorAll('button[aria-label*="Direct message" i], div[role="button"][aria-label*="Direct message" i], button[aria-label*="Message" i]'));
                for (const b of btns) {
                    if (isCommentOrPostBox(b)) continue;
                    const rect = b.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) return b;
                }
                return null;
            },
            findComposer() {
                // Strategy 1: Known X DM testids and composer attributes
                const specificSelectors = [
                    'div[data-testid="dmComposerTextInput"] [contenteditable="true"]',
                    'div[data-testid="dmComposerTextInput"]',
                    '[data-testid*="dmComposer" i] [contenteditable="true"]',
                    '[data-testid*="dmComposer" i]',
                    '[data-testid="messageEntry"] [contenteditable="true"]',
                    '[data-testid="dmComposer"]'
                ];
                for (const sel of specificSelectors) {
                    const el = document.querySelector(sel);
                    if (el && !isCommentOrPostBox(el)) {
                        const target = el.getAttribute("contenteditable") === "true" ? el : (el.querySelector('[contenteditable="true"]') || el);
                        if (!isCommentOrPostBox(target)) {
                            const rect = target.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return target;
                        }
                    }
                }

                // Strategy 2: Look for elements referencing "Unencrypted message", "Start a message", "Direct message"
                const candidateNodes = Array.from(document.querySelectorAll('div, span, p, label, textarea'));
                for (const el of candidateNodes) {
                    if (isCommentOrPostBox(el)) continue;
                    const text = (el.textContent || "").trim().toLowerCase();
                    const aria = (el.getAttribute("aria-label") || "").toLowerCase();
                    const placeholder = (el.getAttribute("placeholder") || el.getAttribute("data-placeholder") || "").toLowerCase();

                    const isMatch = text === "unencrypted message" ||
                                    text.startsWith("unencrypted message") ||
                                    text === "start a message" ||
                                    text.startsWith("start a message") ||
                                    aria.includes("unencrypted message") ||
                                    aria.includes("direct message") ||
                                    aria.includes("start a message") ||
                                    placeholder.includes("unencrypted message") ||
                                    placeholder.includes("start a message") ||
                                    placeholder.includes("direct message");

                    if (isMatch) {
                        if (el.getAttribute("contenteditable") === "true" || el.tagName.toLowerCase() === "textarea") {
                            return el;
                        }
                        const container = el.closest('div[role="textbox"], form, section, aside, div[data-testid*="composer" i]') || el.parentElement?.parentElement;
                        if (container) {
                            const editable = container.querySelector('[contenteditable="true"], textarea');
                            if (editable && !isCommentOrPostBox(editable)) {
                                const rect = editable.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) return editable;
                            }
                        }
                        const nearby = el.parentElement?.querySelector('[contenteditable="true"], textarea');
                        if (nearby && !isCommentOrPostBox(nearby)) return nearby;
                    }
                }

                // Strategy 3: Scan contenteditable elements within messages
                const editables = Array.from(document.querySelectorAll('div[contenteditable="true"], span[contenteditable="true"], [role="textbox"][contenteditable="true"], [contenteditable="true"]'));
                for (const el of editables) {
                    if (isCommentOrPostBox(el)) continue;
                    if (el.closest('[data-testid="tweetTextarea_0"]') || el.getAttribute("data-testid") === "tweetTextarea_0") continue;
                    if (el.closest('[data-testid="SearchBox_Search_Input"], form[role="search"]')) continue;
                    if (window.location.pathname.includes("/messages") || el.closest('[data-testid*="dm" i], [data-testid*="message" i]')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 15) {
                            return el;
                        }
                    }
                }

                // Strategy 4: Any non-search textarea within messages
                if (window.location.pathname.includes("/messages")) {
                    const textareas = Array.from(document.querySelectorAll('textarea'));
                    for (const ta of textareas) {
                        if (isCommentOrPostBox(ta)) continue;
                        if (ta.closest('form[role="search"]') || ta.getAttribute("data-testid") === "SearchBox_Search_Input") continue;
                        const rect = ta.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 15) return ta;
                    }
                }

                return null;
            },
            detectLoggedInUser() {
                try {
                    const profileLink = document.querySelector('a[data-testid="AppTabBar_Profile_Link"]');
                    if (profileLink) {
                        const href = profileLink.getAttribute("href") || "";
                        const clean = href.replace(/^\/+|\/+$/g, "").split("/")[0].replace(/^@+/, "").trim();
                        if (clean && clean !== "home" && clean !== "messages") return clean;
                    }
                } catch (_) {}
                return null;
            }
        },

        // ======================================================================
        // 3. DISCORD (WEB)
        // ======================================================================
        discord: {
            loginUrl: "https://discord.com/login",
            isLoggedOut() {
                const path = window.location.pathname.toLowerCase();
                if (path.startsWith("/login") || path.startsWith("/register")) return true;
                const pwdInput = document.querySelector('input[type="password"]');
                const loginForm = document.querySelector('form[action*="login"]');
                const hasAppContainer = document.querySelector('nav[aria-label="Servers sidebar"], div[class*="guilds"]');
                return Boolean((pwdInput || loginForm) && !hasAppContainer);
            },
            getCreatorTargetUrl(session) {
                const id = session.userId || session.username;
                if (id && /^\d{17,20}$/.test(id)) {
                    return `https://discord.com/users/${id}`;
                }
                return "https://discord.com/channels/@me";
            },
            findMessageButton(session) {
                const targetUser = ((session && session.username) || "").toLowerCase().replace(/^@+/, "");

                // 1. Locate user profile modal/card container if present
                const profileContainers = Array.from(document.querySelectorAll('[class*="userProfile"], [class*="user-profile"], [class*="profileEffect"], div[role="dialog"], div[class*="modal"], div[class*="layer"] div[class*="root"]'));
                
                // If profile container exists, search inside it with highest priority
                for (const container of profileContainers) {
                    const clickables = Array.from(container.querySelectorAll('button, a, div[role="button"], [tabindex="0"]'));
                    for (const el of clickables) {
                        const text = (el.innerText || el.textContent || "").trim().toLowerCase();
                        const aria = (el.getAttribute("aria-label") || "").trim().toLowerCase();

                        // Exact or primary "Message" button (like the big button in the profile right pane)
                        if (text === "message" || text === "send message" || aria === "message" || aria === "send message") {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return el;
                        }
                        // Prefix or containing "Message @username" or "Message username"
                        if (text.startsWith("message ") || aria.startsWith("message ") || aria.includes("direct message")) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return el;
                        }
                    }

                    // Also check for SVG chat bubble icon button inside the profile container
                    for (const el of clickables) {
                        const aria = (el.getAttribute("aria-label") || "").toLowerCase();
                        if (aria.includes("message") && !aria.includes("inbox") && !aria.includes("pinned")) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return el;
                        }
                    }
                }

                // 2. Global scan across document for profile "Message" button
                const allClickables = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                for (const el of allClickables) {
                    if (el.closest('nav[aria-label="Servers sidebar"], [aria-label*="Inbox" i], [aria-label*="Help" i], form[role="search"]')) continue;
                    const text = (el.innerText || el.textContent || "").trim().toLowerCase();
                    const aria = (el.getAttribute("aria-label") || "").trim().toLowerCase();

                    if (text === "message" || text === "send message" || aria === "message" || aria === "send message") {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) return el;
                    }
                }

                // 3. Direct Messages list in left sidebar (matching target creator name)
                if (targetUser) {
                    const dmLinks = Array.from(document.querySelectorAll('nav[aria-label*="Direct Messages" i] a, a[href*="/channels/@me/"]'));
                    for (const a of dmLinks) {
                        const txt = (a.innerText || a.textContent || "").toLowerCase();
                        const aria = (a.getAttribute("aria-label") || "").toLowerCase();
                        if (txt.includes(targetUser) || aria.includes(targetUser)) {
                            const rect = a.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return a;
                        }
                    }
                }

                return null;
            },
            findComposer() {
                // Discord message textarea is Slate-based contenteditable textbox
                const specificSelectors = [
                    'div[role="textbox"][data-slate-editor="true"]',
                    'div[data-slate-editor="true"]',
                    'div[role="textbox"][contenteditable="true"]',
                    'div[class*="slateTextArea"] [contenteditable="true"]',
                    'form div[contenteditable="true"]',
                    'div[aria-label*="Message @" i][contenteditable="true"]',
                    'div[aria-label*="Message" i][contenteditable="true"]'
                ];
                for (const sel of specificSelectors) {
                    const el = document.querySelector(sel);
                    if (el && !isCommentOrPostBox(el)) {
                        const target = el.getAttribute("contenteditable") === "true" ? el : (el.querySelector('[contenteditable="true"]') || el);
                        if (!isCommentOrPostBox(target)) {
                            const rect = target.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return target;
                        }
                    }
                }

                const editables = Array.from(document.querySelectorAll('div[role="textbox"][contenteditable="true"], div[contenteditable="true"]'));
                for (const el of editables) {
                    if (isCommentOrPostBox(el)) continue;
                    if (el.closest('[role="search"], [aria-label*="Search" i]')) continue;
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 50 && rect.height > 15) return el;
                }
                return null;
            },
            detectLoggedInUser() {
                try {
                    const userPanel = document.querySelector('section[aria-label*="User profile" i], div[class*="panels"] button[aria-label*="User settings" i]');
                    if (userPanel) {
                        const text = userPanel.textContent || "";
                        if (text) return text.trim();
                    }
                } catch (_) {}
                return null;
            }
        },

        // ======================================================================
        // 4. FACEBOOK (MESSENGER)
        // ======================================================================
        facebook: {
            loginUrl: "https://www.facebook.com/login.php",
            isLoggedOut() {
                const path = window.location.pathname.toLowerCase();
                if (path.includes("login.php") || path.includes("/login")) return true;
                const emailInput = document.querySelector('input#email, input[name="email"]');
                const passInput = document.querySelector('input#pass, input[name="pass"]');
                const loginBtn = document.querySelector('button[name="login"], #loginbutton');
                return Boolean(passInput && (emailInput || loginBtn));
            },
            getCreatorTargetUrl(session) {
                const u = (session.username || "").toLowerCase().replace(/^@+/, "");
                if (window.location.hostname.includes("messenger.com")) {
                    return u ? `https://www.messenger.com/t/${u}` : "https://www.messenger.com/";
                }
                return u ? `https://www.facebook.com/${u}` : "https://www.facebook.com/messages";
            },
            findMessageButton() {
                const candidates = Array.from(document.querySelectorAll(
                    'div[aria-label="Message" i], ' +
                    'div[aria-label="Send message" i], ' +
                    'div[aria-label="Send Message" i], ' +
                    'a[aria-label*="Message" i], ' +
                    'a[href*="/messages/t/"], ' +
                    'div[role="button"]'
                ));
                for (const el of candidates) {
                    if (isCommentOrPostBox(el)) continue;
                    const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
                    const text = (el.textContent || "").toLowerCase().trim();
                    if (ariaLabel === "message" || ariaLabel === "send message" || text === "message" || text === "send message") {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) return el;
                    }
                }
                return null;
            },
            findComposer() {
                // Messenger / Facebook Chat composer textbox
                // 1. Messenger popup chat tab at bottom right (data-pagelet="ChatTab", etc.) or messenger view
                const chatTabs = Array.from(document.querySelectorAll(
                    'div[data-pagelet="ChatTab"], ' +
                    'div[aria-label*="Chat with" i], ' +
                    'div[aria-label*="Conversation" i], ' +
                    'div[role="region"][aria-label*="Chat" i], ' +
                    'div[class*="fbDockChatTabFlyout"], ' +
                    'div[aria-label*="Messages" i], ' +
                    'div[role="main"]'
                ));

                for (const container of chatTabs) {
                    const editables = Array.from(container.querySelectorAll('div[role="textbox"][contenteditable="true"], div[contenteditable="true"]'));
                    for (const el of editables) {
                        if (isCommentOrPostBox(el)) continue;
                        const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
                        const placeholder = (el.getAttribute("aria-placeholder") || "").toLowerCase();
                        if (ariaLabel.includes("message") || placeholder.includes("message") || 
                            ariaLabel === "aa" || placeholder === "aa" || 
                            ariaLabel.includes("type a message") || ariaLabel.includes("send a message") || 
                            el.hasAttribute("data-lexical-editor")) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) return el;
                        }
                    }
                }

                // 2. Scan for explicit Messenger / DM textboxes with strict aria-labels
                const allEditables = Array.from(document.querySelectorAll('div[role="textbox"][contenteditable="true"]'));
                for (const el of allEditables) {
                    if (isCommentOrPostBox(el)) continue;
                    const ariaLabel = (el.getAttribute("aria-label") || "").toLowerCase();
                    const placeholder = (el.getAttribute("aria-placeholder") || "").toLowerCase();
                    if (ariaLabel.includes("message") || placeholder.includes("message") || 
                        ariaLabel === "aa" || placeholder === "aa" || 
                        ariaLabel.includes("type a message") || ariaLabel.includes("send a message")) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) return el;
                    }
                }

                // STRICT: Never fall back to comment boxes or arbitrary editables! Return null if no genuine DM composer exists.
                return null;
            },
            detectLoggedInUser() {
                try {
                    const profileLink = document.querySelector('svg[aria-label="Your profile" i]?.closest("a"), a[aria-label="Your profile" i]');
                    if (profileLink) {
                        const href = profileLink.getAttribute("href") || "";
                        const clean = href.replace(/^\/+|\/+$/g, "").split("/")[0].trim();
                        if (clean) return clean;
                    }
                } catch (_) {}
                return null;
            }
        }
    };

    // --------------------------------------------------------------------------
    // Main Orchestration & Login Auto-Redirect Engine
    // --------------------------------------------------------------------------
    async function processOutreach(force = false) {
        if (isProcessing && !force) return;

        const driver = PlatformDrivers[currentPlatform];
        if (!driver) {
            console.log(`[Arclent Extension] No driver configured for platform: ${currentPlatform}`);
            return;
        }

        let sessionData = null;
        try {
            const data = await chrome.storage.local.get("activeOutreachSession");
            sessionData = data.activeOutreachSession;
        } catch (e) {
            return;
        }

        if (!sessionData || (sessionData.platform && sessionData.platform !== currentPlatform)) {
            return;
        }

        // Do not re-process if already completed unless manually forced
        if (!force && sessionData.status === "completed") {
            return;
        }

        isProcessing = true;

        const platformDisplayName = sessionData.platformName || (currentPlatform.charAt(0).toUpperCase() + currentPlatform.slice(1));
        const targetName = sessionData.username ? `@${sessionData.username}` : (sessionData.userId ? `ID ${sessionData.userId}` : "the creator");

        try {
            // ==================================================================
            // Step 1: Check Authentication / Login State
            // ==================================================================
            if (driver.isLoggedOut()) {
                console.log(`[Arclent Extension] User is logged out on ${platformDisplayName}.`);

                // Mark session as waiting for login
                sessionData.status = "waiting_for_login";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});

                // Show login guide banner
                showFloatingBanner({
                    title: `🔒 ${platformDisplayName} Login Required`,
                    message: `Please log in to your ${platformDisplayName} account. Arclent will <strong>automatically redirect</strong> to ${targetName}'s DM once you sign in.`,
                    type: "warning",
                    showCopyBtn: true,
                    copyText: sessionData.message
                });

                // If user is logged out and not on login page, redirect to login page
                const targetLoginUrl = sessionData.loginUrl || driver.loginUrl;
                if (targetLoginUrl && !window.location.href.includes("login") && !window.location.href.includes("signin")) {
                    console.log(`[Arclent Extension] Navigating to login page: ${targetLoginUrl}`);
                    window.location.href = targetLoginUrl;
                }

                isProcessing = false;
                return;
            }

            // If we were waiting for login and now the user is authenticated:
            if (sessionData.status === "waiting_for_login") {
                console.log(`[Arclent Extension] Login detected on ${platformDisplayName}! Redirecting to creator DM target...`);
                showFloatingBanner({
                    title: `✓ Signed In to ${platformDisplayName}`,
                    message: `Login successful! Opening ${targetName}'s DM now...`,
                    type: "success",
                    autoDismiss: true,
                    durationMs: 3000
                });

                // Update status back to pending
                sessionData.status = "pending";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});

                const destination = sessionData.targetUrl || driver.getCreatorTargetUrl(sessionData);
                if (destination && !window.location.href.startsWith(destination.split("?")[0])) {
                    window.location.href = destination;
                    isProcessing = false;
                    return;
                }
            }

            const destination = sessionData.targetUrl || driver.getCreatorTargetUrl(sessionData);
            const targetUser = (sessionData.username || "").toLowerCase().replace(/^@+/, "");
            const currentPath = window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();

            // Verify current URL matches target creator before attempting to interact with the DOM
            let onTargetProfile = false;
            if (currentPlatform === "instagram") {
                onTargetProfile = targetUser ? (currentPath === targetUser || currentPath.startsWith(targetUser + "/")) : true;
            } else if (currentPlatform === "x") {
                onTargetProfile = targetUser ? (currentPath === targetUser || currentPath.startsWith(targetUser + "/")) : true;
            } else if (currentPlatform === "discord") {
                const hasProfile = Boolean(
                    driver.findMessageButton(sessionData) || 
                    document.querySelector('[class*="userProfile"], [class*="user-profile"], [class*="profileEffect"], div[role="dialog"]')
                );
                onTargetProfile = hasProfile || currentPath === "channels/@me" || window.location.pathname.includes("/users/");
            } else if (currentPlatform === "facebook") {
                onTargetProfile = targetUser ? currentPath.startsWith(targetUser) : true;
            }

            const inMessages = currentPlatform === "discord"
                ? Boolean(currentPath.match(/channels\/@me\/\d+/))
                : (currentPath.includes("direct/") || currentPath.includes("messages") || currentPath.includes("channels/@me") || currentPath.includes("i/chat"));

            // If we are neither on the target profile nor in messages, navigate to the target profile first
            if (!onTargetProfile && !inMessages && destination) {
                console.log(`[Arclent Extension] Current URL (${window.location.href}) is not target creator (${destination}). Redirecting...`);
                sessionData.status = "pending";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});
                window.location.href = destination;
                isProcessing = false;
                return;
            }

            // Lock session to processing
            sessionData.status = "processing";
            await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});

            console.log(`[Arclent Extension] Preparing DM on ${platformDisplayName} for:`, sessionData.username || sessionData.userId);

            // ==================================================================
            // Step 2: Open DM or Profile Message Button
            // ==================================================================
            // Only click the profile Message button if we are on the target creator's profile
            if (onTargetProfile && !inMessages) {
                const messageBtn = await waitForElement(() => driver.findMessageButton(sessionData), 5000);
                if (messageBtn) {
                    console.log(`[Arclent Extension] Found ${platformDisplayName} Message button on target profile. Clicking to open composer...`);
                    safeClick(messageBtn);
                    await new Promise(r => setTimeout(r, 2000));
                }
            }

            // ==================================================================
            // Step 3: Locate Composer & Prefill Message Draft
            // ==================================================================
            console.log(`[Arclent Extension] Locating ${platformDisplayName} message composer...`);
            const composer = await waitForElement(driver.findComposer, 8000);

            if (!composer) {
                console.warn(`[Arclent Extension] Could not automatically locate ${platformDisplayName} DM composer.`);

                // Auto-copy message to clipboard immediately as requested
                const copied = await copyTextToClipboard(sessionData.message);
                console.log(`[Arclent Extension] Auto-copied outreach message to clipboard: ${copied}`);

                showFloatingBanner({
                    title: "Couldn't Insert Message in DM",
                    message: `We couldn't insert the message directly into the DM (direct messaging may be closed, restricted, or not available on ${targetName}'s page).<br><br><strong>We have copied the message for you</strong> so you can paste it manually if needed.`,
                    type: "warning",
                    showCopyBtn: true,
                    copyText: sessionData.message,
                    buttonLabel: copied ? "✓ Message Copied (Click to re-copy)" : "📋 Copy Message to Clipboard"
                });

                await chrome.runtime.sendMessage({
                    type: "ARCLENT_SOCIAL_DM_FAILED",
                    platform: currentPlatform,
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    reason: `Couldn't insert message in DM for ${targetName}. Message has been copied to your clipboard.`
                }).catch(() => {});

                sessionData.status = "failed";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});
                isProcessing = false;
                return;
            }

            // Step 4: Insert Message Text
            console.log(`[Arclent Extension] Composer found. Inserting draft message...`);
            const inserted = insertMessageIntoComposer(composer, sessionData.message);
            await new Promise(r => setTimeout(r, 400));
            const verified = verifyMessageContent(composer, sessionData.message);

            if (verified || inserted) {
                console.log(`[Arclent Extension] ✓ Message inserted into ${platformDisplayName} composer. STOPPING (user must review & send).`);

                sessionData.status = "completed";
                await chrome.storage.local.set({ activeOutreachSession: sessionData }).catch(() => {});

                // Detect logged-in sender handle
                const loggedInUser = driver.detectLoggedInUser ? driver.detectLoggedInUser() : null;

                // Sync to backend if session ID present
                const backendOrigin = sessionData.backendOrigin || (sessionData.source === "arclent" ? "https://ai-outreach-production-8dcc.up.railway.app" : null);
                if (loggedInUser && backendOrigin && sessionData.sessionId) {
                    try {
                        fetch(`${backendOrigin}/api/outreach/record-social-outreach`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                session_id: sessionData.sessionId,
                                platform: platformDisplayName,
                                sender_handle: loggedInUser,
                                sender_identity: `${loggedInUser} on Arclent`
                            })
                        }).catch(() => {});
                    } catch (_) {}
                }

                // Show clear success banner guiding user to review and click Send manually
                showFloatingBanner({
                    title: "✓ Message Ready",
                    message: `Your outreach message has been inserted for <strong>${targetName}</strong> on ${platformDisplayName}.<br><br><strong>Please review the message and click Send.</strong>`,
                    type: "success",
                    showCopyBtn: true,
                    copyText: sessionData.message,
                    buttonLabel: "📋 Copy Message"
                });

                // Notify background service worker & Arclent web app
                await chrome.runtime.sendMessage({
                    type: "ARCLENT_SOCIAL_DM_READY",
                    platform: currentPlatform,
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    senderHandle: loggedInUser,
                    success: true
                }).catch(() => {});

            } else {
                console.warn(`[Arclent Extension] Verification failed after insertion into ${platformDisplayName} composer.`);
                const copied = await copyTextToClipboard(sessionData.message);

                showFloatingBanner({
                    title: "Couldn't Insert Message in DM",
                    message: `We couldn't automatically insert the message into the DM composer.<br><br><strong>We have copied the message for you</strong> so you can paste (Ctrl+V) directly.`,
                    type: "warning",
                    showCopyBtn: true,
                    copyText: sessionData.message,
                    buttonLabel: copied ? "✓ Message Copied (Click to re-copy)" : "📋 Copy Message to Clipboard"
                });

                await chrome.runtime.sendMessage({
                    type: "ARCLENT_SOCIAL_DM_FAILED",
                    platform: currentPlatform,
                    username: sessionData.username,
                    sessionId: sessionData.sessionId,
                    reason: `Couldn't insert message into DM for ${targetName}. Message has been copied to your clipboard.`
                }).catch(() => {});
            }

        } catch (err) {
            console.error(`[Arclent Extension] Error during ${platformDisplayName} outreach processing:`, err);
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
            setTimeout(() => processOutreach(false), 800);
        }
    });

    observer.observe(document, { subtree: true, childList: true });

    // Initial check on load
    setTimeout(() => processOutreach(false), 1000);

    // Listen for manual trigger from popup or background
    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
        if (msg && msg.type === "TRIGGER_DM_AUTOFILL") {
            processOutreach(true);
            sendResponse({ status: "processing" });
        }
        return true;
    });

})();
