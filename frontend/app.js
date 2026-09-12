/**
 * Arclent Creator Collaboration Verification & Outreach Controller
 * Integrates 2-step verification (1 · EMAIL, 2 · INSTAGRAM) with real discovered backend intelligence.
 */

document.addEventListener("DOMContentLoaded", () => {
    // --------------------------------------------------------------------------
    // Regex & Utilities
    // --------------------------------------------------------------------------
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatHandle(v) {
        if (!v) return "";
        v = v.trim();
        if (v.startsWith("http://") || v.startsWith("https://")) {
            const parts = v.replace(/\/$/, "").split("/");
            v = parts[parts.length - 1];
        }
        return v.startsWith("@") ? v : `@${v}`;
    }

    // --------------------------------------------------------------------------
    // Social Media Icons & Metadata Helper
    // --------------------------------------------------------------------------
    function getSocialMediaMeta(platform) {
        const p = (platform || "").toLowerCase();
        
        if (p.includes("instagram")) {
            return {
                name: "Instagram",
                color: "#FFFFFF",
                bgColor: "linear-gradient(135deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%)",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>`
            };
        }
        if (p.includes("twitter") || p === "x" || p.includes("x/")) {
            return {
                name: "X (Twitter)",
                color: "#FFFFFF",
                bgColor: "#000000",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`
            };
        }
        if (p.includes("twitch")) {
            return {
                name: "Twitch",
                color: "#FFFFFF",
                bgColor: "#9146FF",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"/></svg>`
            };
        }
        if (p.includes("discord")) {
            return {
                name: "Discord",
                color: "#FFFFFF",
                bgColor: "#5865F2",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.894.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>`
            };
        }
        if (p.includes("reddit")) {
            return {
                name: "Reddit",
                color: "#FFFFFF",
                bgColor: "#FF4500",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><circle cx="12" cy="12" r="10" fill="#FF4500"/><path fill="#FFF" d="M12 7.2a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm6.2 4.4a1.8 1.8 0 0 0-1.4.7c-1.3-.9-3-1.4-4.8-1.5l.8-3.8 2.7.6a1.3 1.3 0 1 0 .3-1.2l-3.2-.7a.4.4 0 0 0-.4.3l-1 4.8c-1.9.1-3.6.6-4.9 1.5a1.8 1.8 0 0 0-2.4 2c-.1.4-.1.8-.1 1.2 0 3 3.4 5.3 7.6 5.3s7.6-2.4 7.6-5.3c0-.4 0-.8-.1-1.2a1.8 1.8 0 0 0-.8-2.6zM9 13.5a1.2 1.2 0 1 1 2.4 0 1.2 1.2 0 0 1-2.4 0zm6 3.3c-.9.9-2.3.9-3 0a.4.4 0 0 1 .5-.5c.5.5 1.5.5 2 0a.4.4 0 1 1 .5.5zm-.1-2.1a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4z"/></svg>`
            };
        }
        if (p.includes("facebook")) {
            return {
                name: "Facebook",
                color: "#FFFFFF",
                bgColor: "#1877F2",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`
            };
        }
        if (p.includes("linkedin")) {
            return {
                name: "LinkedIn",
                color: "#FFFFFF",
                bgColor: "#0A66C2",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>`
            };
        }
        if (p.includes("tiktok")) {
            return {
                name: "TikTok",
                color: "#FFFFFF",
                bgColor: "#000000",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.24 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>`
            };
        }
        if (p.includes("youtube")) {
            return {
                name: "YouTube",
                color: "#FFFFFF",
                bgColor: "#FF0000",
                icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`
            };
        }

        return {
            name: platform || "Profile",
            color: "#FFFFFF",
            bgColor: "#374151",
            icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`
        };
    }

    // --------------------------------------------------------------------------
    // Instagram Handle Normalizer
    // --------------------------------------------------------------------------
    function normalizeInstagramHandle(handleOrUrl) {
        if (!handleOrUrl) return "";
        let h = String(handleOrUrl).trim();

        // If URL, strip query params and hash fragment, then parse username
        if (h.includes("instagram.com") || h.includes("instagr.am") || h.includes("ig.me") || h.startsWith("http://") || h.startsWith("https://")) {
            try {
                // Strip query parameters and hash fragments first
                h = h.split("?")[0].split("#")[0];
                const urlObj = new URL(h.startsWith("http") ? h : `https://${h}`);
                const pathSegments = urlObj.pathname.replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);

                if (pathSegments.length > 0) {
                    // Check if ig.me/m/username
                    if (pathSegments[0].toLowerCase() === "m" && pathSegments[1]) {
                        h = pathSegments[1];
                    } else if (pathSegments[0].toLowerCase() === "direct" && pathSegments[1]?.toLowerCase() === "t" && pathSegments[2]) {
                        h = pathSegments[2];
                    } else {
                        // Find first non-system segment
                        const systemSegments = new Set(["direct", "p", "reel", "reels", "stories", "explore", "inbox", "accounts"]);
                        const userSegment = pathSegments.find(seg => !systemSegments.has(seg.toLowerCase()));
                        h = userSegment || pathSegments[pathSegments.length - 1];
                    }
                }
            } catch (e) {
                // Fallback regex parsing
                h = h.split("?")[0].split("#")[0];
                h = h.replace(/^https?:\/\/(www\.)?(instagram\.com|instagr\.am|ig\.me\/m)\//i, "");
                h = h.replace(/\/+$/, "");
            }
        }

        // Strip any residual query params, slashes, or @ symbols
        h = h.split("?")[0].split("#")[0].replace(/\/+$/, "").replace(/^@+/, "").trim();
        return h;
    }

    // --------------------------------------------------------------------------
    // Direct Message URL Generator (Instagram, X, Reddit, Facebook, LinkedIn, etc.)
    // --------------------------------------------------------------------------
    function getDirectMessageUrl(platform, rawHandleOrUrl, text = "", subject = "") {
        const p = (platform || "").toLowerCase();

        // 1. Instagram: Always construct the official direct message shortlink ig.me/m/<username>
        if (p.includes("instagram") || p === "ig") {
            const handle = normalizeInstagramHandle(rawHandleOrUrl);
            if (!handle) {
                // Open Instagram direct inbox as fallback, NEVER profile
                return "https://www.instagram.com/direct/inbox/";
            }
            return `https://ig.me/m/${encodeURIComponent(handle)}`;
        }

        const encodedText = encodeURIComponent(text || "");
        const encodedSubject = encodeURIComponent(subject || "Collaboration Confirmation");

        // 2. X / Twitter: Direct message compose overlay with text prefilled
        if (p.includes("twitter") || p === "x" || p.includes("x/")) {
            return `https://x.com/messages/compose?text=${encodedText}`;
        }

        // 3. Reddit: Official direct message composer prefilling recipient, subject and text
        if (p.includes("reddit")) {
            const cleanRedditHandle = String(rawHandleOrUrl || "")
                .split("?")[0]
                .replace(/^https?:\/\/(www\.)?reddit\.com\/u(ser)?\//i, "")
                .replace(/^@+/, "")
                .replace(/\/+$/, "")
                .trim();
            if (!cleanRedditHandle) return "https://www.reddit.com/message/compose/";
            return `https://www.reddit.com/message/compose/?to=${encodeURIComponent(cleanRedditHandle)}&subject=${encodedSubject}&message=${encodedText}`;
        }

        // 4. Facebook / Messenger: m.me/<username> opens Messenger chat
        if (p.includes("facebook") || p.includes("messenger") || p === "fb") {
            const cleanFb = String(rawHandleOrUrl || "")
                .split("?")[0]
                .replace(/^https?:\/\/(www\.)?(facebook\.com|m\.me|messenger\.com)\//i, "")
                .replace(/^@+/, "")
                .replace(/\/+$/, "")
                .trim();
            if (!cleanFb) return "https://www.messenger.com/";
            return `https://m.me/${encodeURIComponent(cleanFb)}`;
        }

        // 5. LinkedIn: Direct compose body
        if (p.includes("linkedin")) {
            return `https://www.linkedin.com/messaging/compose/?body=${encodedText}`;
        }

        // 6. WhatsApp
        if (p.includes("whatsapp")) {
            const cleanWa = String(rawHandleOrUrl || "").replace(/[^0-9+]/g, "");
            return `https://wa.me/${cleanWa}?text=${encodedText}`;
        }

        // 7. Telegram
        if (p.includes("telegram")) {
            const cleanTg = String(rawHandleOrUrl || "")
                .split("?")[0]
                .replace(/^https?:\/\/t\.me\//i, "")
                .replace(/^@+/, "")
                .replace(/\/+$/, "")
                .trim();
            return `https://t.me/${encodeURIComponent(cleanTg)}?text=${encodedText}`;
        }

        // 8. Discord
        if (p.includes("discord")) {
            if (rawHandleOrUrl && (String(rawHandleOrUrl).includes("discord.gg") || String(rawHandleOrUrl).includes("discord.com"))) {
                return rawHandleOrUrl;
            }
            return `https://discord.com/channels/@me`;
        }

        // 9. Twitch
        if (p.includes("twitch")) {
            const cleanTwitch = String(rawHandleOrUrl || "")
                .split("?")[0]
                .replace(/^https?:\/\/(www\.)?twitch\.tv\//i, "")
                .replace(/^@+/, "")
                .replace(/\/+$/, "")
                .trim();
            if (!cleanTwitch) return "https://www.twitch.tv/";
            return `https://www.twitch.tv/popout/${encodeURIComponent(cleanTwitch)}/chat`;
        }

        // 10. TikTok
        if (p.includes("tiktok")) {
            const cleanTt = String(rawHandleOrUrl || "")
                .split("?")[0]
                .replace(/^https?:\/\/(www\.)?tiktok\.com\/@/i, "")
                .replace(/^@+/, "")
                .replace(/\/+$/, "")
                .trim();
            return cleanTt ? `https://www.tiktok.com/@${encodeURIComponent(cleanTt)}` : `https://www.tiktok.com/messages`;
        }

        // Fallback: Never fall back to profile, try DM handle or direct inbox
        const fallbackHandle = normalizeInstagramHandle(rawHandleOrUrl);
        if (fallbackHandle) {
            return `https://ig.me/m/${encodeURIComponent(fallbackHandle)}`;
        }
        return "https://www.instagram.com/direct/inbox/";
    }

    // Detect mobile touch devices (iOS Safari, Android Chrome, etc.)
    function isMobileDevice() {
        if (typeof navigator === "undefined") return false;
        const ua = navigator.userAgent || navigator.vendor || window.opera || "";
        const isMobileUA = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(ua);
        const isTouchMac = navigator.maxTouchPoints > 1 && /Macintosh/i.test(ua);
        const isNarrowTouch = typeof window !== "undefined" && window.innerWidth <= 768 && ("ontouchstart" in window || navigator.maxTouchPoints > 0);
        return isMobileUA || isTouchMac || isNarrowTouch;
    }

    // Helper: Safely open URL. On mobile, direct navigation triggers OS Universal Links into the native app,
    // avoids mobile browser popup blockers, and preserves session. On desktop, opens in a new tab.
    function openPlatformUrl(url) {
        if (!url) return;
        const isMobile = isMobileDevice();

        if (isMobile) {
            // Direct navigation on mobile triggers OS Universal Links into the native app (e.g. Instagram)
            // without being blocked by Safari or Chrome popup blockers.
            try {
                window.location.href = url;
            } catch (e) {
                console.warn("window.location navigation failed:", e);
                const a = document.createElement("a");
                a.href = url;
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                    try { document.body.removeChild(a); } catch (_) {}
                }, 100);
            }
            return;
        }

        // On Desktop:
        let openedWin = null;
        try {
            openedWin = window.open(url, "_blank", "noopener,noreferrer");
        } catch (e) {
            console.warn("window.open failed:", e);
        }

        if (!openedWin || openedWin.closed || typeof openedWin.closed === "undefined") {
            try {
                const a = document.createElement("a");
                a.href = url;
                a.target = "_blank";
                a.rel = "noopener noreferrer";
                document.body.appendChild(a);
                a.click();
                setTimeout(() => {
                    try { document.body.removeChild(a); } catch (_) {}
                }, 200);
            } catch (err) {
                console.warn("Anchor click fallback failed:", err);
                window.location.href = url;
            }
        }
    }

    // Backwards-compatibility alias
    function openInNewTab(url) {
        openPlatformUrl(url);
    }

    // --------------------------------------------------------------------------
    // State Management
    // --------------------------------------------------------------------------
    const state = {
        sessionId: null,
        stage: "input",
        userRole: "Video editor",
        creator: null,
        discoveredEmail: null,
        emailCandidates: [],
        finalEmail: null,
        emailConfirmed: false,
        emailSource: null,
        emailConfidence: null,
        instagramProfile: null,
        selectedSocialProfile: null,
        activeSocialProfile: null,
        finalInstagramHandle: null,
        finalInstagramUrl: null,
        instagramConfirmed: false,
        discordProfile: null,
        finalDiscordUserId: null,
        discordConfirmed: false,
        socialProfiles: [],
        message: null,
        gmailConnected: false,
        senderEmail: null,
        senderHandle: (() => {
            try {
                return localStorage.getItem("arclent_user_ig_handle") || null;
            } catch (_) {
                return null;
            }
        })(),
        linkedInstagramAccount: null,
        isSending: false,
        selectedChannel: null,
        stageBeforeDelivery: null,
        extensionInstalled: false,
        pendingExtensionSession: null
    };

    // Default assumed connected account for the user (@ummer.04)
    // Allows testing unlinked cases via ?unlinked=true or localStorage
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const forceUnlinked = urlParams.get("unlinked") === "true" || urlParams.get("unlinked") === "1" || urlParams.get("connected") === "false";
        const storedLinked = localStorage.getItem("arclent_linked_instagram");
        if (forceUnlinked || storedLinked === "unlinked" || storedLinked === "none") {
            state.linkedInstagramAccount = null;
        } else if (storedLinked) {
            state.linkedInstagramAccount = storedLinked.replace(/^@+/, "");
        } else {
            // Assume @ummer.04 Instagram account is already connected by default
            state.linkedInstagramAccount = "ummer.04";
        }
    } catch (_) {
        state.linkedInstagramAccount = "ummer.04";
    }

    function saveSessionState() {
        if (!state.sessionId) return;
        try {
            sessionStorage.setItem("arclent_active_session_id", state.sessionId);
            sessionStorage.setItem("arclent_active_session_data", JSON.stringify({
                sessionId: state.sessionId,
                stage: state.stage,
                userRole: state.userRole,
                creator: state.creator,
                selectedChannel: state.selectedChannel,
                finalInstagramHandle: state.finalInstagramHandle,
                finalEmail: state.finalEmail,
                senderEmail: state.senderEmail,
                senderHandle: state.senderHandle,
                linkedInstagramAccount: state.linkedInstagramAccount
            }));
        } catch (e) {}
    }

    // Header elements
    const extensionStatusPill = document.getElementById("extension-status-pill");
    const extensionStatusText = document.getElementById("extension-status-text");
    const gmailStatusPill = document.getElementById("gmail-status-pill");
    const gmailStatusText = document.getElementById("gmail-status-text");
    const headerConnectBtn = document.getElementById("header-connect-btn");
    const headerDisconnectBtn = document.getElementById("header-disconnect-btn");
    const composerDisconnectGmailBtn = document.getElementById("composer-disconnect-gmail-btn");

    // 4-Segment Progress Bar Elements
    const progSeg1 = document.getElementById("prog-seg-1");
    const progSeg2 = document.getElementById("prog-seg-2");
    const progSeg3 = document.getElementById("prog-seg-3");
    const progSeg4 = document.getElementById("prog-seg-4");

    // Screens
    const screens = {
        input: document.getElementById("screen-input"),
        analyzing: document.getElementById("screen-analyzing"),
        verifyEmail: document.getElementById("screen-verify-email"),
        verifyInstagram: document.getElementById("screen-verify-instagram"),
        outreachHub: document.getElementById("screen-outreach-hub"),
        deliverySuccess: document.getElementById("screen-delivery-success")
    };

    // Screen 1 Elements
    const discoveryForm = document.getElementById("discovery-form");
    const youtubeUrlInput = document.getElementById("youtube-url-input");
    const userRoleInput = document.getElementById("user-role-input");
    const sampleChips = document.querySelectorAll(".retro-chip-btn");

    // Screen 2 Stepper Elements
    const progStep1 = document.getElementById("prog-step-1");
    const progStep2 = document.getElementById("prog-step-2");
    const progStep3 = document.getElementById("prog-step-3");
    const progStep4 = document.getElementById("prog-step-4");

    // Screen 3: Step 1 (EMAIL) Elements
    const btnBackEmail = document.getElementById("btn-back-email");
    const igStepPillFromEmail = document.getElementById("ig-step-pill-from-email");
    const emailCreatorThumb = document.getElementById("email-creator-thumb");
    const emailCreatorInitial = document.getElementById("email-creator-initial");
    const emailCreatorAvatar = document.getElementById("email-creator-avatar");
    const emailStepCreatorRole = document.getElementById("email-step-creator-role");
    const emailStepCreatorPlatform = document.getElementById("email-step-creator-platform");

    const emailFoundView = document.getElementById("email-found-view");
    const emailFoundCreatorName = document.getElementById("email-found-creator-name");
    const emailFoundAddress = document.getElementById("email-found-address");
    const emailFoundSourceTag = document.getElementById("email-found-source-tag");
    const btnEmailConfirmYes = document.getElementById("btn-email-confirm-yes");
    const btnEmailConfirmNo = document.getElementById("btn-email-confirm-no");

    const emailFallbackView = document.getElementById("email-fallback-view");
    const emailFallbackDesc = document.getElementById("email-fallback-desc");
    const emailCandidateChipsWrapper = document.getElementById("email-candidate-chips-wrapper");
    const emailCandidateChipsRow = document.getElementById("email-candidate-chips-row");
    const emailManualEntryForm = document.getElementById("email-manual-entry-form");
    const emailManualEntryInput = document.getElementById("email-manual-entry-input");
    const emailManualEntryStatusIcon = document.getElementById("email-manual-entry-status-icon");
    const emailManualEntryErrMsg = document.getElementById("email-manual-entry-err-msg");
    const btnEmailManualSubmit = document.getElementById("btn-email-manual-submit");
    const btnEmailFallbackBack = document.getElementById("btn-email-fallback-back");
    const btnEmailSkipToIg = document.getElementById("btn-email-skip-to-ig");

    // Screen 4: Step 2 (SOCIAL / INSTAGRAM) Elements
    const btnBackIg = document.getElementById("btn-back-ig");
    const igStepPill = document.getElementById("ig-step-pill");
    const emailStepPillFromIg = document.getElementById("email-step-pill-from-ig");
    const igCreatorThumb = document.getElementById("ig-creator-thumb");
    const igCreatorInitial = document.getElementById("ig-creator-initial");
    const igCreatorAvatar = document.getElementById("ig-creator-avatar");
    const igStepCreatorRole = document.getElementById("ig-step-creator-role");
    const igStepCreatorPlatform = document.getElementById("ig-step-creator-platform");

    const igStepHeading = document.getElementById("ig-step-heading");
    const igStepSubheading = document.getElementById("ig-step-subheading");
    const igFoundView = document.getElementById("ig-found-view");
    const igDiscoveredCard = document.getElementById("ig-discovered-card");
    const igDiscoveredIcon = document.getElementById("ig-discovered-icon");
    const igFoundCreatorName = document.getElementById("ig-found-creator-name");
    const igFoundHandle = document.getElementById("ig-found-handle");
    const igFoundLink = document.getElementById("ig-found-link");
    const btnIgConfirmYes = document.getElementById("btn-ig-confirm-yes");
    const btnIgConfirmNo = document.getElementById("btn-ig-confirm-no");

    // Other Socials Accordion Option in Step 2
    const igOtherSocialsSection = document.getElementById("ig-other-socials-section");
    const btnToggleOtherSocials = document.getElementById("btn-toggle-other-socials");
    const igOtherSocialsCount = document.getElementById("ig-other-socials-count");
    const igOtherSocialsContent = document.getElementById("ig-other-socials-content");
    const igOtherSocialsList = document.getElementById("ig-other-socials-list");

    const igFallbackView = document.getElementById("ig-fallback-view");
    const igFallbackHeading = document.getElementById("ig-fallback-heading");
    const igFallbackDesc = document.getElementById("ig-fallback-desc");
    const igSocialChipsWrapper = document.getElementById("ig-social-chips-wrapper");
    const igSocialChipsRow = document.getElementById("ig-social-chips-row");
    const igManualEntryForm = document.getElementById("ig-manual-entry-form");
    const igManualEntryInput = document.getElementById("ig-manual-entry-input");
    const btnIgManualSubmit = document.getElementById("btn-ig-manual-submit");
    const btnIgFallbackBack = document.getElementById("btn-ig-fallback-back");

    // Confirmed View Elements
    const igConfirmedView = document.getElementById("ig-confirmed-view");
    const igConfirmedStatusBadge = document.getElementById("ig-confirmed-status-badge");
    const igConfirmedHeading = document.getElementById("ig-confirmed-heading");
    const igConfirmedSubheading = document.getElementById("ig-confirmed-subheading");
    const igConfirmedIcon = document.getElementById("ig-confirmed-icon");
    const igConfirmedCreatorName = document.getElementById("ig-confirmed-creator-name");
    const igConfirmedHandle = document.getElementById("ig-confirmed-handle");
    const igConfirmedMessageDraft = document.getElementById("ig-confirmed-message-draft");
    const btnIgCopyDraft = document.getElementById("btn-ig-copy-draft");
    const btnIgCopyDraftMain = document.getElementById("btn-ig-copy-draft-main");
    const btnIgCopyText = document.getElementById("btn-ig-copy-text");
    const btnIgOpenSend = document.getElementById("btn-ig-open-send");
    const btnIgToHub = document.getElementById("btn-ig-to-hub");
    const igConfirmedOtherSocialsBox = document.getElementById("ig-confirmed-other-socials-box");
    const igConfirmedOtherSocialsList = document.getElementById("ig-confirmed-other-socials-list");
    const igConfirmedOtherCount = document.getElementById("ig-confirmed-other-count");
    const igExtensionStatusNote = document.getElementById("ig-extension-status-note");
    const igExtensionNoteText = document.getElementById("ig-extension-note-text");

    // Screen 5: Outreach Hub Elements
    const btnBackHub = document.getElementById("btn-back-hub");
    const hubCreatorHeading = document.getElementById("hub-creator-heading");
    const hubSummaryEmailRow = document.getElementById("hub-summary-email-row");
    const hubSummaryEmailVal = document.getElementById("hub-summary-email-val");
    const hubEditEmailBtn = document.getElementById("hub-edit-email-btn");
    const hubSummaryIgRow = document.getElementById("hub-summary-ig-row");
    const hubSummaryIgVal = document.getElementById("hub-summary-ig-val");
    const hubEditIgBtn = document.getElementById("hub-edit-ig-btn");

    const hubEmailBlock = document.getElementById("hub-email-block");
    const workflowEmailRecipient = document.getElementById("workflow-email-recipient");
    const composerRecipientSourceTag = document.getElementById("composer-recipient-source-tag");
    const composerSenderBadge = document.getElementById("composer-sender-badge");
    const composerConnectGmailBtn = document.getElementById("composer-connect-gmail-btn");
    const workflowEmailForm = document.getElementById("workflow-email-form");
    const workflowEmailSubject = document.getElementById("workflow-email-subject");
    const workflowEmailBody = document.getElementById("workflow-email-body");
    const regenerateEmailBtn = document.getElementById("regenerate-email-btn");
    const workflowSendEmailBtn = document.getElementById("workflow-send-email-btn");

    const hubInstagramBlock = document.getElementById("hub-instagram-block");
    const hubDmHeadHandle = document.getElementById("hub-dm-head-handle");
    const instaMessageBody = document.getElementById("insta-message-body");
    const copyInstaMsgBtn = document.getElementById("copy-insta-msg-btn");
    const copyInstaBtnText = document.getElementById("copy-insta-btn-text");
    const openInstagramBtn = document.getElementById("open-instagram-btn");

    // Discord Outreach Elements
    const hubSummaryDiscordRow = document.getElementById("hub-summary-discord-row");
    const hubSummaryDiscordVal = document.getElementById("hub-summary-discord-val");
    const hubEditDiscordBtn = document.getElementById("hub-edit-discord-btn");
    const hubDiscordBlock = document.getElementById("hub-discord-block");
    const discordStatusBadge = document.getElementById("discord-status-badge");
    const discordIdentificationBanner = document.getElementById("discord-identification-banner");
    const discordDiscoveredTarget = document.getElementById("discord-discovered-target");
    const discordUserIdInput = document.getElementById("discord-user-id-input");
    const btnDiscordSetId = document.getElementById("btn-discord-set-id");
    const discordErrorAlert = document.getElementById("discord-error-alert");
    const discordErrorMessage = document.getElementById("discord-error-message");
    const hubDiscordHeadHandle = document.getElementById("hub-discord-head-handle");
    const discordMessageBody = document.getElementById("discord-message-body");
    const btnSendDiscordBot = document.getElementById("btn-send-discord-bot");
    const btnSendDiscordText = document.getElementById("btn-send-discord-text");
    const btnCopyDiscordMsg = document.getElementById("btn-copy-discord-msg");
    const btnCopyDiscordText = document.getElementById("btn-copy-discord-text");

    // Helper: Automatically Update Sender Handle (from Extension or Context)
    function setSenderHandle(handle, syncBackend = true) {
        if (!handle) return;
        const clean = String(handle).replace(/^@+/, '').trim();
        if (!clean) return;
        state.senderHandle = clean;
        try {
            localStorage.setItem("arclent_user_ig_handle", clean);
        } catch (_) {}
        saveSessionState();

        if (syncBackend && state.sessionId) {
            const senderIdentity = `${clean} on Arclent`;
            fetch("/api/outreach/record-social-outreach", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    platform: "Instagram",
                    sender_handle: clean,
                    sender_identity: senderIdentity
                })
            }).catch(() => {});
        }
    }

    const hubOtherSocialsBlock = document.getElementById("hub-other-socials-block");
    const hubSocialsGrid = document.getElementById("hub-socials-grid");

    // Screen 6: Delivery & Status Polling Elements
    const deliveryHeaderRow = document.getElementById("delivery-header-row") || document.querySelector(".delivery-header-row");
    const btnBackDelivery = document.getElementById("btn-back-delivery");
    const verificationDmReadyBox = document.getElementById("verification-dm-ready-box");
    const vDmReadySub = document.getElementById("v-dm-ready-sub");
    const vDmReadyGuideText = document.getElementById("v-dm-ready-guide-text");
    const btnConfirmDmSent = document.getElementById("btn-confirm-dm-sent");
    const verificationPendingBox = document.getElementById("verification-pending-box");
    const verificationSuccessBox = document.getElementById("verification-success-box");
    const verificationRejectedBox = document.getElementById("verification-rejected-box");
    const vPendingRecipientSub = document.getElementById("v-pending-recipient-sub");
    const vSuccessRecipientSub = document.getElementById("v-success-recipient-sub");
    const vRejectedRecipientSub = document.getElementById("v-rejected-recipient-sub");
    const vShieldAudienceText = document.getElementById("v-shield-audience-text");
    const vRejectedDescText = document.getElementById("v-rejected-desc-text");

    // Auto-Verification Elements
    const autoVerifyFallbackBanner = document.getElementById("auto-verify-fallback-banner");
    const autoVerifyFallbackReason = document.getElementById("auto-verify-fallback-reason");
    const verificationAutoVerifiedBox = document.getElementById("verification-auto-verified-box");
    const vAutoMatchedHandle = document.getElementById("v-auto-matched-handle");
    const vAutoVerifiedDesc = document.getElementById("v-auto-verified-desc");
    const vAutoCreatorName = document.getElementById("v-auto-creator-name");
    const vAutoCreatorSubs = document.getElementById("v-auto-creator-subs");
    const vAutoRoleName = document.getElementById("v-auto-role-name");
    const vAutoVideoTitle = document.getElementById("v-auto-video-title");
    const vAutoMatchedAccountVal = document.getElementById("v-auto-matched-account-val");
    const hubCreatorSubs = document.getElementById("hub-creator-subs");

    const toastContainer = document.getElementById("toast-container");
    const resetButtons = document.querySelectorAll(".reset-workflow-btn");

    // Modal & Banner Elements for Connecting Instagram (when description credits are detected)
    const modalConnectInstagram = document.getElementById("modal-connect-instagram");
    const btnModalCiClose = document.getElementById("btn-modal-ci-close");
    const modalCiTitle = document.getElementById("modal-ci-title");
    const modalCiDesc = document.getElementById("modal-ci-desc");
    const modalDetectedHandlesList = document.getElementById("modal-detected-handles-list");
    const modalCiChipsContainer = document.getElementById("modal-ci-chips-container");
    const modalCiChipsRow = document.getElementById("modal-ci-chips-row");
    const modalCiForm = document.getElementById("modal-ci-form");
    const modalCiInput = document.getElementById("modal-ci-input");
    const modalCiErr = document.getElementById("modal-ci-err");
    const btnModalCiSubmit = document.getElementById("btn-modal-ci-submit");
    const btnModalCiSkip = document.getElementById("btn-modal-ci-skip");

    const bannerCreditsDetected = document.getElementById("banner-credits-detected");
    const bannerCreditsHandles = document.getElementById("banner-credits-handles");
    const btnBannerConnectIg = document.getElementById("btn-banner-connect-ig");

    let currentModalExtractedHandles = [];

    function showCreditsDetectedBanner(handles) {
        if (!bannerCreditsDetected) return;
        const list = handles && handles.length > 0 ? handles : [];
        if (list.length === 0) {
            bannerCreditsDetected.classList.add("hidden");
            return;
        }
        const formatted = list.map(h => {
            const trimmed = (h || "").trim();
            if (trimmed.includes(" ")) {
                return `"${trimmed}"`;
            }
            return `@${trimmed.replace(/^@+/, '')}`;
        }).join(", ");
        if (bannerCreditsHandles) bannerCreditsHandles.textContent = formatted;
        bannerCreditsDetected.classList.remove("hidden");
    }

    function hideCreditsDetectedBanner() {
        if (bannerCreditsDetected) bannerCreditsDetected.classList.add("hidden");
    }

    function showConnectInstagramModal(handles = [], discoveryData = null) {
        if (!modalConnectInstagram) return;

        // CRITICAL: Must ONLY show up when it starts processing and NOT on the first page
        if (screens.input && !screens.input.classList.contains("hidden")) {
            return;
        }
        if (state.stage === "input" || !state.sessionId) {
            return;
        }

        // CRITICAL: Must ONLY be there if user has NOT connected
        if (state.linkedInstagramAccount) {
            return;
        }

        // CRITICAL: Must ONLY be there if credits are mentioned in the given video
        const rawHandles = Array.isArray(handles) ? handles : [];
        const cleanHandles = rawHandles.filter(h => h && typeof h === "string" && h.trim().length > 0);
        if (cleanHandles.length === 0) {
            return;
        }

        currentModalExtractedHandles = cleanHandles;
        const formatted = currentModalExtractedHandles.map(h => {
            const trimmed = (h || "").trim();
            if (trimmed.includes(" ")) {
                return `"${trimmed}"`;
            }
            return `@${trimmed.replace(/^@+/, '')}`;
        }).join(", ");
        if (modalDetectedHandlesList) modalDetectedHandlesList.textContent = formatted;
        if (modalCiTitle) modalCiTitle.textContent = "Credits are already mentioned!";
        if (modalCiDesc) {
            const roleStr = state.userRole ? `for ${escapeHtml(state.userRole.toLowerCase())} ` : "";
            modalCiDesc.innerHTML = `Credits ${roleStr}<strong>${escapeHtml(formatted)}</strong> were found in the video description. To get <strong>auto-verified</strong>, connect your Instagram account.`;
        }

        if (modalCiChipsRow && modalCiChipsContainer) {
            modalCiChipsRow.innerHTML = "";
            currentModalExtractedHandles.forEach(h => {
                const trimmed = (h || "").trim();
                const isName = trimmed.includes(" ");
                const chipLabel = isName ? `"${trimmed}"` : `@${trimmed.replace(/^@+/, '')}`;
                const cleanValue = isName ? trimmed.toLowerCase().replace(/[^a-z0-9_\.]/g, '') : trimmed.replace(/^@+/, '');

                const chip = document.createElement("button");
                chip.type = "button";
                chip.className = "modal-chip-btn";
                chip.textContent = chipLabel;
                chip.addEventListener("click", () => {
                    if (modalCiInput) {
                        modalCiInput.value = cleanValue;
                        modalCiInput.focus();
                    }
                    modalCiChipsRow.querySelectorAll(".modal-chip-btn").forEach(c => c.classList.remove("selected"));
                    chip.classList.add("selected");
                });
                modalCiChipsRow.appendChild(chip);
            });
            modalCiChipsContainer.classList.remove("hidden");
        }

        // Pre-fill input if only 1 handle
        if (currentModalExtractedHandles.length === 1 && modalCiInput) {
            const single = currentModalExtractedHandles[0].trim();
            if (single.includes(" ")) {
                modalCiInput.value = single.toLowerCase().replace(/[^a-z0-9_\.]/g, '');
            } else {
                modalCiInput.value = single.replace(/^@+/, '');
            }
        } else if (modalCiInput && !modalCiInput.value && state.linkedInstagramAccount) {
            modalCiInput.value = state.linkedInstagramAccount;
        }

        if (modalCiErr) modalCiErr.classList.add("hidden");
        modalConnectInstagram.classList.remove("hidden");
        setTimeout(() => {
            if (modalCiInput) modalCiInput.focus();
        }, 60);
    }

    function hideConnectInstagramModal() {
        if (modalConnectInstagram) {
            modalConnectInstagram.classList.add("hidden");
        }
    }

    if (btnBannerConnectIg) {
        btnBannerConnectIg.addEventListener("click", () => {
            const extracted = (state.autoVerification && state.autoVerification.extracted_accounts) || currentModalExtractedHandles || [];
            if (extracted.length > 0 && !state.linkedInstagramAccount) {
                showConnectInstagramModal(extracted);
            }
        });
    }

    if (modalCiForm) {
        modalCiForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const rawVal = modalCiInput ? modalCiInput.value.trim() : "";
            const cleanHandle = rawVal.replace(/^@+/, "").trim().toLowerCase();

            if (!cleanHandle) {
                if (modalCiErr) {
                    modalCiErr.textContent = "Please enter your Instagram username";
                    modalCiErr.classList.remove("hidden");
                }
                return;
            }

            state.linkedInstagramAccount = cleanHandle;
            try {
                localStorage.setItem("arclent_linked_instagram", cleanHandle);
            } catch (_) {}
            saveSessionState();

            const isMatch = currentModalExtractedHandles.map(h => h.replace(/^@+/, '').toLowerCase()).includes(cleanHandle);

            let verifyData = null;
            if (state.sessionId) {
                try {
                    const res = await fetch("/api/outreach/verify-linked-account", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            session_id: state.sessionId,
                            instagram_account: cleanHandle
                        })
                    });
                    if (res.ok) {
                        verifyData = await res.json();
                    }
                } catch (_) {}
            }

            if (btnModalCiSubmit) {
                btnModalCiSubmit.disabled = true;
                btnModalCiSubmit.textContent = "Connecting... Redirecting to Instagram ↗";
            }

            // Redirect user to Instagram login page
            window.location.href = "https://www.instagram.com/accounts/login/";
        });
    }

    if (btnModalCiClose) {
        btnModalCiClose.addEventListener("click", () => {
            hideConnectInstagramModal();
        });
    }

    if (btnModalCiSkip) {
        btnModalCiSkip.addEventListener("click", () => {
            hideConnectInstagramModal();
        });
    }

    if (modalConnectInstagram) {
        modalConnectInstagram.addEventListener("click", (e) => {
            if (e.target === modalConnectInstagram) {
                hideConnectInstagramModal();
            }
        });
    }

    let verificationPollInterval = null;

    // --------------------------------------------------------------------------
    // Toast Utility
    // --------------------------------------------------------------------------
    function showToast(message, type = "success", durationMs = 3500) {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        const icon = type === "success" ? "✓" : type === "error" ? "✕" : "!";
        toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(8px)";
            toast.style.transition = "all 0.25s ease";
            setTimeout(() => toast.remove(), 250);
        }, durationMs);
        return toast;
    }

    // --------------------------------------------------------------------------
    // 4-Segment Progress Bar Manager
    // --------------------------------------------------------------------------
    function setStepTracker(activeStepNum) {
        const segs = [progSeg1, progSeg2, progSeg3, progSeg4];
        segs.forEach((seg, idx) => {
            if (!seg) return;
            const stepNum = idx + 1;
            seg.className = "seg-bar";
            if (stepNum === activeStepNum) {
                seg.classList.add("active");
            } else if (stepNum < activeStepNum) {
                seg.classList.add("completed");
            }
        });
    }

    function showScreen(screenKey, stepNum) {
        Object.keys(screens).forEach((key) => {
            if (screens[key]) {
                screens[key].classList.add("hidden");
                screens[key].classList.remove("active");
            }
        });

        if (screens[screenKey]) {
            screens[screenKey].classList.remove("hidden");
            screens[screenKey].classList.add("active");
        }

        // On the first page, ensure connect modal and credits banner are strictly hidden
        if (screenKey === "input") {
            hideConnectInstagramModal();
            hideCreditsDetectedBanner();
        }

        if (stepNum) {
            setStepTracker(stepNum);
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // --------------------------------------------------------------------------
    // Gmail Status & OAuth Handler
    // --------------------------------------------------------------------------
    async function checkGmailStatus() {
        try {
            const res = await fetch("/api/gmail/status");
            if (!res.ok) throw new Error("Status check failed");
            const data = await res.json();
            state.gmailConnected = !!data.connected;
            state.senderEmail = data.email || null;
            updateGmailUI();
        } catch (err) {
            state.gmailConnected = false;
            state.senderEmail = null;
            updateGmailUI();
        }
    }

    function updateGmailUI() {
        if (state.gmailConnected && state.senderEmail) {
            if (gmailStatusPill) gmailStatusPill.className = "status-pill status-connected";
            if (gmailStatusText) gmailStatusText.textContent = `Gmail: ${state.senderEmail} ✓`;
            if (headerConnectBtn) headerConnectBtn.style.display = "none";
            if (headerDisconnectBtn) headerDisconnectBtn.style.display = "inline-block";

            if (composerSenderBadge) {
                composerSenderBadge.textContent = `${state.senderEmail} ✓ Connected`;
                composerSenderBadge.style.color = "var(--color-green-text)";
            }
            if (composerConnectGmailBtn) composerConnectGmailBtn.style.display = "none";
            if (composerDisconnectGmailBtn) composerDisconnectGmailBtn.style.display = "inline-block";
        } else {
            if (gmailStatusPill) gmailStatusPill.className = "status-pill status-disconnected";
            if (gmailStatusText) gmailStatusText.textContent = "Gmail: Not connected";
            if (headerConnectBtn) headerConnectBtn.style.display = "inline-block";
            if (headerDisconnectBtn) headerDisconnectBtn.style.display = "none";

            if (composerSenderBadge) {
                composerSenderBadge.textContent = "Not connected (OAuth required)";
                composerSenderBadge.style.color = "var(--color-accent-amber)";
            }
            if (composerConnectGmailBtn) composerConnectGmailBtn.style.display = "inline-block";
            if (composerDisconnectGmailBtn) composerDisconnectGmailBtn.style.display = "none";
        }

        validateSendButton();
    }

    async function handleConnectGmail() {
        if (state.isConnectingGmail) return;
        state.isConnectingGmail = true;
        try {
            showToast("Opening Google Sign-In...", "warning");
            const res = await fetch("/api/gmail/connect");
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to initiate Gmail OAuth");
            }
            const data = await res.json();
            
            if (data.auth_url) {
                const width = 520, height = 650;
                const left = Math.max(0, (window.innerWidth - width) / 2);
                const top = Math.max(0, (window.innerHeight - height) / 2);
                const authWindow = window.open(
                    data.auth_url,
                    "Gmail_OAuth",
                    `width=${width},height=${height},top=${top},left=${left},status=no,toolbar=no,menubar=no`
                );

                if (!authWindow || authWindow.closed || typeof authWindow.closed === "undefined") {
                    window.location.href = data.auth_url;
                    return;
                }

                let pollCount = 0;
                const timer = setInterval(async () => {
                    pollCount++;
                    let isClosed = false;
                    try { isClosed = authWindow.closed; } catch (e) {}

                    if (isClosed || pollCount % 2 === 0) {
                        await checkGmailStatus();
                        if (state.gmailConnected || isClosed || pollCount > 90) {
                            clearInterval(timer);
                            state.isConnectingGmail = false;
                        }
                    }
                }, 1200);
            }
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            setTimeout(() => { state.isConnectingGmail = false; }, 2000);
        }
    }

    async function handleDisconnectGmail() {
        try {
            const res = await fetch("/api/gmail/disconnect", { method: "POST" });
            if (!res.ok) throw new Error("Disconnect failed");
            
            state.gmailConnected = false;
            state.senderEmail = null;
            updateGmailUI();
            showToast("Gmail account disconnected.");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    if (headerConnectBtn) headerConnectBtn.onclick = handleConnectGmail;
    if (headerDisconnectBtn) headerDisconnectBtn.onclick = handleDisconnectGmail;
    if (composerConnectGmailBtn) composerConnectGmailBtn.onclick = handleConnectGmail;
    if (composerDisconnectGmailBtn) composerDisconnectGmailBtn.onclick = handleDisconnectGmail;

    window.addEventListener("message", (event) => {
        if (event.data && event.data.type === "GMAIL_AUTH_SUCCESS") {
            showToast(`Connected Gmail: ${event.data.email}`);
            checkGmailStatus();
        } else if (event.data && event.data.type === "GMAIL_AUTH_FAILED") {
            showToast(`OAuth Error: ${event.data.error}`, "error");
            checkGmailStatus();
        }
    });

    if (window.location.search.includes("gmail_connected=true")) {
        showToast("Gmail account connected successfully!");
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // --------------------------------------------------------------------------
    // Step 1: Form & Discovery Start
    // --------------------------------------------------------------------------
    function isValidYouTubeUrl(url) {
        if (!url) return false;
        const u = url.trim().toLowerCase();
        return u.includes("youtube.com") || u.includes("youtu.be") || u.startsWith("@");
    }

    if (discoveryForm) {
        discoveryForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const url = youtubeUrlInput.value.trim();
            const role = userRoleInput ? (userRoleInput.value.trim() || "Video editor") : "Video editor";
            state.userRole = role;

            if (!isValidYouTubeUrl(url)) {
                showToast("Please enter a valid YouTube video or channel URL.", "error");
                youtubeUrlInput.focus();
                return;
            }
            startDiscovery(url, role);
        });
    }

    sampleChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const sampleUrl = chip.getAttribute("data-url");
            const sampleRole = chip.getAttribute("data-role") || "Video editor";
            if (youtubeUrlInput) youtubeUrlInput.value = sampleUrl;
            if (userRoleInput) userRoleInput.value = sampleRole;
            state.userRole = sampleRole;
            startDiscovery(sampleUrl, sampleRole);
        });
    });

    function updateStepper(stepIndex, status, detailText = "") {
        const steps = [progStep1, progStep2, progStep3, progStep4];
        steps.forEach((stepEl, idx) => {
            if (!stepEl) return;
            const iconEl = stepEl.querySelector(".step-icon");
            const detailEl = stepEl.querySelector(".step-detail");
            
            if (idx + 1 < stepIndex) {
                stepEl.className = "progress-step-item completed";
                iconEl.textContent = "✓";
            } else if (idx + 1 === stepIndex) {
                if (status === "running") {
                    stepEl.className = "progress-step-item active";
                    iconEl.textContent = "●";
                } else if (status === "completed") {
                    stepEl.className = "progress-step-item completed";
                    iconEl.textContent = "✓";
                } else if (status === "error") {
                    stepEl.className = "progress-step-item error";
                    iconEl.textContent = "✕";
                }
                if (detailText && detailEl) detailEl.textContent = detailText;
            } else {
                stepEl.className = "progress-step-item";
                iconEl.textContent = "○";
            }
        });
    }

    function startDiscovery(youtubeUrl, role) {
        state.stage = "discovering";
        state.sessionId = null;
        state.creator = null;
        state.discoveredEmail = null;
        state.emailCandidates = [];
        state.finalEmail = null;
        state.emailConfirmed = false;
        state.instagramProfile = null;
        state.finalInstagramHandle = null;
        state.finalInstagramUrl = null;
        state.instagramConfirmed = false;
        state.socialProfiles = [];
        state.userRole = role || (userRoleInput ? userRoleInput.value.trim() : "Video editor") || "Video editor";

        showScreen("analyzing", 2);
        updateStepper(1, "running");

        const linkedAccountParam = encodeURIComponent(state.linkedInstagramAccount || "");
        const sseUrl = `/api/outreach/stream?youtube_url=${encodeURIComponent(youtubeUrl)}&user_role=${encodeURIComponent(state.userRole)}&linked_account=${linkedAccountParam}`;
        let eventSource = null;
        let isFinalized = false;

        try {
            eventSource = new EventSource(sseUrl);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.session_id && !state.sessionId) {
                        state.sessionId = data.session_id;
                    }

                    if (data.status === "error") {
                        eventSource.close();
                        handleDiscoveryError(data.error || "We couldn't identify the creator from this URL.");
                        return;
                    }

                    if (data.step >= 1 && data.step <= 4) {
                        updateStepper(data.step, data.status, data.label);
                    }

                    // Early credit detection right when processing starts & metadata is parsed
                    if (data.step === 2 && data.status === "completed" && data.extracted_accounts && data.extracted_accounts.length > 0) {
                        if (!state.linkedInstagramAccount) {
                            showConnectInstagramModal(data.extracted_accounts);
                        }
                    } else if (data.step === 6 && data.status === "completed" && data.data) {
                        isFinalized = true;
                        eventSource.close();
                        updateStepper(4, "completed", "Evidence verified");
                        setTimeout(() => handleDiscoveryCompleted(data.data), 400);
                    }
                } catch (err) {
                    console.error("SSE parse error:", err);
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                if (!isFinalized) {
                    executeStandardDiscoveryPost(youtubeUrl);
                }
            };
        } catch (e) {
            executeStandardDiscoveryPost(youtubeUrl);
        }
    }

    async function executeStandardDiscoveryPost(youtubeUrl) {
        try {
            updateStepper(2, "running", "Processing via backend agent...");
            const res = await fetch("/api/outreach/discover", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    youtube_url: youtubeUrl,
                    user_role: state.userRole,
                    linked_instagram_account: state.linkedInstagramAccount || ""
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Discovery failed");
            }

            const data = await res.json();
            handleDiscoveryCompleted(data);
        } catch (err) {
            handleDiscoveryError(err.message);
        }
    }

    function handleDiscoveryError(msg) {
        showToast(msg, "error");
        showScreen("input", 1);
    }

    function handleDiscoveryCompleted(data) {
        state.sessionId = data.session_id;

        if (data.creator && typeof data.creator === "object") {
            state.creator = data.creator;
        } else {
            const rawName = data.creator_name || data.channel_name || "Creator";
            const rawHandle = data.channel_handle || (rawName ? `@${rawName.toLowerCase().replace(/\s+/g, '')}` : "@creator");
            state.creator = {
                name: rawName,
                channel_name: data.channel_name || rawName,
                channel_handle: rawHandle,
                channel_url: data.channel_url || data.video_url || "#",
                profile_image: data.profile_image || null,
                subscriber_count: data.subscriber_count || "Active Creator",
                video_title: data.video_title || "YouTube Video",
                video_url: data.video_url || "#"
            };
        }

        state.discoveredEmail = data.discovered_email || (data.selected_email ? {
            email: data.selected_email,
            source: data.email_source || "YouTube Description",
            confidence: data.email_confidence || "high",
            source_type: data.email_source_type || "publicly_published"
        } : null);

        state.emailCandidates = data.email_candidates || [];

        if (state.discoveredEmail && state.discoveredEmail.email) {
            state.finalEmail = state.discoveredEmail.email;
            state.emailSource = state.discoveredEmail.source;
            state.emailConfidence = state.discoveredEmail.confidence;
        } else {
            state.finalEmail = null;
            state.emailSource = null;
            state.emailConfidence = null;
        }

        state.socialProfiles = data.social_profiles || [];
        state.instagramProfile = data.instagram_profile || state.socialProfiles.find(s => (s.platform || "").toLowerCase() === "instagram") || null;
        state.selectedSocialProfile = state.instagramProfile || null;

        state.discordProfile = data.discord_profile || null;
        if (!state.discordProfile) {
            const discSocial = state.socialProfiles.find(s => (s.platform || "").toLowerCase() === "discord");
            if (discSocial) {
                state.discordProfile = {
                    discord_invite: discSocial.discord_invite || (discSocial.url && discSocial.url.includes("discord.gg") ? discSocial.url : null),
                    discord_username: discSocial.discord_username || (discSocial.username && !discSocial.username.includes("http") ? discSocial.username : null),
                    discord_user_id: discSocial.discord_user_id || null,
                    discord_source: discSocial.discord_source || "youtube_description",
                    status: discSocial.status || (discSocial.discord_user_id ? "sendable" : "discovered"),
                    url: discSocial.url
                };
            }
        }
        if (state.discordProfile && state.discordProfile.discord_user_id) {
            state.finalDiscordUserId = state.discordProfile.discord_user_id;
        } else {
            state.finalDiscordUserId = null;
        }

        if (state.instagramProfile) {
            state.finalInstagramHandle = formatHandle(state.instagramProfile.username);
            state.finalInstagramUrl = state.instagramProfile.url;
        } else {
            state.finalInstagramHandle = null;
            state.finalInstagramUrl = null;
        }

        // Store auto-verification result in state
        state.autoVerification = data.auto_verification || null;

        // CASE 1: Automatically Verified via YouTube Description Match
        if (data.auto_verification && data.auto_verification.verified) {
            hideCreditsDetectedBanner();
            hideConnectInstagramModal();
            renderAutoVerifiedSuccess(data.auto_verification);
            return;
        }

        const extracted = (data.auto_verification && data.auto_verification.extracted_accounts) || [];
        const isUnlinked = !state.linkedInstagramAccount;

        // CASE 2: Credits are already mentioned in the description and user hasn't linked Instagram
        if (isUnlinked && extracted.length > 0) {
            state.stage = "verify_email";
            renderVerifyEmailStep();
            showScreen("verifyEmail", 3);
            showCreditsDetectedBanner(extracted);
            showConnectInstagramModal(extracted, data);
            return;
        }

        // CASE 3: No credits mentioned or not verified -> keep connect modal & banner hidden
        if (autoVerifyFallbackBanner) {
            autoVerifyFallbackBanner.classList.add("hidden");
        }
        hideCreditsDetectedBanner();
        hideConnectInstagramModal();

        // START SPECIFICALLY FROM 1 · EMAIL (Existing Verification Workflow)
        state.stage = "verify_email";
        renderVerifyEmailStep();
        showScreen("verifyEmail", 3);
    }

    // --------------------------------------------------------------------------
    // Format Confirmation Draft Messages
    // --------------------------------------------------------------------------
    function getVerificationLink() {
        const origin = window.location.origin && window.location.origin !== "null" ? window.location.origin : "http://127.0.0.1:8000";
        if (state.sessionId) {
            return `${origin}/verify?session_id=${encodeURIComponent(state.sessionId)}`;
        }
        return `${origin}/verify`;
    }

    function generateConfirmationDraft(creatorName, videoTitle, role) {
        const target = creatorName || "there";
        const roleStr = (role || state.userRole || "Video editor").trim();
        const vTitle = (videoTitle || "your video").trim();
        const sender = state.senderHandle ? `@${state.senderHandle.replace(/^@+/, '')}` : (state.senderEmail || "your collaborator");
        return `Hi ${target}, ${sender} claims they worked as ${roleStr} on "${vTitle}". Can you confirm this collaboration?`;
    }

    function generateSocialDmDraft(creatorName, videoTitle, role, platformName = "Instagram") {
        const target = creatorName || "there";
        const roleStr = (role || state.userRole || "Video editor").trim();
        const vTitle = (videoTitle || "your video").trim();
        const verifyUrl = getVerificationLink();
        return `Hey ${target}! I added our work together (${roleStr} on "${vTitle}") to my Arclent portfolio. Could you confirm it here so it shows as verified?\n\nConfirm at: ${verifyUrl}`;
    }

    function generateInstagramDmDraft(creatorName, videoTitle, role) {
        return generateSocialDmDraft(creatorName, videoTitle, role, "Instagram");
    }

    // --------------------------------------------------------------------------
    // Universal Cross-Browser Clipboard Copy Engine (Chrome, Edge, Firefox, Safari, Mobile)
    // --------------------------------------------------------------------------
    function execCommandCopy(text) {
        if (!text) return false;
        let successful = false;
        const prevActive = document.activeElement;
        try {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.readOnly = false;
            // Native, clean off-screen element without contenteditable
            textarea.style.position = "fixed";
            textarea.style.top = "0";
            textarea.style.left = "0";
            textarea.style.width = "1px";
            textarea.style.height = "1px";
            textarea.style.padding = "0";
            textarea.style.margin = "0";
            textarea.style.border = "none";
            textarea.style.outline = "none";
            textarea.style.boxShadow = "none";
            textarea.style.background = "transparent";
            textarea.style.opacity = "0";
            textarea.style.fontSize = "16px";
            document.body.appendChild(textarea);

            textarea.focus({ preventScroll: true });
            textarea.select();
            textarea.setSelectionRange(0, text.length);

            successful = document.execCommand("copy");
            document.body.removeChild(textarea);
        } catch (e) {
            console.warn("Cross-browser execCommand copy fallback failed:", e);
        }
        if (prevActive && typeof prevActive.focus === "function") {
            try { prevActive.focus({ preventScroll: true }); } catch (_) {}
        }
        return successful;
    }

    async function copyTextToClipboard(text) {
        if (!text) return false;
        // Step 1: Immediately execute synchronous fallback within user gesture
        let copied = execCommandCopy(text);

        // Step 2: Also trigger modern async Clipboard API if supported and document has focus
        if (navigator.clipboard && typeof navigator.clipboard.writeText === "function" && window.isSecureContext !== false) {
            try {
                await navigator.clipboard.writeText(text);
                copied = true;
            } catch (err) {
                console.warn("navigator.clipboard.writeText warning (fallback already executed):", err);
            }
        }
        return copied;
    }

    function fallbackClipboardCopy(text) {
        return copyTextToClipboard(text);
    }

    // --------------------------------------------------------------------------
    // Chrome Extension Integration & Handshake
    // --------------------------------------------------------------------------
    function updateExtensionStatusUI(isInstalled) {
        state.extensionInstalled = !!isInstalled;
        // Don't show extension status pills or notes in user-facing UI per user preference
        if (extensionStatusPill) {
            extensionStatusPill.style.display = "none";
        }
        if (igExtensionStatusNote) {
            igExtensionStatusNote.style.display = "none";
        }
    }

    // Immediate and event-driven extension presence check
    function checkDirectDomPresence() {
        if (document.documentElement && (
            document.documentElement.getAttribute("data-arclent-instagram-extension") === "installed" ||
            document.documentElement.dataset.arclentInstagramExtension === "installed" ||
            document.documentElement.dataset.arclentExtensionVersion
        )) {
            updateExtensionStatusUI(true);
            return true;
        }
        return false;
    }

    async function isInstagramExtensionInstalled(timeoutMs = 500) {
        if (checkDirectDomPresence()) {
            return true;
        }

        return new Promise((resolve) => {
            let resolved = false;

            function onMessage(e) {
                if (e.data && (e.data.type === "ARCLENT_EXTENSION_PONG" || e.data.type === "ARCLENT_INSTAGRAM_EXTENSION_READY")) {
                    resolved = true;
                    window.removeEventListener("message", onMessage);
                    updateExtensionStatusUI(true);
                    resolve(true);
                }
            }

            function onCustomEvent() {
                resolved = true;
                window.removeEventListener("ARCLENT_INSTAGRAM_EXTENSION_READY", onCustomEvent);
                updateExtensionStatusUI(true);
                resolve(true);
            }

            window.addEventListener("message", onMessage);
            window.addEventListener("ARCLENT_INSTAGRAM_EXTENSION_READY", onCustomEvent);
            window.postMessage({ type: "ARCLENT_CHECK_EXTENSION" }, "*");

            setTimeout(() => {
                if (!resolved) {
                    window.removeEventListener("message", onMessage);
                    window.removeEventListener("ARCLENT_INSTAGRAM_EXTENSION_READY", onCustomEvent);
                    const isInstalled = checkDirectDomPresence();
                    updateExtensionStatusUI(isInstalled);
                    resolve(isInstalled);
                }
            }, timeoutMs);
        });
    }

    // Global persistent listeners for extension announcements
    window.addEventListener("ARCLENT_INSTAGRAM_EXTENSION_READY", () => updateExtensionStatusUI(true));
    window.addEventListener("message", (e) => {
        if (e.data && (e.data.type === "ARCLENT_EXTENSION_PONG" || e.data.type === "ARCLENT_INSTAGRAM_EXTENSION_READY")) {
            updateExtensionStatusUI(true);
        }
    });

    // Make status pill clickable to re-check
    if (extensionStatusPill) {
        extensionStatusPill.style.cursor = "pointer";
        extensionStatusPill.addEventListener("click", async () => {
            if (extensionStatusText) extensionStatusText.textContent = "Extension: Checking...";
            const installed = await isInstagramExtensionInstalled(800);
            if (installed) {
                showToast("✓ Arclent Instagram Extension is connected & active!");
            } else {
                showToast("Extension not detected. Make sure to reload the extension in chrome://extensions and refresh this page.", "warning");
            }
        });
    }

    // Multi-stage auto-detection on load
    checkDirectDomPresence();
    setTimeout(() => { isInstagramExtensionInstalled(400); }, 300);
    setTimeout(() => { isInstagramExtensionInstalled(500); }, 1200);
    setTimeout(() => { isInstagramExtensionInstalled(600); }, 2500);

    // Handle extension outreach dispatch
    async function dispatchInstagramWithExtension({ username, message, sessionId }) {
        const cleanUsername = normalizeInstagramHandle(username);
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const handle = formatHandle(cleanUsername);

        state.pendingExtensionSession = {
            username: cleanUsername,
            handle: handle,
            message: message,
            sessionId: sessionId
        };

        // Post outreach message to extension via bridge
        window.postMessage({
            type: "ARCLENT_INSTAGRAM_OUTREACH",
            username: cleanUsername,
            message: message,
            sessionId: sessionId,
            backendOrigin: window.location.origin,
            senderHandle: state.senderHandle || null,
            source: "arclent"
        }, "*");

        // Robust clipboard backup
        fallbackClipboardCopy(message);

        // Transition Arclent UI to "Instagram DM Ready" state (NEVER assuming sent until user confirms)
        state.stageBeforeDelivery = state.stage === "verify_instagram" ? "verify_instagram" : "outreach_hub";
        state.stage = "sent";
        state.selectedChannel = "instagram";
        saveSessionState();

        if (vDmReadySub) {
            vDmReadySub.textContent = `Your message has been added to @${cleanUsername}'s Instagram composer.`;
        }
        if (vDmReadyGuideText) {
            vDmReadyGuideText.textContent = `We opened ${creatorName}'s DM in Instagram and populated your draft. Review the message and click Send in Instagram.`;
        }

        if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
        if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
        if (verificationDmReadyBox) verificationDmReadyBox.classList.remove("hidden");
        if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
        if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

        showScreen("deliverySuccess", 4);
        showToast(`✓ Opening Instagram DM for @${cleanUsername}... Review & click Send!`);

        // Notify backend of social outreach dispatch immediately
        if (state.sessionId) {
            const senderIdentity = state.senderHandle ? `${state.senderHandle.replace(/^@+/, '')} on Arclent` : "Someone on Arclent";
            fetch("/api/outreach/record-social-outreach", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    platform: "Instagram",
                    handle: handle,
                    sender_handle: state.senderHandle || null,
                    sender_identity: senderIdentity,
                    message: message
                })
            }).catch(() => {});
        }

        // Start live verification polling immediately (without waiting for user to click "I've Sent the Message")
        startVerificationPolling();
    }

    // Confirmation handler for "I've Sent the Message"
    if (btnConfirmDmSent) {
        btnConfirmDmSent.onclick = async () => {
            try {
                btnConfirmDmSent.disabled = true;
                btnConfirmDmSent.innerHTML = `<span>Recording Dispatch...</span>`;

                const c = state.creator || {};
                const creatorName = c.name || c.channel_name || "Creator";
                const handle = state.finalInstagramHandle || (state.pendingExtensionSession ? state.pendingExtensionSession.handle : "@creator");
                const message = (state.pendingExtensionSession ? state.pendingExtensionSession.message : "") || "";
                const senderIdentity = state.senderHandle ? `${state.senderHandle.replace(/^@+/, '')} on Arclent` : "Someone on Arclent";

                // Record social outreach on backend
                if (state.sessionId) {
                    await fetch("/api/outreach/record-social-outreach", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            session_id: state.sessionId,
                            platform: "Instagram",
                            handle: handle,
                            sender_handle: state.senderHandle || null,
                            sender_identity: senderIdentity,
                            message: message
                        })
                    }).catch(() => {});
                }

                // Transition UI to Verification Pending
                if (vPendingRecipientSub) {
                    vPendingRecipientSub.textContent = `Message dispatched to ${creatorName} (${handle}) on Instagram`;
                }

                const pendingSub = document.querySelector("#verification-pending-box .v-step-card:nth-child(2) .v-step-sub");
                if (pendingSub) {
                    pendingSub.textContent = `Waiting for ${creatorName} to confirm collaboration via the verification link in your Instagram message.`;
                }

                if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
                if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
                if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
                if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

                saveSessionState();
                showToast("✓ Message marked as sent! Polling for creator confirmation...");

                // Start verification polling
                startVerificationPolling();

            } catch (err) {
                showToast(err.message, "error");
            } finally {
                if (btnConfirmDmSent) {
                    btnConfirmDmSent.disabled = false;
                    btnConfirmDmSent.innerHTML = `<span>I've Sent the Message ✓</span>`;
                }
            }
        };
    }

    // Global listener for extension messages
    window.addEventListener("message", (event) => {
        if (!event.data || typeof event.data !== "object") return;
        const { type, success, username, reason, senderHandle } = event.data;

        if (type === "ARCLENT_INSTAGRAM_DM_READY") {
            if (senderHandle) {
                setSenderHandle(senderHandle, true);
            }
            showToast(`✓ Instagram DM ready for @${username || 'creator'}! Review and click Send in Instagram.`);
            if (verificationDmReadyBox && !verificationDmReadyBox.classList.contains("hidden")) {
                if (vDmReadySub) {
                    vDmReadySub.textContent = `Your message has been verified and added to @${username || 'creator'}'s Instagram composer.`;
                }
            }
        } else if (type === "ARCLENT_INSTAGRAM_DM_FAILED") {
            showToast(`Note: ${reason || 'We copied your message to the clipboard. Please paste into the box.'}`, "warning");
        } else if (type === "ARCLENT_EXTENSION_PONG" || type === "ARCLENT_INSTAGRAM_EXTENSION_READY") {
            updateExtensionStatusUI(true);
        }
    });

    // --------------------------------------------------------------------------
    // Copy & 4-Second Redirect Countdown Notification Engine (Mobile & Desktop)
    // --------------------------------------------------------------------------
    async function showCopyAndRedirectCountdown({ text, meta, clickedBtn, openAction }) {
        if (text) {
            await copyTextToClipboard(text);
        }

        const originalBtnHtml = clickedBtn ? clickedBtn.innerHTML : "";
        const isMobile = isMobileDevice();
        const pasteHint = isMobile ? "Just paste into the chat." : "Just paste (Ctrl+V) into the chat.";

        if (clickedBtn) {
            clickedBtn.disabled = true;
            clickedBtn.innerHTML = `<span>📋 Copied! Opening in 4s...</span>`;
        }

        if (btnIgCopyText) {
            btnIgCopyText.textContent = "✓ Copied!";
            setTimeout(() => { if (btnIgCopyText) btnIgCopyText.textContent = "📋 Copy Message"; }, 5000);
        }
        if (btnIgCopyDraft) {
            btnIgCopyDraft.textContent = "✓ Copied!";
            setTimeout(() => { if (btnIgCopyDraft) btnIgCopyDraft.textContent = "📋 Copy Text"; }, 5000);
        }
        if (copyInstaBtnText) {
            copyInstaBtnText.textContent = "✓ Message Copied!";
            setTimeout(() => { if (copyInstaBtnText) copyInstaBtnText.textContent = "📋 Copy Message"; }, 5000);
        }

        const overlay = document.getElementById("copy-redirect-overlay");
        const titleEl = document.getElementById("copy-redirect-title");
        const subEl = document.getElementById("copy-redirect-sub");
        const previewEl = document.getElementById("copy-redirect-preview");
        const timerEl = document.getElementById("copy-redirect-timer");

        if (titleEl) titleEl.textContent = "Message Copied to Clipboard!";
        if (timerEl) timerEl.textContent = "4";
        if (subEl) subEl.innerHTML = `Opening ${meta.name} in <strong id="copy-redirect-timer">4</strong>s... ${pasteHint}`;
        if (previewEl && text) {
            const previewClean = text.replace(/\s+/g, " ").trim();
            previewEl.textContent = previewClean.length > 90 ? `"${previewClean.substring(0, 90)}..."` : `"${previewClean}"`;
        }
        if (overlay) overlay.classList.add("active");

        // Tick second 1 (3 seconds remaining)
        await new Promise(r => setTimeout(r, 1000));
        const timer3 = document.getElementById("copy-redirect-timer");
        if (timer3) timer3.textContent = "3";
        if (clickedBtn) clickedBtn.innerHTML = `<span>📋 Copied! Opening in 3s...</span>`;
        if (subEl) subEl.innerHTML = `Opening ${meta.name} in <strong id="copy-redirect-timer">3</strong>s... ${pasteHint}`;

        // Tick second 2 (2 seconds remaining)
        await new Promise(r => setTimeout(r, 1000));
        const timer2 = document.getElementById("copy-redirect-timer");
        if (timer2) timer2.textContent = "2";
        if (clickedBtn) clickedBtn.innerHTML = `<span>📋 Copied! Opening in 2s...</span>`;
        if (subEl) subEl.innerHTML = `Opening ${meta.name} in <strong id="copy-redirect-timer">2</strong>s... ${pasteHint}`;

        // Tick second 3 (1 second remaining)
        await new Promise(r => setTimeout(r, 1000));
        const timer1 = document.getElementById("copy-redirect-timer");
        if (timer1) timer1.textContent = "1";
        if (clickedBtn) clickedBtn.innerHTML = `<span>📋 Copied! Opening in 1s...</span>`;
        if (subEl) subEl.innerHTML = `Opening ${meta.name} in <strong id="copy-redirect-timer">1</strong>s... ${pasteHint}`;

        // Tick second 4 (0s -> opening)
        await new Promise(r => setTimeout(r, 1000));
        if (clickedBtn) clickedBtn.innerHTML = `<span>🚀 Opening ${meta.name}...</span>`;
        if (subEl) subEl.innerHTML = `Opening ${meta.name} now...`;

        // Execute navigation
        if (typeof openAction === "function") {
            await openAction();
        }

        setTimeout(() => {
            if (overlay) overlay.classList.remove("active");
            if (clickedBtn) {
                clickedBtn.disabled = false;
                clickedBtn.innerHTML = originalBtnHtml || `<span>Open ${meta.name} & Send ↗</span>`;
            }
        }, 1500);
    }

    // --------------------------------------------------------------------------
    // Unified Social Outreach Dispatcher
    // --------------------------------------------------------------------------
    async function dispatchSocialOutreach(options = {}) {
        const active = options.profile || state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile || { platform: "Instagram" };
        const platformName = options.platform || active.platform || "Instagram";
        const meta = getSocialMediaMeta(platformName);
        const handle = formatHandle(options.handle || state.finalInstagramHandle || active.username || platformName);
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "your video";
        const role = state.userRole || "Video editor";
        const subject = `Collaboration confirmation for "${videoTitle}"`;

        let text = options.text;
        if (!text && igConfirmedMessageDraft && igConfirmedMessageDraft.value.trim()) {
            text = igConfirmedMessageDraft.value.trim();
        }
        if (!text && instaMessageBody && instaMessageBody.value.trim()) {
            text = instaMessageBody.value.trim();
        }
        if (!text) {
            text = generateSocialDmDraft(creatorName, videoTitle, role, meta.name);
        }

        const clickedBtn = options.button || 
            (btnIgOpenSend && !btnIgOpenSend.closest(".hidden") ? btnIgOpenSend : 
            (openInstagramBtn && !openInstagramBtn.closest(".hidden") ? openInstagramBtn : null));

        if (platformName.toLowerCase() === "discord") {
            const discUserId = options.handle && /^[0-9]{17,20}$/.test(options.handle.replace('@', ''))
                ? options.handle.replace('@', '')
                : (state.finalDiscordUserId || (state.discordProfile ? state.discordProfile.discord_user_id : null));

            if (discUserId) {
                state.finalDiscordUserId = discUserId;
                await sendDiscordOutreachMessage({
                    recipientId: discUserId,
                    message: text,
                    returnScreen: options.returnScreen
                });
                return;
            } else {
                state.stage = "outreach_hub";
                renderOutreachHub();
                showScreen("outreachHub", 4);
                if (hubDiscordBlock) {
                    hubDiscordBlock.classList.remove("hidden");
                    hubDiscordBlock.scrollIntoView({ behavior: "smooth" });
                }
                showToast("Discord found, but creator's Discord account could not be identified automatically. Enter their User ID to send.", "info");
                return;
            }
        }

        const isInstagram = platformName.toLowerCase().includes("instagram") || platformName.toLowerCase() === "ig";
        const isDesktop = !isMobileDevice();
        const extensionInstalled = isInstagram && isDesktop && (checkDirectDomPresence() || !!state.extensionInstalled);

        const targetHandleOrUrl = options.url || options.handle || active.url || active.username || handle;
        const dmUrl = getDirectMessageUrl(platformName, targetHandleOrUrl, text, subject);

        // Run countdown notification (or instant on mobile) before opening
        await showCopyAndRedirectCountdown({
            text: text,
            meta: meta,
            clickedBtn: clickedBtn,
            openAction: async () => {
                if (extensionInstalled) {
                    await dispatchInstagramWithExtension({
                        username: handle,
                        message: text,
                        sessionId: state.sessionId
                    });
                } else {
                    // Transition original tab to Confirmation Status
                    state.stageBeforeDelivery = options.returnScreen || (state.stage === "verify_instagram" ? "verify_instagram" : "outreach_hub");
                    state.stage = "sent";
                    state.selectedChannel = platformName.toLowerCase();
                    saveSessionState();

                    const isMob = isMobileDevice();
                    if (vDmReadySub) {
                        vDmReadySub.textContent = `Your draft message was copied to clipboard. Ready to paste and send in ${meta.name}.`;
                    }
                    if (vDmReadyGuideText) {
                        const pasteHint = isMob ? "Just paste your message and tap Send." : "Just paste (Ctrl+V) your message and click Send.";
                        const fallbackTarget = isMob ? "" : 'target="_blank" rel="noopener noreferrer"';
                        vDmReadyGuideText.innerHTML = `We opened ${escapeHtml(creatorName)}'s chat on ${meta.name}. ${pasteHint} <br><span style="font-size: 12px; color: var(--text-muted); margin-top: 4px; display: inline-block;">Didn't open? <a href="${dmUrl}" ${fallbackTarget} style="color: var(--primary); text-decoration: underline; font-weight: 700;">Tap here to open ${meta.name} ↗</a></span>`;
                    }

                    if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
                    if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
                    if (verificationDmReadyBox) verificationDmReadyBox.classList.remove("hidden");
                    if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
                    if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
                    if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

                    showScreen("deliverySuccess", 4);

                    // Notify backend of social outreach dispatch
                    if (state.sessionId) {
                        const senderIdentity = state.senderHandle ? `${state.senderHandle.replace(/^@+/, '')} on Arclent` : "Someone on Arclent";
                        fetch("/api/outreach/record-social-outreach", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                session_id: state.sessionId,
                                platform: platformName,
                                handle: handle,
                                sender_handle: state.senderHandle || null,
                                sender_identity: senderIdentity,
                                message: text
                            })
                        }).catch(() => {});
                    }

                    // Start live verification polling
                    startVerificationPolling();

                    // Open Instagram or destination platform
                    openPlatformUrl(dmUrl);
                }
            }
        });
    }

    // --------------------------------------------------------------------------
    // Helper: Update Creator Meta Card Inset
    // --------------------------------------------------------------------------
    function updateCreatorMetaCard(prefix) {
        const c = state.creator || {};
        const name = c.name || c.channel_name || "Creator";
        const roleStr = state.userRole || "Video editor";
        const videoTitle = c.video_title || "YouTube Video";

        const initialEl = document.getElementById(`${prefix}-creator-initial`);
        const avatarEl = document.getElementById(`${prefix}-creator-avatar`);
        const roleEl = document.getElementById(`${prefix}-step-creator-role`);
        const platformEl = document.getElementById(`${prefix}-step-creator-platform`);
        const subsEl = document.getElementById(`${prefix}-step-creator-subs`);

        if (roleEl) roleEl.textContent = `${roleStr} — ${name}`;
        if (platformEl) platformEl.textContent = `YouTube · "${videoTitle}"`;

        if (subsEl) {
            const rawSubs = (c.subscriber_count || "").trim();
            if (rawSubs && rawSubs.toLowerCase() !== "active creator" && rawSubs.toLowerCase() !== "none") {
                const cleanSubs = rawSubs.replace(/subscribers/i, "").trim();
                subsEl.textContent = `🔴 ${cleanSubs} subscribers`;
                subsEl.style.display = "inline-flex";
            } else if (rawSubs) {
                subsEl.textContent = `🔴 ${rawSubs}`;
                subsEl.style.display = "inline-flex";
            } else {
                subsEl.style.display = "none";
            }
        }

        const initialChar = name[0] ? name[0].toUpperCase() : "C";
        if (initialEl) initialEl.textContent = initialChar;

        if (c.profile_image && avatarEl) {
            avatarEl.src = c.profile_image;
            avatarEl.classList.remove("hidden");
            if (initialEl) initialEl.classList.add("hidden");
        } else {
            if (avatarEl) avatarEl.classList.add("hidden");
            if (initialEl) initialEl.classList.remove("hidden");
        }
    }

    // --------------------------------------------------------------------------
    // STEP 1: 1 · EMAIL VERIFICATION
    // --------------------------------------------------------------------------
    function renderVerifyEmailStep() {
        updateCreatorMetaCard("email");

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";

        if (state.discoveredEmail && state.discoveredEmail.email) {
            // Real email found
            if (emailFoundView) emailFoundView.classList.remove("hidden");
            if (emailFallbackView) emailFallbackView.classList.add("hidden");

            if (emailFoundCreatorName) emailFoundCreatorName.textContent = creatorName;
            if (emailFoundAddress) emailFoundAddress.textContent = state.discoveredEmail.email;
            if (emailFoundSourceTag) {
                emailFoundSourceTag.textContent = `Source: ${state.discoveredEmail.source || 'Publicly Published'}`;
            }
        } else {
            // No public email found -> go directly to fallback input
            showEmailFallback(true);
        }
    }

    function showEmailFallback(isInitialNotFound = false) {
        if (emailFoundView) emailFoundView.classList.add("hidden");
        if (emailFallbackView) emailFallbackView.classList.remove("hidden");

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";

        if (emailFallbackDesc) {
            emailFallbackDesc.textContent = isInitialNotFound
                ? `We couldn't find a public email for ${creatorName}. Add it yourself and we'll send the verification request.`
                : `Add the correct email for ${creatorName} and we'll send the verification request there instead.`;
        }

        if (emailManualEntryInput) {
            emailManualEntryInput.value = state.finalEmail || "";
            validateManualEmailInput();
        }

        if (btnEmailFallbackBack) {
            btnEmailFallbackBack.classList.remove("hidden");
            const span = btnEmailFallbackBack.querySelector("span");
            if (span) {
                span.textContent = (state.discoveredEmail && state.discoveredEmail.email)
                    ? "← Back to detected email"
                    : "← Back to Link input";
            }
        }

        // Render any alternative email candidates found
        if (emailCandidateChipsRow && emailCandidateChipsWrapper) {
            emailCandidateChipsRow.innerHTML = "";
            const validCandidates = (state.emailCandidates || []).filter(cand => cand.email && emailRegex.test(cand.email));
            
            if (validCandidates.length > 0) {
                emailCandidateChipsWrapper.classList.remove("hidden");
                validCandidates.forEach(cand => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "helper-chip-btn";
                    btn.innerHTML = `<span>✉</span><span>${escapeHtml(cand.email)}</span>`;
                    btn.onclick = () => {
                        if (emailManualEntryInput) {
                            emailManualEntryInput.value = cand.email;
                            validateManualEmailInput();
                        }
                    };
                    emailCandidateChipsRow.appendChild(btn);
                });
            } else {
                emailCandidateChipsWrapper.classList.add("hidden");
            }
        }
    }

    function validateManualEmailInput() {
        if (!emailManualEntryInput) return;
        const val = emailManualEntryInput.value.trim();
        const isValid = emailRegex.test(val);

        if (btnEmailManualSubmit) btnEmailManualSubmit.disabled = !isValid;

        if (emailManualEntryStatusIcon) {
            if (val.length === 0) {
                emailManualEntryStatusIcon.innerHTML = "";
            } else if (isValid) {
                emailManualEntryStatusIcon.innerHTML = `<span style="color: var(--green); font-weight: bold;">✓</span>`;
            } else {
                emailManualEntryStatusIcon.innerHTML = `<span style="color: #EF4444; font-weight: bold;">✕</span>`;
            }
        }

        if (emailManualEntryErrMsg) {
            if (val.length > 0 && !isValid) {
                emailManualEntryErrMsg.classList.remove("hidden");
            } else {
                emailManualEntryErrMsg.classList.add("hidden");
            }
        }
    }

    if (emailManualEntryInput) {
        emailManualEntryInput.addEventListener("input", validateManualEmailInput);
    }

    // --------------------------------------------------------------------------
    // Helper: Dispatch Email Verification & Transition to Delivery Screen
    // --------------------------------------------------------------------------
    async function dispatchEmailVerification(recipient) {
        if (!recipient) {
            showToast("No recipient email specified.", "error");
            return;
        }

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "your video";
        const subject = `Collaboration confirmation for "${videoTitle}"`;
        const body = generateConfirmationDraft(creatorName, videoTitle, state.userRole);

        state.isSending = true;
        state.finalEmail = recipient;
        state.emailConfirmed = true;

        try {
            // Confirm email on backend session
            if (state.sessionId) {
                await fetch("/api/outreach/confirm-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        email_confirmed: true,
                        user_role: state.userRole
                    })
                }).catch(() => {});
            }

            // Attempt sending email via Gmail API
            let sendSucceeded = false;
            let sendErrorMsg = null;

            if (state.sessionId) {
                const sendRes = await fetch("/api/outreach/send-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        recipient: recipient,
                        subject: subject,
                        body: body
                    })
                });

                if (sendRes.ok) {
                    sendSucceeded = true;
                } else {
                    const errData = await sendRes.json().catch(() => ({}));
                    sendErrorMsg = errData.detail || "Failed to send email via connected Gmail.";
                }
            }

            if (!sendSucceeded && !state.gmailConnected) {
                // If Gmail is not connected, inform user and open Hub
                showToast("Please connect Gmail to send verification emails directly.", "error");
                state.stage = "outreach_hub";
                renderOutreachHub();
                showScreen("outreachHub", 4);
                return;
            }

            if (!sendSucceeded) {
                throw new Error(sendErrorMsg || "Failed to dispatch email.");
            }

            // Successfully sent -> show delivery status screen
            if (vPendingRecipientSub) {
                vPendingRecipientSub.textContent = `Message delivered to ${creatorName} (${recipient}) via verified channel`;
            }

            if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
            if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
            if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
            if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
            if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

            state.stage = "sent";
            showScreen("deliverySuccess", 4);
            showToast("✓ Email inquiry sent with Yes / No verification options!");

            startVerificationPolling();

        } catch (err) {
            showToast(err.message, "error");
        } finally {
            state.isSending = false;
        }
    }

    // Step 1: "Yes, that's them" -> Confirm discovered email and send immediately
    if (btnEmailConfirmYes) {
        btnEmailConfirmYes.onclick = async () => {
            try {
                btnEmailConfirmYes.disabled = true;
                btnEmailConfirmYes.innerHTML = `<span>Sending Email...</span>`;
                const recipient = state.discoveredEmail ? state.discoveredEmail.email : state.finalEmail;
                await dispatchEmailVerification(recipient);
            } finally {
                if (btnEmailConfirmYes) {
                    btnEmailConfirmYes.disabled = false;
                    btnEmailConfirmYes.innerHTML = `<span>Yes, that's them</span>`;
                }
            }
        };
    }

    // Step 1: "No, not them" -> Show Fallback manual input
    if (btnEmailConfirmNo) {
        btnEmailConfirmNo.onclick = () => {
            showEmailFallback(false);
        };
    }

    // Step 1: Fallback Manual Submit -> Confirm custom email and send immediately
    if (emailManualEntryForm) {
        emailManualEntryForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const manualEmail = emailManualEntryInput ? emailManualEntryInput.value.trim() : "";
            if (!manualEmail || !emailRegex.test(manualEmail)) {
                showToast("Please enter a valid email address.", "error");
                return;
            }

            try {
                if (btnEmailManualSubmit) {
                    btnEmailManualSubmit.disabled = true;
                    btnEmailManualSubmit.innerHTML = `<span>Sending Email...</span>`;
                }
                await dispatchEmailVerification(manualEmail);
            } finally {
                if (btnEmailManualSubmit) {
                    btnEmailManualSubmit.disabled = false;
                    btnEmailManualSubmit.innerHTML = `<span>Send Email</span>`;
                }
            }
        });
    }

    // Step 1: "I don't have their email →" (Moves to Instagram Step 2)
    if (btnEmailSkipToIg) {
        btnEmailSkipToIg.onclick = async () => {
            state.finalEmail = null;
            state.emailConfirmed = false;

            if (state.sessionId) {
                await fetch("/api/outreach/confirm-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        email_confirmed: false,
                        user_role: state.userRole
                    })
                }).catch(() => {});
            }

            // Advance to Step 2 · INSTAGRAM
            state.stage = "verify_instagram";
            renderVerifyInstagramStep();
            showScreen("verifyInstagram", 3);
        };
    }

    // Step 1: Back to "Link your work"
    if (btnBackEmail) {
        btnBackEmail.onclick = (e) => {
            if (e) e.preventDefault();
            if (emailFallbackView && !emailFallbackView.classList.contains("hidden") && state.discoveredEmail && state.discoveredEmail.email) {
                if (emailFoundView) emailFoundView.classList.remove("hidden");
                if (emailFallbackView) emailFallbackView.classList.add("hidden");
                return;
            }
            state.stage = "input";
            showScreen("input", 1);
        };
    }

    if (igStepPillFromEmail) {
        igStepPillFromEmail.onclick = () => {
            state.stage = "verify_instagram";
            renderVerifyInstagramStep();
            showScreen("verifyInstagram", 3);
        };
    }

    // Step 1 Fallback: Back to detected email or Input
    if (btnEmailFallbackBack) {
        btnEmailFallbackBack.onclick = (e) => {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            if (state.discoveredEmail && state.discoveredEmail.email) {
                if (emailFoundView) emailFoundView.classList.remove("hidden");
                if (emailFallbackView) emailFallbackView.classList.add("hidden");
            } else {
                state.stage = "input";
                showScreen("input", 1);
            }
        };
    }

    // --------------------------------------------------------------------------
    // Helper: Filter Clean Social Profiles (Removes truncated URLs & sponsors)
    // --------------------------------------------------------------------------
    function filterCleanSocials(socials) {
        if (!socials || !Array.isArray(socials)) return [];
        const c = state.creator || {};
        const cName = (c.name || c.channel_name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
        const cHdl = (c.channel_handle || "").toLowerCase().replace(/[^a-z0-9]/g, "");
        const knownSponsors = new Set([
            "anthropic", "openai", "claude", "chatgpt", "gemini", "google", "microsoft", "apple",
            "nordvpn", "expressvpn", "surfshark", "squarespace", "wix", "shopify",
            "betterhelp", "audible", "skillshare", "grammarly", "honey", "cashapp",
            "patreon", "subscribestar", "buymeacoffee", "kofi", "amazon", "merch"
        ]);

        const platformUsers = {};
        socials.forEach(s => {
            const u = (s.username || "").toLowerCase().replace(/[^a-z0-9]/g, "");
            platformUsers[s.platform] = platformUsers[s.platform] || [];
            platformUsers[s.platform].push(u);
        });

        return socials.filter(s => {
            const raw = s.username || "";
            if (raw.includes("..") || raw.includes("...") || raw.includes("…") || raw.endsWith(".") || raw.endsWith("…")) {
                return false;
            }
            const clean = raw.toLowerCase().replace(/[^a-z0-9]/g, "");
            if (clean.length < 2) return false;

            // Reject prefix duplicate on same platform (e.g. siliconvall vs siliconvalleygirl)
            const others = platformUsers[s.platform] || [];
            if (others.some(otherU => otherU.length > clean.length && otherU.startsWith(clean))) {
                return false;
            }

            // Reject non-creator sponsor handles
            if (knownSponsors.has(clean) && clean !== cName && clean !== cHdl) {
                return false;
            }

            return true;
        });
    }

    // --------------------------------------------------------------------------
    // Helper: Dynamic Platform UI Updater for Step 2 & Confirmed View
    // --------------------------------------------------------------------------
    function updateStep2PlatformUI(profile) {
        const p = profile || state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile || { platform: "Instagram", username: "@creator" };
        const platformKey = p.platform || "Instagram";
        const meta = getSocialMediaMeta(platformKey);
        const handle = formatHandle(p.username || platformKey);
        const defaultBase = platformKey.toLowerCase() === "x" ? "https://x.com" : "https://instagram.com";
        const url = p.url || `${defaultBase}/${handle.replace('@', '')}`;

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";

        // 1. Top Navigation Step Pills
        if (igStepPill) {
            igStepPill.textContent = `2 · ${meta.name.toUpperCase()}`;
        }
        if (igStepPillFromEmail) {
            igStepPillFromEmail.textContent = `2 · ${meta.name.toUpperCase()}`;
        }

        // 2. Step 2 Main Detected View
        if (igStepHeading) {
            igStepHeading.textContent = `Confirm ${meta.name} Profile`;
        }
        if (igStepSubheading) {
            igStepSubheading.innerHTML = `We found a ${meta.name} profile for <strong id="ig-found-creator-name">${escapeHtml(creatorName)}</strong>.`;
        }
        if (igFoundCreatorName) {
            igFoundCreatorName.textContent = creatorName;
        }
        if (igDiscoveredIcon) {
            igDiscoveredIcon.style.background = meta.bgColor;
            igDiscoveredIcon.innerHTML = meta.icon;
            igDiscoveredIcon.title = meta.name;
        }
        if (igFoundHandle) {
            igFoundHandle.textContent = handle;
        }
        if (igFoundLink) {
            igFoundLink.href = url;
            igFoundLink.innerHTML = `<span>Open Profile</span><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`;
            igFoundLink.onclick = async (e) => {
                if (e) e.preventDefault();
                const draftText = (igConfirmedMessageDraft && !igConfirmedMessageDraft.closest(".hidden") ? igConfirmedMessageDraft.value.trim() : "") ||
                                  (instaMessageBody && !instaMessageBody.closest(".hidden") ? instaMessageBody.value.trim() : "") ||
                                  generateSocialDmDraft(creatorName, c.video_title || "your video", state.userRole || "Video editor", meta.name);
                
                await showCopyAndRedirectCountdown({
                    text: draftText,
                    meta: meta,
                    clickedBtn: igFoundLink,
                    openAction: () => {
                        openPlatformUrl(url);
                    }
                });
            };
        }

        // 3. Step 2 Fallback View
        if (igFallbackHeading) {
            igFallbackHeading.textContent = `Enter the correct ${meta.name} profile`;
        }
        if (igFallbackDesc) {
            igFallbackDesc.textContent = `Enter their ${meta.name} handle or profile URL to continue.`;
        }
        if (igManualEntryInput) {
            igManualEntryInput.placeholder = `@handle or ${meta.name.toLowerCase()}.com/handle`;
        }

        // 4. Step 2 Confirmed View
        if (igConfirmedStatusBadge) {
            igConfirmedStatusBadge.innerHTML = `<span class="dot"></span>${meta.name.toUpperCase()} PROFILE CONFIRMED`;
        }
        if (igConfirmedHeading) {
            igConfirmedHeading.textContent = `${meta.name} profile confirmed`;
        }
        if (igConfirmedSubheading) {
            igConfirmedSubheading.innerHTML = `Ready to contact <strong id="ig-confirmed-creator-name">${escapeHtml(creatorName)}</strong> on ${meta.name}.`;
        }
        if (igConfirmedIcon) {
            igConfirmedIcon.style.background = meta.bgColor;
            igConfirmedIcon.innerHTML = meta.icon;
            igConfirmedIcon.title = meta.name;
        }
        if (btnIgOpenSend) {
            btnIgOpenSend.innerHTML = `<span>Open ${meta.name} & Send ↗</span>`;
        }
    }

    // --------------------------------------------------------------------------
    // STEP 2: 2 · SOCIAL / INSTAGRAM VERIFICATION
    // --------------------------------------------------------------------------
    function renderDiscoveredOtherSocials() {
        if (!igOtherSocialsList) return;
        igOtherSocialsList.innerHTML = "";

        const allSocials = filterCleanSocials(state.socialProfiles || []);
        const activeProfile = state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile;
        const activePlatform = (activeProfile ? activeProfile.platform : "Instagram").toLowerCase();
        const activeHandle = (state.finalInstagramHandle || (activeProfile ? formatHandle(activeProfile.username) : "")).toLowerCase();
        
        if (igOtherSocialsCount) {
            igOtherSocialsCount.textContent = allSocials.length;
        }

        if (allSocials.length === 0) {
            igOtherSocialsList.innerHTML = `<div class="other-socials-empty">No additional social media profiles found in channel metadata.</div>`;
            return;
        }

        allSocials.forEach(s => {
            const meta = getSocialMediaMeta(s.platform);
            const formatted = formatHandle(s.username || s.platform);
            const sPlatform = (s.platform || "").toLowerCase();
            
            // Mark selected if matching active social profile
            let isSelected = false;
            if (state.selectedSocialProfile) {
                isSelected = (s === state.selectedSocialProfile) || 
                             (s.url && state.selectedSocialProfile.url && s.url === state.selectedSocialProfile.url) ||
                             (sPlatform === (state.selectedSocialProfile.platform || "").toLowerCase() && formatted.toLowerCase() === formatHandle(state.selectedSocialProfile.username || state.selectedSocialProfile.platform).toLowerCase());
            } else {
                isSelected = (sPlatform === activePlatform) && (formatted.toLowerCase() === activeHandle);
            }
            
            const item = document.createElement("div");
            item.className = "other-social-item font-mono";
            item.innerHTML = `
                <div class="other-social-left">
                    <div class="other-social-icon" style="background: ${meta.bgColor};">
                        ${meta.icon}
                    </div>
                    <div class="other-social-meta">
                        <span class="other-social-platform-name">${escapeHtml(meta.name)}</span>
                        <span class="other-social-handle" title="${escapeHtml(formatted)}">${escapeHtml(formatted)}</span>
                    </div>
                </div>
                <div class="other-social-actions">
                    <button type="button" class="other-social-open-dm-btn other-social-open-link" style="background: var(--bg-cream); border: 1.5px solid var(--black); font-weight: 700; cursor: pointer;" title="Send DM on ${escapeHtml(meta.name)}">Send DM ↗</button>
                    <button type="button" class="other-social-select-btn ${isSelected ? 'active-selected' : ''}" title="Use this handle for outreach">
                        ${isSelected ? '✓ Selected' : 'Select'}
                    </button>
                </div>
            `;

            const dmBtn = item.querySelector(".other-social-open-dm-btn");
            if (dmBtn) {
                dmBtn.onclick = (e) => {
                    e.stopPropagation();
                    dispatchSocialOutreach({
                        profile: s,
                        platform: s.platform,
                        handle: s.username || s.platform,
                        url: s.url,
                        button: dmBtn,
                        returnScreen: "verify_instagram"
                    });
                };
            }

            const selectBtn = item.querySelector(".other-social-select-btn");
            if (selectBtn) {
                selectBtn.onclick = (e) => {
                    e.stopPropagation();
                    selectActiveSocialProfile(s);
                };
            }

            igOtherSocialsList.appendChild(item);
        });
    }

    function selectActiveSocialProfile(social) {
        if (!social) return;
        state.selectedSocialProfile = social;
        state.activeSocialProfile = social;
        const meta = getSocialMediaMeta(social.platform);
        const cleanHandle = formatHandle(social.username || social.platform);
        const defaultBase = (social.platform || "").toLowerCase() === "x" ? "https://x.com" : "https://instagram.com";
        const url = social.url || `${defaultBase}/${cleanHandle.replace('@', '')}`;

        state.instagramProfile = {
            platform: social.platform || "Instagram",
            username: cleanHandle,
            url: url
        };
        state.finalInstagramHandle = cleanHandle;
        state.finalInstagramUrl = url;

        updateStep2PlatformUI(social);

        if (igManualEntryInput) {
            igManualEntryInput.value = cleanHandle;
            validateManualIgInput();
        }

        if (igDiscoveredCard) {
            igDiscoveredCard.classList.remove("highlight-pulse");
            void igDiscoveredCard.offsetWidth;
            igDiscoveredCard.classList.add("highlight-pulse");
        }

        renderDiscoveredOtherSocials();
        showToast(`✓ Switched to ${meta.name} (${cleanHandle})`);
    }

    // Toggle button for other social media profiles
    if (btnToggleOtherSocials) {
        btnToggleOtherSocials.onclick = () => {
            const isExpanded = btnToggleOtherSocials.getAttribute("aria-expanded") === "true";
            const nextState = !isExpanded;
            btnToggleOtherSocials.setAttribute("aria-expanded", String(nextState));
            if (igOtherSocialsSection) {
                igOtherSocialsSection.classList.toggle("open", nextState);
            }
            if (igOtherSocialsContent) {
                igOtherSocialsContent.classList.toggle("hidden", !nextState);
            }
        };
    }

    function renderVerifyInstagramStep() {
        updateCreatorMetaCard("ig");

        // Set default active social profile if not set yet
        if (!state.activeSocialProfile && state.instagramProfile) {
            state.activeSocialProfile = state.instagramProfile;
        }

        const active = state.activeSocialProfile || state.instagramProfile;

        if (active && active.username) {
            if (igFoundView) igFoundView.classList.remove("hidden");
            if (igFallbackView) igFallbackView.classList.add("hidden");
            if (igConfirmedView) igConfirmedView.classList.add("hidden");

            const handle = formatHandle(active.username);
            state.finalInstagramHandle = handle;
            const defaultBase = (active.platform || "").toLowerCase() === "x" ? "https://x.com" : "https://instagram.com";
            state.finalInstagramUrl = active.url || `${defaultBase}/${handle.replace("@", "")}`;

            updateStep2PlatformUI(active);
        } else {
            showInstagramFallback(true);
        }

        renderDiscoveredOtherSocials();
    }

    function showInstagramFallback(isInitialNotFound = false) {
        if (igFoundView) igFoundView.classList.add("hidden");
        if (igFallbackView) igFallbackView.classList.remove("hidden");
        if (igConfirmedView) igConfirmedView.classList.add("hidden");

        const active = state.activeSocialProfile || state.instagramProfile || { platform: "Instagram" };
        const meta = getSocialMediaMeta(active.platform);
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";

        if (igFallbackHeading) {
            igFallbackHeading.textContent = `Enter the correct ${meta.name} profile`;
        }

        if (igFallbackDesc) {
            igFallbackDesc.textContent = isInitialNotFound
                ? `We couldn't locate a verified ${meta.name} profile on ${creatorName}'s channel. Enter their handle or link to continue.`
                : `Enter their ${meta.name} handle or profile URL to continue.`;
        }

        if (igManualEntryInput) {
            igManualEntryInput.placeholder = `@handle or ${meta.name.toLowerCase()}.com/handle`;
            igManualEntryInput.value = state.finalInstagramHandle || "";
            validateManualIgInput();
        }

        // Render other discovered social platforms as suggestions
        if (igSocialChipsRow && igSocialChipsWrapper) {
            igSocialChipsRow.innerHTML = "";
            const otherSocials = (state.socialProfiles || []).filter(s => s.platform && (s.platform || "").toLowerCase() !== (active.platform || "").toLowerCase());

            if (otherSocials.length > 0) {
                igSocialChipsWrapper.classList.remove("hidden");
                otherSocials.forEach(s => {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "helper-chip-btn";
                    btn.innerHTML = `<span>🔗</span><span>${escapeHtml(s.platform)}: ${escapeHtml(s.username || s.platform)}</span>`;
                    btn.onclick = () => {
                        selectActiveSocialProfile(s);
                    };
                    igSocialChipsRow.appendChild(btn);
                });
            } else {
                igSocialChipsWrapper.classList.add("hidden");
            }
        }
    }

    function showInstagramConfirmed(handle, url) {
        if (igFoundView) igFoundView.classList.add("hidden");
        if (igFallbackView) igFallbackView.classList.add("hidden");
        if (igConfirmedView) igConfirmedView.classList.remove("hidden");

        const active = state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile || { platform: "Instagram", username: handle, url: url };
        const meta = getSocialMediaMeta(active.platform || "Instagram");
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "your video";

        state.finalInstagramHandle = handle;
        state.finalInstagramUrl = url || active.url || `https://instagram.com/${handle.replace('@', '')}`;

        updateStep2PlatformUI(active);

        if (igConfirmedCreatorName) igConfirmedCreatorName.textContent = creatorName;
        if (igConfirmedHandle) igConfirmedHandle.textContent = handle;

        const draftMsg = generateInstagramDmDraft(creatorName, videoTitle, state.userRole);
        if (igConfirmedMessageDraft) {
            igConfirmedMessageDraft.value = draftMsg;
        }

        // Render other discovered profiles below the action buttons
        renderConfirmedOtherProfiles();
    }

    function renderConfirmedOtherProfiles() {
        if (!igConfirmedOtherSocialsList) return;
        igConfirmedOtherSocialsList.innerHTML = "";

        const allSocials = filterCleanSocials(state.socialProfiles || []);
        const active = state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile || { platform: "Instagram" };
        const activePlatform = (active.platform || "Instagram").toLowerCase();
        const currentCleanHandle = (state.finalInstagramHandle || (active ? active.username : "") || "").toLowerCase().replace('@', '');

        const itemsToDisplay = [];

        // 1. Add discovered email if available
        if (state.discoveredEmail && state.discoveredEmail.email) {
            itemsToDisplay.push({
                platform: "Email",
                name: "Email Contact",
                username: state.discoveredEmail.email,
                url: `mailto:${state.discoveredEmail.email}`
            });
        }

        // 2. Add all other social accounts except the currently active profile
        allSocials.forEach(s => {
            const sUser = (s.username || s.platform || "").toLowerCase().replace('@', '');
            const sPlatform = (s.platform || "").toLowerCase();
            const isCurrentActive = sPlatform === activePlatform && sUser === currentCleanHandle;
            
            if (!isCurrentActive) {
                const meta = getSocialMediaMeta(s.platform);
                itemsToDisplay.push({
                    platform: s.platform,
                    name: meta.name,
                    username: formatHandle(s.username || s.platform),
                    url: s.url,
                    meta: meta,
                    raw: s
                });
            }
        });

        if (igConfirmedOtherCount) {
            igConfirmedOtherCount.textContent = `${itemsToDisplay.length}`;
        }

        if (itemsToDisplay.length === 0) {
            igConfirmedOtherSocialsList.innerHTML = `<div class="other-socials-empty font-mono" style="padding: 10px; font-size: 12px; color: var(--slate); background: #F4EFE6; border: 1px dashed var(--slate);">No additional public profiles discovered.</div>`;
            return;
        }

        itemsToDisplay.forEach(item => {
            const meta = item.meta || getSocialMediaMeta(item.platform);
            const row = document.createElement("div");
            row.className = "other-social-item font-mono";
            row.style.marginBottom = "8px";
            row.innerHTML = `
                <div class="other-social-left">
                    <div class="other-social-icon" style="background: ${meta.bgColor};">
                        ${meta.icon}
                    </div>
                    <div class="other-social-meta">
                        <span class="other-social-platform-name">${escapeHtml(item.name)}</span>
                        <span class="other-social-handle" title="${escapeHtml(item.username)}">${escapeHtml(item.username)}</span>
                    </div>
                </div>
                <div class="other-social-actions">
                    <button type="button" class="other-social-open-dm-btn other-social-open-link" style="padding: 5px 12px; font-size: 11px; background: var(--bg-cream); border: 1.5px solid var(--black); font-weight: 700; cursor: pointer;">Send DM ↗</button>
                    ${item.raw ? `<button type="button" class="other-social-select-btn" style="padding: 4px 10px; font-size: 11px;">Switch to this</button>` : ''}
                </div>
            `;

            const dmBtn = row.querySelector(".other-social-open-dm-btn");
            if (dmBtn) {
                dmBtn.onclick = (e) => {
                    e.stopPropagation();
                    if (item.platform === "Email") {
                        state.stage = "outreach_hub";
                        renderOutreachHub();
                        showScreen("outreachHub", 4);
                    } else {
                        dispatchSocialOutreach({
                            profile: item.raw || item,
                            platform: item.platform,
                            handle: item.username,
                            url: item.url,
                            returnScreen: "verify_instagram"
                        });
                    }
                };
            }

            const selectBtn = row.querySelector(".other-social-select-btn");
            if (selectBtn && item.raw) {
                selectBtn.onclick = (e) => {
                    e.stopPropagation();
                    selectActiveSocialProfile(item.raw);
                    showInstagramConfirmed(formatHandle(item.raw.username), item.raw.url);
                };
            }

            igConfirmedOtherSocialsList.appendChild(row);
        });
    }

    function validateManualIgInput() {
        if (!igManualEntryInput) return;
        const val = igManualEntryInput.value.trim();
        const isValid = val.length > 1;
        if (btnIgManualSubmit) btnIgManualSubmit.disabled = !isValid;
    }

    if (igManualEntryInput) {
        igManualEntryInput.addEventListener("input", validateManualIgInput);
    }

    // Step 2: "Yes, that's them" -> Confirm discovered social profile & reveal confirmed action
    if (btnIgConfirmYes) {
        btnIgConfirmYes.onclick = async () => {
            try {
                btnIgConfirmYes.disabled = true;
                state.instagramConfirmed = true;
                const active = state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile;
                const handle = active ? formatHandle(active.username) : "@creator";
                const meta = getSocialMediaMeta(active ? active.platform : "Instagram");
                const defaultBase = (active && (active.platform || "").toLowerCase() === "x") ? "https://x.com" : "https://instagram.com";
                const url = active ? (active.url || `${defaultBase}/${handle.replace('@', '')}`) : `${defaultBase}/${handle.replace('@', '')}`;

                state.finalInstagramHandle = handle;
                state.finalInstagramUrl = url;

                if (state.sessionId) {
                    await fetch("/api/outreach/confirm-instagram", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            session_id: state.sessionId,
                            instagram_confirmed: true,
                            user_role: state.userRole,
                            platform: active ? active.platform : "Instagram"
                        })
                    }).catch(() => {});
                }

                showInstagramConfirmed(handle, url);
                showToast(`✓ ${meta.name} profile confirmed`);
            } finally {
                btnIgConfirmYes.disabled = false;
            }
        };
    }

    // Step 2: "No, not them"
    if (btnIgConfirmNo) {
        btnIgConfirmNo.onclick = () => {
            showInstagramFallback(false);
        };
    }

    // Step 2: Fallback Manual Submit -> Reveal confirmed action
    if (igManualEntryForm) {
        igManualEntryForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const handle = igManualEntryInput ? igManualEntryInput.value.trim() : "";
            if (!handle || handle.length < 2) {
                showToast("Please enter a handle or profile URL.", "error");
                return;
            }

            try {
                if (btnIgManualSubmit) btnIgManualSubmit.disabled = true;
                const active = state.activeSocialProfile || state.selectedSocialProfile || state.instagramProfile || { platform: "Instagram" };
                const meta = getSocialMediaMeta(active.platform);
                const formatted = formatHandle(handle);
                const defaultBase = (active.platform || "").toLowerCase() === "x" ? "https://x.com" : "https://instagram.com";
                const url = `${defaultBase}/${formatted.replace('@', '')}`;
                
                state.finalInstagramHandle = formatted;
                state.finalInstagramUrl = url;
                state.instagramConfirmed = true;

                if (state.sessionId) {
                    await fetch("/api/outreach/manual-instagram", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            session_id: state.sessionId,
                            handle: formatted,
                            user_role: state.userRole,
                            platform: active.platform
                        })
                    }).catch(() => {});
                }

                showInstagramConfirmed(formatted, url);
                showToast(`✓ ${meta.name} profile confirmed`);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                if (btnIgManualSubmit) btnIgManualSubmit.disabled = false;
            }
        });
    }

    // Actions on Confirmed View: Copy Message Handler
    async function handleCopyConfirmedDraft() {
        const text = igConfirmedMessageDraft ? igConfirmedMessageDraft.value.trim() : "";
        if (!text) return;
        await copyTextToClipboard(text);
        if (btnIgCopyText) btnIgCopyText.textContent = "✓ Copied!";
        if (btnIgCopyDraft) btnIgCopyDraft.textContent = "✓ Copied!";
        setTimeout(() => {
            if (btnIgCopyText) btnIgCopyText.textContent = "📋 Copy Message";
            if (btnIgCopyDraft) btnIgCopyDraft.textContent = "📋 Copy Text";
        }, 2500);
        showToast("✓ Message copied to clipboard!");
    }

    if (btnIgCopyDraftMain) {
        btnIgCopyDraftMain.onclick = handleCopyConfirmedDraft;
    }
    if (btnIgCopyDraft) {
        btnIgCopyDraft.onclick = handleCopyConfirmedDraft;
    }

    if (btnIgOpenSend) {
        btnIgOpenSend.onclick = () => {
            dispatchSocialOutreach({ returnScreen: "verify_instagram", button: btnIgOpenSend });
        };
    }

    // Step 2 Back navigation to Step 1 or Previous Sub-view
    if (btnBackIg) {
        btnBackIg.onclick = () => {
            // If on confirmed view, return to Step 2 detected selection view
            if (igConfirmedView && !igConfirmedView.classList.contains("hidden")) {
                if (igFoundView) igFoundView.classList.remove("hidden");
                if (igConfirmedView) igConfirmedView.classList.add("hidden");
                if (igFallbackView) igFallbackView.classList.add("hidden");
                renderDiscoveredOtherSocials();
                return;
            }
            // If on fallback view and we have a discovered profile, return to detected view
            if (igFallbackView && !igFallbackView.classList.contains("hidden") && state.instagramProfile && state.instagramProfile.username) {
                if (igFoundView) igFoundView.classList.remove("hidden");
                if (igFallbackView) igFallbackView.classList.add("hidden");
                if (igConfirmedView) igConfirmedView.classList.add("hidden");
                renderDiscoveredOtherSocials();
                return;
            }
            // Otherwise go back to Step 1 (Email)
            state.stage = "verify_email";
            renderVerifyEmailStep();
            showScreen("verifyEmail", 3);
        };
    }

    if (emailStepPillFromIg) {
        emailStepPillFromIg.onclick = () => {
            state.stage = "verify_email";
            renderVerifyEmailStep();
            showScreen("verifyEmail", 3);
        };
    }

    if (btnIgFallbackBack) {
        btnIgFallbackBack.onclick = () => {
            if (state.instagramProfile && state.instagramProfile.username) {
                if (igFoundView) igFoundView.classList.remove("hidden");
                if (igFallbackView) igFallbackView.classList.add("hidden");
                if (igConfirmedView) igConfirmedView.classList.add("hidden");
                renderDiscoveredOtherSocials();
            } else {
                state.stage = "verify_email";
                renderVerifyEmailStep();
                showScreen("verifyEmail", 3);
            }
        };
    }

    if (btnIgToHub) {
        btnIgToHub.onclick = () => {
            state.stage = "outreach_hub";
            renderOutreachHub();
            showScreen("outreachHub", 4);
        };
    }

    // --------------------------------------------------------------------------
    // STEP 3: OUTREACH & DISPATCH HUB
    // --------------------------------------------------------------------------
    function renderOutreachHub() {
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "your video";

        if (hubCreatorHeading) hubCreatorHeading.textContent = `Reaching out to ${creatorName}`;

        if (hubCreatorSubs) {
            const rawSubs = (c.subscriber_count || "").trim();
            if (rawSubs && rawSubs.toLowerCase() !== "active creator" && rawSubs.toLowerCase() !== "none") {
                const cleanSubs = rawSubs.replace(/subscribers/i, "").trim();
                hubCreatorSubs.textContent = `🔴 ${cleanSubs} subscribers`;
                hubCreatorSubs.style.display = "inline-flex";
            } else if (rawSubs) {
                hubCreatorSubs.textContent = `🔴 ${rawSubs}`;
                hubCreatorSubs.style.display = "inline-flex";
            } else {
                hubCreatorSubs.style.display = "none";
            }
        }

        // Update summary items
        if (hubSummaryEmailVal) {
            hubSummaryEmailVal.textContent = state.finalEmail || "Not provided (Skipped)";
            hubSummaryEmailVal.style.color = state.finalEmail ? "var(--green)" : "var(--text-muted)";
        }
        if (hubSummaryIgVal) {
            hubSummaryIgVal.textContent = state.finalInstagramHandle || "Not provided (Skipped)";
            hubSummaryIgVal.style.color = state.finalInstagramHandle ? "var(--green)" : "var(--text-muted)";
        }

        // 1. Email Section
        if (state.finalEmail) {
            if (hubEmailBlock) hubEmailBlock.classList.remove("hidden");
            if (workflowEmailRecipient) workflowEmailRecipient.value = state.finalEmail;
            if (composerRecipientSourceTag) {
                composerRecipientSourceTag.textContent = state.emailConfirmed ? "Verified Contact" : "User Provided";
            }
            if (workflowEmailSubject) {
                workflowEmailSubject.value = `Collaboration confirmation for "${videoTitle}"`;
            }
            if (workflowEmailBody) {
                workflowEmailBody.value = generateConfirmationDraft(creatorName, videoTitle, state.userRole);
            }
            validateSendButton();
        } else {
            if (hubEmailBlock) hubEmailBlock.classList.add("hidden");
        }

        // 2. Instagram Section
        if (state.finalInstagramHandle) {
            if (hubInstagramBlock) hubInstagramBlock.classList.remove("hidden");
            if (hubDmHeadHandle) hubDmHeadHandle.textContent = `Direct message to ${state.finalInstagramHandle}`;
            if (instaMessageBody) {
                instaMessageBody.value = generateInstagramDmDraft(creatorName, videoTitle, state.userRole);
            }
        } else {
            if (hubInstagramBlock) hubInstagramBlock.classList.add("hidden");
        }

        // 3. Discord Bot Section
        const disc = state.discordProfile || (state.socialProfiles || []).find(s => (s.platform || "").toLowerCase() === "discord");
        if (disc || state.finalDiscordUserId) {
            if (hubSummaryDiscordRow) hubSummaryDiscordRow.classList.remove("hidden");
            if (hubDiscordBlock) hubDiscordBlock.classList.remove("hidden");

            const discUserId = state.finalDiscordUserId || (disc ? (disc.discord_user_id || (/^[0-9]{17,20}$/.test(disc.username || '') ? disc.username : null)) : null);
            const isSendable = !!discUserId;

            if (hubSummaryDiscordVal) {
                if (discUserId) {
                    hubSummaryDiscordVal.textContent = `User ID: ${discUserId}`;
                    hubSummaryDiscordVal.style.color = "var(--green)";
                } else if (disc && (disc.discord_username || disc.username)) {
                    hubSummaryDiscordVal.textContent = `Handle: ${disc.discord_username || disc.username}`;
                    hubSummaryDiscordVal.style.color = "var(--text-main)";
                } else if (disc && (disc.discord_invite || disc.url)) {
                    hubSummaryDiscordVal.textContent = `Invite: ${disc.discord_invite || disc.url}`;
                    hubSummaryDiscordVal.style.color = "var(--text-main)";
                } else {
                    hubSummaryDiscordVal.textContent = "Discovered";
                    hubSummaryDiscordVal.style.color = "var(--text-muted)";
                }
            }

            if (discordMessageBody) {
                const currentVal = discordMessageBody.value ? discordMessageBody.value.trim() : "";
                if (!currentVal || !currentVal.includes("/verify")) {
                    discordMessageBody.value = generateDiscordDmDraft(creatorName, videoTitle, state.userRole);
                }
            }

            if (isSendable) {
                state.finalDiscordUserId = discUserId;
                if (discordStatusBadge) {
                    discordStatusBadge.textContent = "SENDABLE · BOT READY";
                    discordStatusBadge.style.background = "#DCFCE7";
                    discordStatusBadge.style.color = "#166534";
                    discordStatusBadge.style.borderColor = "#22C55E";
                }
                if (discordIdentificationBanner) discordIdentificationBanner.classList.add("hidden");
                if (btnSendDiscordBot) btnSendDiscordBot.disabled = false;
                if (hubDiscordHeadHandle) hubDiscordHeadHandle.textContent = `Direct message to Discord User ID ${discUserId}`;
            } else {
                if (discordStatusBadge) {
                    discordStatusBadge.textContent = "DISCOVERED · ID REQUIRED";
                    discordStatusBadge.style.background = "#FEF3C7";
                    discordStatusBadge.style.color = "#92400E";
                    discordStatusBadge.style.borderColor = "#F59E0B";
                }
                if (discordIdentificationBanner) {
                    discordIdentificationBanner.classList.remove("hidden");
                    const targetStr = (disc && (disc.discord_invite || disc.discord_username || disc.url || disc.username)) || "Server invite / public mention";
                    if (discordDiscoveredTarget) discordDiscoveredTarget.textContent = targetStr;
                }
                if (btnSendDiscordBot) btnSendDiscordBot.disabled = !state.finalDiscordUserId;
                if (hubDiscordHeadHandle) hubDiscordHeadHandle.textContent = "Direct message from Arclent Bot";
            }
        } else {
            if (hubSummaryDiscordRow) hubSummaryDiscordRow.classList.add("hidden");
            if (hubDiscordBlock) hubDiscordBlock.classList.add("hidden");
        }

        // 3. Other Socials Grid (Displays all other channels including other Instagram profiles)
        const currentIg = (state.finalInstagramHandle || "").toLowerCase().replace('@', '');
        const otherSocials = (state.socialProfiles || []).filter(s => {
            const isCurrentIg = (s.platform || "").toLowerCase() === "instagram" && (s.username || "").toLowerCase().replace('@', '') === currentIg;
            return !isCurrentIg;
        });

        if (hubOtherSocialsBlock && hubSocialsGrid) {
            if (otherSocials.length > 0) {
                hubOtherSocialsBlock.classList.remove("hidden");
                hubSocialsGrid.innerHTML = "";
                otherSocials.forEach(s => {
                    const meta = getSocialMediaMeta(s.platform);
                    const card = document.createElement("div");
                    card.className = "social-card font-mono";
                    card.innerHTML = `
                        <div class="social-card-left">
                            <div class="social-icon-wrapper" style="background: ${meta.bgColor};">
                                ${meta.icon}
                            </div>
                            <div class="social-info">
                                <span class="social-platform-title">${escapeHtml(meta.name)}</span>
                                <span class="social-handle-text">${escapeHtml(s.username || s.platform)}</span>
                            </div>
                        </div>
                        <button type="button" class="btn-secondary hub-social-send-btn" style="padding: 5px 12px; font-size: 11.5px; white-space: nowrap; flex: 0; cursor: pointer;">
                            <span>Send DM ↗</span>
                        </button>
                    `;
                    const sendBtn = card.querySelector(".hub-social-send-btn");
                    if (sendBtn) {
                        sendBtn.onclick = (e) => {
                            e.preventDefault();
                            dispatchSocialOutreach({
                                profile: s,
                                platform: s.platform,
                                handle: s.username,
                                url: s.url,
                                button: sendBtn,
                                returnScreen: "outreach_hub"
                            });
                        };
                    }
                    hubSocialsGrid.appendChild(card);
                });
            } else {
                hubOtherSocialsBlock.classList.add("hidden");
            }
        }
    }

    // Jump back to edit email or IG from Outreach Hub
    if (hubEditEmailBtn) {
        hubEditEmailBtn.onclick = () => {
            state.stage = "verify_email";
            renderVerifyEmailStep();
            showScreen("verifyEmail", 3);
        };
    }

    if (hubEditIgBtn) {
        hubEditIgBtn.onclick = () => {
            state.stage = "verify_instagram";
            renderVerifyInstagramStep();
            showScreen("verifyInstagram", 3);
        };
    }

    // Back from Outreach Hub to Step 2 · Instagram
    if (btnBackHub) {
        btnBackHub.onclick = () => {
            state.stage = "verify_instagram";
            renderVerifyInstagramStep();
            showScreen("verifyInstagram", 3);
        };
    }

    // Back from Delivery screen to Outreach Hub or Step 2
    if (btnBackDelivery) {
        btnBackDelivery.onclick = () => {
            if (state.stageBeforeDelivery === "verify_instagram") {
                state.stage = "verify_instagram";
                renderVerifyInstagramStep();
                showScreen("verifyInstagram", 3);
            } else {
                state.stage = "outreach_hub";
                renderOutreachHub();
                showScreen("outreachHub", 4);
            }
        };
    }

    // Email Send Validation
    function validateSendButton() {
        if (!workflowSendEmailBtn) return;
        const recipientVal = workflowEmailRecipient ? workflowEmailRecipient.value.trim() : (state.finalEmail || "");
        const validRecipient = !!recipientVal && emailRegex.test(recipientVal);
        const canSend = state.gmailConnected && validRecipient && !state.isSending;
        workflowSendEmailBtn.disabled = !canSend;
    }

    if (workflowEmailRecipient) {
        workflowEmailRecipient.addEventListener("input", () => {
            state.finalEmail = workflowEmailRecipient.value.trim();
            validateSendButton();
        });
    }

    if (regenerateEmailBtn) {
        regenerateEmailBtn.onclick = () => {
            const c = state.creator || {};
            const creatorName = c.name || c.channel_name || "Creator";
            const videoTitle = c.video_title || "your video";
            if (workflowEmailSubject) workflowEmailSubject.value = `Collaboration confirmation for "${videoTitle}"`;
            if (workflowEmailBody) workflowEmailBody.value = generateConfirmationDraft(creatorName, videoTitle, state.userRole);
            showToast("✓ Draft reset to standard confirmation template");
        };
    }

    // Instagram Actions
    if (copyInstaMsgBtn) {
        copyInstaMsgBtn.onclick = async () => {
            const text = instaMessageBody ? instaMessageBody.value.trim() : "";
            if (!text) return;
            await copyTextToClipboard(text);
            if (copyInstaBtnText) {
                copyInstaBtnText.textContent = "✓ Message Copied!";
                setTimeout(() => { if (copyInstaBtnText) copyInstaBtnText.textContent = "📋 Copy Message"; }, 2500);
            }
            showToast("✓ Message copied to clipboard!");
        };
    }

    if (openInstagramBtn) {
        openInstagramBtn.onclick = () => {
            dispatchSocialOutreach({ returnScreen: "outreach_hub", button: openInstagramBtn });
        };
    }

    // Helper: Discord Draft and Dispatch Handlers
    function generateDiscordDmDraft(creatorName, videoTitle, userRole) {
        const cName = creatorName || "Creator";
        const vTitle = videoTitle || "your video";
        const role = (userRole || state.userRole || "Video editor").trim();
        const verifyUrl = getVerificationLink();
        return `Hi ${cName}, your collaborator (${role}) on "${vTitle}" here via Arclent. Can you confirm our collaboration on this project?\n\nConfirm at: ${verifyUrl}`;
    }

    async function sendDiscordOutreachMessage(opts = {}) {
        const userId = opts.recipientId || state.finalDiscordUserId;
        if (!userId || !/^[0-9]{17,20}$/.test(String(userId).trim())) {
            showToast("Please enter a valid 17-20 digit Discord User ID.", "error");
            if (discordUserIdInput) {
                discordUserIdInput.focus();
                discordUserIdInput.style.borderColor = "var(--red)";
            }
            return;
        }

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "your video";
        const role = state.userRole || "Video editor";

        let text = opts.message;
        if (!text && discordMessageBody && discordMessageBody.value.trim()) {
            text = discordMessageBody.value.trim();
        }
        if (!text) {
            text = generateDiscordDmDraft(creatorName, videoTitle, role);
        } else if (!text.includes("/verify")) {
            const verifyUrl = getVerificationLink();
            text = `${text}\n\nConfirm at: ${verifyUrl}`;
        }

        if (discordErrorAlert) discordErrorAlert.classList.add("hidden");
        if (btnSendDiscordBot) {
            btnSendDiscordBot.disabled = true;
            if (btnSendDiscordText) btnSendDiscordText.innerHTML = `<span class="analyzing-spinner" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 6px;"></span> Sending via Bot...`;
        }

        try {
            const resp = await fetch("/api/outreach/send-discord-message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    discord_user_id: String(userId).trim(),
                    message: text,
                    creator_id: c.channel_name || null,
                    source: "youtube_description"
                })
            });

            const data = await resp.json().catch(() => ({}));

            if (!resp.ok) {
                const errMsg = data.detail || "We couldn't send the Discord message. The creator may have Discord DMs restricted. Try another contact method.";
                if (discordErrorAlert && discordErrorMessage) {
                    discordErrorMessage.textContent = errMsg;
                    discordErrorAlert.classList.remove("hidden");
                }
                showToast(errMsg, "error");
                return;
            }

            // Success!
            state.stage = "sent";
            state.selectedChannel = "discord";
            state.finalDiscordUserId = String(userId).trim();
            saveSessionState();

            // Transition directly to Delivery Success Screen (no manual "I've sent the message" button needed!)
            if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
            if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
            if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
            if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
            if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
            if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

            if (vPendingRecipientSub) {
                const msgIdStr = data.message_id ? ` (ID: ${data.message_id})` : "";
                vPendingRecipientSub.textContent = `Message delivered to Discord User ID ${state.finalDiscordUserId} via Arclent Discord Bot${msgIdStr}`;
            }

            showScreen("deliverySuccess", 4);
            showToast("✓ Message dispatched via Arclent Discord Bot!");
            startVerificationPolling();

        } catch (err) {
            console.error("Discord outreach dispatch error:", err);
            const errMsg = err.message || "Failed to deliver Discord message.";
            if (discordErrorAlert && discordErrorMessage) {
                discordErrorMessage.textContent = errMsg;
                discordErrorAlert.classList.remove("hidden");
            }
            showToast(errMsg, "error");
        } finally {
            if (btnSendDiscordBot) {
                btnSendDiscordBot.disabled = false;
                if (btnSendDiscordText) btnSendDiscordText.textContent = "Send via Arclent Discord Bot ⚡";
            }
        }
    }

    if (btnDiscordSetId && discordUserIdInput) {
        btnDiscordSetId.onclick = () => {
            const rawId = discordUserIdInput.value.trim();
            if (!/^[0-9]{17,20}$/.test(rawId)) {
                showToast("Please enter a valid 17-20 digit Discord User ID.", "error");
                discordUserIdInput.style.borderColor = "var(--red)";
                return;
            }
            discordUserIdInput.style.borderColor = "var(--green)";
            state.finalDiscordUserId = rawId;
            if (state.discordProfile) {
                state.discordProfile.discord_user_id = rawId;
                state.discordProfile.status = "sendable";
            } else {
                state.discordProfile = {
                    discord_user_id: rawId,
                    discord_source: "manual",
                    status: "sendable",
                    url: `https://discord.com/users/${rawId}`
                };
            }
            if (discordStatusBadge) {
                discordStatusBadge.textContent = "SENDABLE · BOT READY";
                discordStatusBadge.style.background = "#DCFCE7";
                discordStatusBadge.style.color = "#166534";
                discordStatusBadge.style.borderColor = "#22C55E";
            }
            if (hubSummaryDiscordVal) {
                hubSummaryDiscordVal.textContent = `User ID: ${rawId}`;
                hubSummaryDiscordVal.style.color = "var(--green)";
            }
            if (discordIdentificationBanner) discordIdentificationBanner.classList.add("hidden");
            if (hubDiscordHeadHandle) hubDiscordHeadHandle.textContent = `Direct message to Discord User ID ${rawId}`;
            if (btnSendDiscordBot) btnSendDiscordBot.disabled = false;
            showToast("✓ Discord User ID set. Ready to send via Arclent Bot!");
        };
    }

    if (btnSendDiscordBot) {
        btnSendDiscordBot.onclick = () => {
            sendDiscordOutreachMessage();
        };
    }

    if (btnCopyDiscordMsg) {
        btnCopyDiscordMsg.onclick = async () => {
            const text = discordMessageBody ? discordMessageBody.value.trim() : "";
            if (!text) return;
            await copyTextToClipboard(text);
            if (btnCopyDiscordText) {
                btnCopyDiscordText.textContent = "✓ Copied!";
                setTimeout(() => { if (btnCopyDiscordText) btnCopyDiscordText.textContent = "📋 Copy Message"; }, 2500);
            }
            showToast("✓ Message copied to clipboard!");
        };
    }

    if (hubEditDiscordBtn) {
        hubEditDiscordBtn.onclick = () => {
            if (hubDiscordBlock) {
                hubDiscordBlock.classList.remove("hidden");
                hubDiscordBlock.scrollIntoView({ behavior: "smooth" });
                if (discordUserIdInput) discordUserIdInput.focus();
            }
        };
    }

    // --------------------------------------------------------------------------
    // STEP 4: Send Real Email & Live Verification Polling
    // --------------------------------------------------------------------------
    function renderVerificationSuccess() {
        if (verificationPollInterval) {
            clearInterval(verificationPollInterval);
            verificationPollInterval = null;
        }

        state.stage = "verified";
        saveSessionState();

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "creator";
        const rawSubs = (c.subscriber_count || "").replace(/subscribers/i, "").trim();
        const audText = (rawSubs && rawSubs !== "Active Creator") 
            ? `${creatorName}'s ${rawSubs} YouTube audience.` 
            : `${creatorName}'s YouTube audience.`;

        if (vSuccessRecipientSub) {
            vSuccessRecipientSub.textContent = `Message delivered to ${creatorName} via verified channel`;
        }

        if (vShieldAudienceText) {
            vShieldAudienceText.textContent = `Collaboration verified against ${audText}`;
        }

        if (deliveryHeaderRow) {
            deliveryHeaderRow.classList.add("hidden");
            deliveryHeaderRow.style.display = "none";
        }
        if (btnBackDelivery) {
            btnBackDelivery.classList.add("hidden");
            btnBackDelivery.style.display = "none";
        }
        if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
        if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
        if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.remove("hidden");

        showScreen("deliverySuccess", 4);
        showToast("✓ Response received! Confirmed by creator.");
    }

    function renderAutoVerifiedSuccess(autoVerify) {
        if (verificationPollInterval) {
            clearInterval(verificationPollInterval);
            verificationPollInterval = null;
        }

        state.stage = "auto_verified";
        saveSessionState();

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const videoTitle = c.video_title || "the video";
        const role = state.userRole || "Video editor";
        const matchedAccount = (autoVerify && autoVerify.matched_account) 
            ? autoVerify.matched_account 
            : (state.linkedInstagramAccount || "contributor");
        const cleanHandle = matchedAccount.replace(/^@+/, "");
        const matchedHandle = `@${cleanHandle}`;

        if (vAutoMatchedHandle) vAutoMatchedHandle.textContent = matchedHandle;
        if (vAutoVerifiedDesc) {
            vAutoVerifiedDesc.innerHTML = `Your username <strong>${escapeHtml(matchedHandle)}</strong> matches with the one mentioned for credits in the video description. Therefore, your collaboration is verified!`;
        }
        if (vAutoCreatorName) vAutoCreatorName.textContent = creatorName;
        if (vAutoCreatorSubs) {
            const rawSubs = (c.subscriber_count || "").trim();
            if (rawSubs && rawSubs.toLowerCase() !== "active creator" && rawSubs.toLowerCase() !== "none") {
                const cleanSubs = rawSubs.replace(/subscribers/i, "").trim();
                vAutoCreatorSubs.textContent = `🔴 ${cleanSubs} subscribers`;
            } else if (rawSubs) {
                vAutoCreatorSubs.textContent = `🔴 ${rawSubs}`;
            } else {
                vAutoCreatorSubs.textContent = "🔴 Active Audience";
            }
        }
        if (vAutoRoleName) vAutoRoleName.textContent = role;
        if (vAutoVideoTitle) vAutoVideoTitle.textContent = `"${videoTitle}"`;
        if (vAutoMatchedAccountVal) vAutoMatchedAccountVal.textContent = `${matchedHandle} (Verified Contributor)`;

        if (deliveryHeaderRow) {
            deliveryHeaderRow.classList.add("hidden");
            deliveryHeaderRow.style.display = "none";
        }
        if (btnBackDelivery) {
            btnBackDelivery.classList.add("hidden");
            btnBackDelivery.style.display = "none";
        }
        if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
        if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
        if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");
        if (verificationAutoVerifiedBox) verificationAutoVerifiedBox.classList.remove("hidden");

        showScreen("deliverySuccess", 4);

        // Mark all progress segments complete
        const segs = [progSeg1, progSeg2, progSeg3, progSeg4];
        segs.forEach(s => {
            if (s) {
                s.className = "seg-bar completed";
            }
        });

        showToast("✓ Automatically verified! Your username matches the video credits.");
    }

    function renderVerificationRejected() {
        if (verificationPollInterval) {
            clearInterval(verificationPollInterval);
            verificationPollInterval = null;
        }

        state.stage = "rejected";
        saveSessionState();

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "creator";

        if (vRejectedRecipientSub) {
            vRejectedRecipientSub.textContent = `Message delivered to ${creatorName} via verified channel`;
        }

        if (vRejectedDescText) {
            vRejectedDescText.textContent = `Collaboration not confirmed. ${creatorName} indicated they did not collaborate on this project.`;
        }

        if (deliveryHeaderRow) deliveryHeaderRow.classList.add("hidden");
        if (btnBackDelivery) btnBackDelivery.classList.add("hidden");
        if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
        if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
        if (verificationRejectedBox) verificationRejectedBox.classList.remove("hidden");

        showScreen("deliverySuccess", 4);
        showToast("✕ Response received: Collaboration declined by creator.", "error");
    }

    function startVerificationPolling() {
        if (verificationPollInterval) clearInterval(verificationPollInterval);
        if (!state.sessionId) return;
        
        const checkStatus = async () => {
            if (!state.sessionId) return;
            try {
                const res = await fetch(`/api/outreach/session-status?session_id=${encodeURIComponent(state.sessionId)}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.creator && !state.creator) {
                        state.creator = data.creator;
                    }
                    if (data.creator_response === "confirmed" || data.stage === "verified") {
                        renderVerificationSuccess();
                    } else if (data.creator_response === "rejected" || data.stage === "rejected") {
                        renderVerificationRejected();
                    }
                }
            } catch (e) {
                // Background polling
            }
        };

        // Immediate check + interval every 1500ms
        checkStatus();
        verificationPollInterval = setInterval(checkStatus, 1500);
    }

    if (workflowEmailForm) {
        workflowEmailForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            if (!state.gmailConnected) {
                showToast("Gmail connection required. Please connect your Gmail account.", "warning");
                handleConnectGmail();
                return;
            }

            const recipient = workflowEmailRecipient ? workflowEmailRecipient.value.trim() : (state.finalEmail || "").trim();
            const subject = workflowEmailSubject ? workflowEmailSubject.value.trim() : "";
            const body = workflowEmailBody ? workflowEmailBody.value.trim() : "";
            state.finalEmail = recipient;

            if (!recipient || !emailRegex.test(recipient)) {
                showToast("Invalid recipient email address.", "error");
                return;
            }

            state.isSending = true;
            workflowSendEmailBtn.disabled = true;
            workflowSendEmailBtn.innerHTML = `<span>Sending...</span><div class="analyzing-spinner" style="width:14px;height:14px;border-width:2px;"></div>`;

            try {
                const res = await fetch("/api/outreach/send-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        recipient: recipient,
                        subject: subject,
                        body: body
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to send email");
                }

                const c = state.creator || {};
                const creatorName = c.name || c.channel_name || "creator";

                if (vPendingRecipientSub) {
                    vPendingRecipientSub.textContent = `Message delivered to ${creatorName} via verified channel`;
                }

                if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
                if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
                if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
                if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
                if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
                if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");

                state.stage = "sent";
                state.selectedChannel = "email";
                saveSessionState();

                showScreen("deliverySuccess", 4);
                showToast("✓ Email inquiry sent with Yes / No verification options!");

                startVerificationPolling();

            } catch (err) {
                showToast(err.message, "error");
            } finally {
                state.isSending = false;
                workflowSendEmailBtn.innerHTML = `<span>Send Verification Email</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`;
                validateSendButton();
            }
        });
    }

    // --------------------------------------------------------------------------
    // Reset / New Search
    // --------------------------------------------------------------------------
    function resetWorkflow() {
        if (verificationPollInterval) {
            clearInterval(verificationPollInterval);
            verificationPollInterval = null;
        }

        try {
            sessionStorage.removeItem("arclent_active_session_id");
            sessionStorage.removeItem("arclent_active_session_data");
        } catch (e) {}

        state.sessionId = null;
        state.stage = "input";
        state.creator = null;
        state.discoveredEmail = null;
        state.emailCandidates = [];
        state.finalEmail = null;
        state.emailConfirmed = false;
        state.instagramProfile = null;
        state.selectedSocialProfile = null;
        state.activeSocialProfile = null;
        state.finalInstagramHandle = null;
        state.finalInstagramUrl = null;
        state.instagramConfirmed = false;
        state.socialProfiles = [];
        state.message = null;
        state.selectedChannel = null;
        state.stageBeforeDelivery = null;
        state.pendingExtensionSession = null;
        state.senderHandle = null;
        state.discordProfile = null;
        state.finalDiscordUserId = null;
        state.discordConfirmed = false;

        if (discordUserIdInput) discordUserIdInput.value = "";
        if (discordMessageBody) discordMessageBody.value = "";
        if (discordErrorAlert) discordErrorAlert.classList.add("hidden");
        if (hubSummaryDiscordRow) hubSummaryDiscordRow.classList.add("hidden");
        if (hubDiscordBlock) hubDiscordBlock.classList.add("hidden");

        if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
        if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
        if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
        if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
        if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");
        if (verificationAutoVerifiedBox) verificationAutoVerifiedBox.classList.add("hidden");
        if (autoVerifyFallbackBanner) autoVerifyFallbackBanner.classList.add("hidden");
        state.autoVerification = null;

        if (youtubeUrlInput) youtubeUrlInput.value = "";
        showScreen("input", 1);
        if (youtubeUrlInput) youtubeUrlInput.focus();
    }

    resetButtons.forEach((btn) => {
        btn.addEventListener("click", resetWorkflow);
    });

    // --------------------------------------------------------------------------
    // Restore Session State across Refresh
    // --------------------------------------------------------------------------
    async function restoreActiveSession() {
        const urlParams = new URLSearchParams(window.location.search);
        const urlSessionId = urlParams.get("session_id");
        let storedSessionId = null;
        try {
            storedSessionId = sessionStorage.getItem("arclent_active_session_id");
        } catch (e) {}

        const targetSessionId = urlSessionId || storedSessionId;
        if (!targetSessionId) return;

        try {
            let cachedData = {};
            try {
                const raw = sessionStorage.getItem("arclent_active_session_data");
                if (raw) cachedData = JSON.parse(raw);
            } catch (e) {}

            const res = await fetch(`/api/outreach/session-status?session_id=${encodeURIComponent(targetSessionId)}`);
            if (res.ok) {
                const data = await res.json();
                state.sessionId = data.session_id;
                state.creator = data.creator || cachedData.creator || null;
                state.userRole = data.user_role || cachedData.userRole || "Video editor";
                state.selectedChannel = data.selected_channel || cachedData.selectedChannel || null;
                state.finalInstagramHandle = data.final_instagram_handle || cachedData.finalInstagramHandle || null;
                state.finalEmail = data.final_email || cachedData.finalEmail || null;
                state.senderHandle = data.sender_handle || cachedData.senderHandle || null;
                state.autoVerification = data.auto_verification || null;

                if (data.stage === "auto_verified" || (data.auto_verification && data.auto_verification.verified)) {
                    renderAutoVerifiedSuccess(data.auto_verification || { matched_account: state.linkedInstagramAccount || "contributor" });
                } else if (data.creator_response === "confirmed" || data.stage === "verified") {
                    renderVerificationSuccess();
                } else if (data.creator_response === "rejected" || data.stage === "rejected") {
                    renderVerificationRejected();
                } else if (data.stage === "sent") {
                    const c = state.creator || {};
                    const creatorName = c.name || c.channel_name || "Creator";
                    const ch = (state.selectedChannel || "verified channel").toUpperCase();
                    if (vPendingRecipientSub) {
                        vPendingRecipientSub.textContent = `Message dispatched to ${creatorName} via ${ch}`;
                    }
                    if (deliveryHeaderRow) deliveryHeaderRow.classList.remove("hidden");
                    if (btnBackDelivery) btnBackDelivery.classList.remove("hidden");
                    if (verificationDmReadyBox) verificationDmReadyBox.classList.add("hidden");
                    if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
                    if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");
                    if (verificationRejectedBox) verificationRejectedBox.classList.add("hidden");
                    showScreen("deliverySuccess", 4);
                    startVerificationPolling();
                }
            }
        } catch (err) {
            console.warn("Could not restore session state:", err);
        }
    }

    // Initialize on page load
    checkGmailStatus();
    isInstagramExtensionInstalled();
    restoreActiveSession();
});
