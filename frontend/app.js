/**
 * Arclent Creator Collaboration Verification & Outreach Controller
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

    // --------------------------------------------------------------------------
    // Social Media Icons & Metadata Helper
    // --------------------------------------------------------------------------
    function getSocialMediaMeta(platform) {
        const p = (platform || "").toLowerCase();
        
        if (p.includes("instagram")) {
            return {
                name: "Instagram",
                color: "#E1306C",
                bgColor: "#FDF2F8",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#E1306C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>`
            };
        }
        if (p.includes("twitter") || p === "x" || p.includes("x/")) {
            return {
                name: "X (Twitter)",
                color: "#111827",
                bgColor: "#F3F4F6",
                icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="#111827"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`
            };
        }
        if (p.includes("discord")) {
            return {
                name: "Discord",
                color: "#5865F2",
                bgColor: "#EEF2FF",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.894.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>`
            };
        }
        if (p.includes("reddit")) {
            return {
                name: "Reddit",
                color: "#FF4500",
                bgColor: "#FFF7ED",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#FF4500"><circle cx="12" cy="12" r="10" fill="#FF4500"/><path fill="#FFF" d="M12 7.2a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm6.2 4.4a1.8 1.8 0 0 0-1.4.7c-1.3-.9-3-1.4-4.8-1.5l.8-3.8 2.7.6a1.3 1.3 0 1 0 .3-1.2l-3.2-.7a.4.4 0 0 0-.4.3l-1 4.8c-1.9.1-3.6.6-4.9 1.5a1.8 1.8 0 0 0-2.4 2c-.1.4-.1.8-.1 1.2 0 3 3.4 5.3 7.6 5.3s7.6-2.4 7.6-5.3c0-.4 0-.8-.1-1.2a1.8 1.8 0 0 0-.8-2.6zM9 13.5a1.2 1.2 0 1 1 2.4 0 1.2 1.2 0 0 1-2.4 0zm6 3.3c-.9.9-2.3.9-3 0a.4.4 0 0 1 .5-.5c.5.5 1.5.5 2 0a.4.4 0 1 1 .5.5zm-.1-2.1a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4z"/></svg>`
            };
        }
        if (p.includes("facebook")) {
            return {
                name: "Facebook",
                color: "#1877F2",
                bgColor: "#EFF6FF",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#1877F2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`
            };
        }
        if (p.includes("linkedin")) {
            return {
                name: "LinkedIn",
                color: "#0A66C2",
                bgColor: "#F0F9FF",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#0A66C2"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>`
            };
        }
        if (p.includes("tiktok")) {
            return {
                name: "TikTok",
                color: "#000000",
                bgColor: "#F3F4F6",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#000000"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.24 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>`
            };
        }
        if (p.includes("youtube")) {
            return {
                name: "YouTube",
                color: "#FF0000",
                bgColor: "#FEF2F2",
                icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`
            };
        }

        return {
            name: platform || "Profile",
            color: "#4B5563",
            bgColor: "#F3F4F6",
            icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4B5563" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`
        };
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
        finalEmail: null,
        emailSource: null,
        emailConfidence: null,
        instagramProfile: null,
        socialProfiles: [],
        message: null,
        gmailConnected: false,
        senderEmail: null,
        isSending: false
    };

    // Header elements
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
        creatorFound: document.getElementById("screen-creator-found"),
        noEmailChoice: document.getElementById("screen-no-email-choice"),
        manualEmail: document.getElementById("screen-manual-email"),
        messageEmail: document.getElementById("screen-message-email"),
        messageInstagram: document.getElementById("screen-message-instagram"),
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

    // Screen 3A Elements (Creator Match Confirmation Card)
    const foundCreatorAvatar = document.getElementById("found-creator-avatar");
    const foundCreatorInitial = document.getElementById("found-creator-initial");
    const foundCreatorName = document.getElementById("found-creator-name");
    const foundSubscriberBadge = document.getElementById("found-subscriber-badge");
    const foundChannelHandle = document.getElementById("found-channel-handle");
    const foundVideoTitle = document.getElementById("found-video-title");
    const confirmYesBtn = document.getElementById("confirm-yes-btn");
    const confirmNoBtn = document.getElementById("confirm-no-btn");

    // Screen 3B Elements (No Email Choice & Socials Drawer)
    const noemailCreatorAvatar = document.getElementById("noemail-creator-avatar");
    const noemailCreatorInitial = document.getElementById("noemail-creator-initial");
    const noemailCreatorName = document.getElementById("noemail-creator-name");
    const noemailSubscriberBadge = document.getElementById("noemail-subscriber-badge");
    const noemailChannelHandle = document.getElementById("noemail-channel-handle");
    const noemailVideoTitle = document.getElementById("noemail-video-title");
    const noemailSocialsGrid = document.getElementById("noemail-socials-grid");
    const noemailSocialsEmpty = document.getElementById("noemail-socials-empty");
    const noemailCopyPitchBody = document.getElementById("noemail-copy-pitch-body");
    const noemailPitchRegenBtn = document.getElementById("noemail-pitch-regen-btn");
    const noemailPitchCopyBtn = document.getElementById("noemail-pitch-copy-btn");
    const noemailPitchBtnText = document.getElementById("noemail-pitch-btn-text");
    const noemailManualEmailForm = document.getElementById("noemail-manual-email-form");
    const noemailManualEmailInput = document.getElementById("noemail-manual-email-input");
    const noemailManualStatusIcon = document.getElementById("noemail-manual-status-icon");
    const noemailManualErrMsg = document.getElementById("noemail-manual-err-msg");
    const noemailManualSubmitBtn = document.getElementById("noemail-manual-submit-btn");
    const socialsAccordion = document.getElementById("socials-accordion");
    const socialsCountBadge = document.getElementById("socials-count-badge");

    // Screen 4A Elements (Manual Email Alternative)
    const manualEmailForm = document.getElementById("manual-email-form");
    const manualEmailInputField = document.getElementById("manual-email-input-field");
    const manualEmailStatusIcon = document.getElementById("manual-email-status-icon");
    const manualEmailErrMsg = document.getElementById("manual-email-err-msg");
    const submitManualEmailBtn = document.getElementById("submit-manual-email-btn");
    const backFromManualEmailBtn = document.getElementById("back-from-manual-email-btn");
    const manualCopyMessageBody = document.getElementById("manual-copy-message-body");
    const manualCopyRegenBtn = document.getElementById("manual-copy-regen-btn");
    const manualCopyMessageBtn = document.getElementById("manual-copy-message-btn");
    const manualCopyBtnText = document.getElementById("manual-copy-btn-text");

    // Screen 4B Elements (Email Draft Composer)
    const emailFlowHeading = document.getElementById("email-flow-heading");
    const emailFlowBadge = document.getElementById("email-flow-badge");
    const workflowEmailRecipient = document.getElementById("workflow-email-recipient");
    const composerRecipientSourceTag = document.getElementById("composer-recipient-source-tag");
    const composerSenderBadge = document.getElementById("composer-sender-badge");
    const composerConnectGmailBtn = document.getElementById("composer-connect-gmail-btn");
    const workflowEmailForm = document.getElementById("workflow-email-form");
    const workflowEmailSubject = document.getElementById("workflow-email-subject");
    const workflowEmailBody = document.getElementById("workflow-email-body");
    const regenerateEmailBtn = document.getElementById("regenerate-email-btn");
    const workflowSendEmailBtn = document.getElementById("workflow-send-email-btn");

    // Screen 4C Elements (Instagram)
    const instaUsername = document.getElementById("insta-username");
    const instaCreatorName = document.getElementById("insta-creator-name");
    const instaMessageBody = document.getElementById("insta-message-body");
    const copyInstaMsgBtn = document.getElementById("copy-insta-msg-btn");
    const openInstagramBtn = document.getElementById("open-instagram-btn");
    const backFromInstagramBtn = document.getElementById("back-from-instagram-btn");

    // Screen 5 Elements (Delivery & Verification Status)
    const verificationPendingBox = document.getElementById("verification-pending-box");
    const verificationSuccessBox = document.getElementById("verification-success-box");
    const vPendingRecipientSub = document.getElementById("v-pending-recipient-sub");
    const vSuccessRecipientSub = document.getElementById("v-success-recipient-sub");
    const vShieldAudienceText = document.getElementById("v-shield-audience-text");
    const simulateCreatorConfirmBtn = document.getElementById("simulate-creator-confirm-btn");

    const toastContainer = document.getElementById("toast-container");
    const resetButtons = document.querySelectorAll(".reset-workflow-btn");

    let verificationPollInterval = null;

    // --------------------------------------------------------------------------
    // Toast Utility
    // --------------------------------------------------------------------------
    function showToast(message, type = "success") {
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
        }, 3500);
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
                        }
                    }
                }, 1200);
            }
        } catch (err) {
            showToast(err.message, "error");
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
        state.finalEmail = null;
        state.userRole = role || (userRoleInput ? userRoleInput.value.trim() : "Video editor") || "Video editor";

        showScreen("analyzing", 2);
        updateStepper(1, "running");

        const sseUrl = `/api/outreach/stream?youtube_url=${encodeURIComponent(youtubeUrl)}`;
        let eventSource = null;
        let isFinalized = false;

        try {
            eventSource = new EventSource(sseUrl);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.status === "error") {
                        eventSource.close();
                        handleDiscoveryError(data.error || "We couldn't identify the creator from this URL.");
                        return;
                    }

                    if (data.step >= 1 && data.step <= 4) {
                        updateStepper(data.step, data.status, data.label);
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
                    user_role: state.userRole
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
        state.instagramProfile = data.instagram_profile || state.socialProfiles.find(s => s.platform === "Instagram");

        // ALWAYS SHOW THE CREATOR MATCH SCREEN (Screen 3A) FIRST!
        state.stage = "creator_found";
        renderCreatorFoundScreen();
        showScreen("creatorFound", 3);
    }

    // --------------------------------------------------------------------------
    // Format Arclent Collaboration Confirmation Draft Message
    // --------------------------------------------------------------------------
    function generateConfirmationDraft(creatorName, videoTitle, role) {
        const target = creatorName || "there";
        const roleStr = (role || state.userRole || "Video editor").trim();
        const vTitle = (videoTitle || "your video").trim();
        return `Hi ${target}, someone on Arclent claims they worked as ${roleStr} on "${vTitle}". Can you confirm this collaboration?`;
    }

    // --------------------------------------------------------------------------
    // SCREEN 3A: Render "Is this who you worked with?" (Screenshot Match)
    // --------------------------------------------------------------------------
    function renderCreatorFoundScreen() {
        const c = state.creator || {};

        if (foundCreatorName) foundCreatorName.textContent = c.name || c.channel_name || "Creator";
        if (foundChannelHandle) foundChannelHandle.textContent = c.channel_handle || "@creator";
        if (foundSubscriberBadge) foundSubscriberBadge.textContent = c.subscriber_count || "Active Creator";
        if (foundVideoTitle) foundVideoTitle.textContent = `"${c.video_title || 'YouTube Video'}"`;

        const initialChar = (c.name || c.channel_name || 'M')[0].toUpperCase();
        if (foundCreatorInitial) foundCreatorInitial.textContent = initialChar;

        if (c.profile_image) {
            if (foundCreatorAvatar) {
                foundCreatorAvatar.src = c.profile_image;
                foundCreatorAvatar.classList.remove("hidden");
            }
            if (foundCreatorInitial) foundCreatorInitial.classList.add("hidden");
        } else {
            if (foundCreatorAvatar) foundCreatorAvatar.classList.add("hidden");
            if (foundCreatorInitial) foundCreatorInitial.classList.remove("hidden");
        }
    }

    // --------------------------------------------------------------------------
    // Confirmation Decision Handlers ("Yes, that's them" vs "Not the right creator")
    // --------------------------------------------------------------------------
    if (confirmYesBtn) {
        confirmYesBtn.onclick = async () => {
            try {
                confirmYesBtn.disabled = true;
                const res = await fetch("/api/outreach/confirm", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        creator_confirmed: true,
                        user_role: state.userRole
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Confirmation failed");
                }

                const updatedSession = await res.json();
                
                if (updatedSession.final_email) {
                    state.finalEmail = updatedSession.final_email;
                    state.emailSource = updatedSession.email_source;
                    state.emailConfidence = updatedSession.email_confidence;
                    state.message = updatedSession.message;
                    state.stage = "message_draft";

                    renderEmailComposerScreen();
                    showScreen("messageEmail", 4);
                } else {
                    // No email found -> Go to Screen 3B (Manual email + Socials Drawer)
                    state.stage = "no_email_choice";
                    renderNoEmailChoiceScreen();
                    showScreen("noEmailChoice", 3);
                }
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                confirmYesBtn.disabled = false;
            }
        };
    }

    if (confirmNoBtn) {
        confirmNoBtn.onclick = async () => {
            try {
                confirmNoBtn.disabled = true;
                const res = await fetch("/api/outreach/confirm", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        creator_confirmed: false,
                        user_role: state.userRole
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to register choice");
                }

                state.discoveredEmail = null;
                state.finalEmail = null;
                state.stage = "manual_email_input";

                renderManualEmailScreen();
                showScreen("manualEmail", 3);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                confirmNoBtn.disabled = false;
            }
        };
    }

    // --------------------------------------------------------------------------
    // SCREEN 3B: Render "Is this who you worked with?" (No Email Found)
    // --------------------------------------------------------------------------
    function renderNoEmailChoiceScreen() {
        const c = state.creator || {};

        if (noemailCreatorName) noemailCreatorName.textContent = c.name || c.channel_name || "Creator";
        if (noemailChannelHandle) noemailChannelHandle.textContent = c.channel_handle || "@creator";
        if (noemailSubscriberBadge) noemailSubscriberBadge.textContent = c.subscriber_count || "Active Creator";
        if (noemailVideoTitle) noemailVideoTitle.textContent = `"${c.video_title || 'Creator Video'}"`;

        const initialChar = (c.name || c.channel_name || 'C')[0].toUpperCase();
        if (noemailCreatorInitial) noemailCreatorInitial.textContent = initialChar;

        if (c.profile_image) {
            if (noemailCreatorAvatar) {
                noemailCreatorAvatar.src = c.profile_image;
                noemailCreatorAvatar.classList.remove("hidden");
            }
            if (noemailCreatorInitial) noemailCreatorInitial.classList.add("hidden");
        } else {
            if (noemailCreatorAvatar) noemailCreatorAvatar.classList.add("hidden");
            if (noemailCreatorInitial) noemailCreatorInitial.classList.remove("hidden");
        }

        if (noemailManualEmailInput) {
            noemailManualEmailInput.value = "";
            if (noemailManualStatusIcon) noemailManualStatusIcon.textContent = "";
            if (noemailManualErrMsg) noemailManualErrMsg.classList.add("hidden");
            if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = true;
        }

        // Populate Socials Drawer with Brand Icons
        const allowed = new Set(["Instagram", "X", "X/Twitter", "Facebook", "LinkedIn", "Discord", "Reddit", "TikTok", "YouTube"]);
        const validSocials = (state.socialProfiles || []).filter(s => allowed.has(s.platform));

        if (socialsCountBadge) {
            socialsCountBadge.textContent = `${validSocials.length} ${validSocials.length === 1 ? 'profile' : 'profiles'} found`;
        }

        if (noemailSocialsGrid) {
            noemailSocialsGrid.innerHTML = "";
            if (validSocials.length > 0) {
                if (noemailSocialsEmpty) noemailSocialsEmpty.classList.add("hidden");
                validSocials.forEach(s => {
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
                                <span class="social-handle-text">${escapeHtml(s.username)}</span>
                            </div>
                        </div>
                        <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="btn-retro-outline" style="padding: 5px 12px; font-size: 11.5px; white-space: nowrap;">
                            <span>Open ↗</span>
                        </a>
                    `;
                    noemailSocialsGrid.appendChild(card);
                });
            } else {
                if (noemailSocialsEmpty) noemailSocialsEmpty.classList.remove("hidden");
            }
        }

        if (noemailCopyPitchBody) {
            noemailCopyPitchBody.value = generateConfirmationDraft(c.name || c.channel_name, c.video_title, state.userRole);
        }
    }

    if (noemailPitchCopyBtn) {
        noemailPitchCopyBtn.onclick = async () => {
            const text = noemailCopyPitchBody ? noemailCopyPitchBody.value.trim() : "";
            if (!text) return;
            try {
                await navigator.clipboard.writeText(text);
                if (noemailPitchBtnText) {
                    noemailPitchBtnText.textContent = "✓ Message copied";
                    setTimeout(() => { noemailPitchBtnText.textContent = "📋 Copy Message"; }, 2500);
                }
                showToast("✓ Message copied to clipboard!");
            } catch (err) {
                if (noemailCopyPitchBody) {
                    noemailCopyPitchBody.select();
                    document.execCommand("copy");
                }
                showToast("✓ Message copied to clipboard!");
            }
        };
    }

    if (noemailPitchRegenBtn) {
        noemailPitchRegenBtn.onclick = () => {
            const c = state.creator || {};
            if (noemailCopyPitchBody) {
                noemailCopyPitchBody.value = generateConfirmationDraft(c.name || c.channel_name, c.video_title, state.userRole);
            }
            showToast("✓ Message reset");
        };
    }

    // Inline Manual Email Input Listener
    if (noemailManualEmailInput) {
        noemailManualEmailInput.addEventListener("input", () => {
            const val = noemailManualEmailInput.value.trim();
            if (!val) {
                if (noemailManualStatusIcon) noemailManualStatusIcon.textContent = "";
                if (noemailManualErrMsg) noemailManualErrMsg.classList.add("hidden");
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = true;
                return;
            }

            if (emailRegex.test(val)) {
                if (noemailManualStatusIcon) {
                    noemailManualStatusIcon.textContent = "✓";
                    noemailManualStatusIcon.style.color = "var(--color-primary-green-dark)";
                }
                if (noemailManualErrMsg) noemailManualErrMsg.classList.add("hidden");
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = false;
            } else {
                if (noemailManualStatusIcon) {
                    noemailManualStatusIcon.textContent = "✕";
                    noemailManualStatusIcon.style.color = "var(--color-accent-red)";
                }
                if (noemailManualErrMsg) noemailManualErrMsg.classList.remove("hidden");
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = true;
            }
        });
    }

    if (noemailManualEmailForm) {
        noemailManualEmailForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = noemailManualEmailInput.value.trim();
            if (!emailRegex.test(email)) {
                showToast("Please enter a valid email address.", "error");
                return;
            }

            try {
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = true;
                const res = await fetch("/api/outreach/manual-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        email: email,
                        user_role: state.userRole
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to set manual email");
                }

                const updatedSession = await res.json();
                state.finalEmail = updatedSession.final_email;
                state.emailSource = updatedSession.email_source;
                state.emailConfidence = updatedSession.email_confidence;
                state.message = updatedSession.message;
                state.stage = "message_draft";

                renderEmailComposerScreen();
                showScreen("messageEmail", 4);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = false;
            }
        });
    }

    // --------------------------------------------------------------------------
    // SCREEN 4A: Manual Email Screen (After "Not the right creator")
    // --------------------------------------------------------------------------
    function renderManualEmailScreen() {
        const c = state.creator || {};
        if (manualEmailInputField) manualEmailInputField.value = "";
        if (manualEmailStatusIcon) manualEmailStatusIcon.textContent = "";
        if (manualEmailErrMsg) manualEmailErrMsg.classList.add("hidden");
        if (submitManualEmailBtn) submitManualEmailBtn.disabled = true;

        if (manualCopyMessageBody) {
            manualCopyMessageBody.value = generateConfirmationDraft(c.name || c.channel_name, c.video_title, state.userRole);
        }
    }

    if (manualEmailInputField) {
        manualEmailInputField.addEventListener("input", () => {
            const val = manualEmailInputField.value.trim();
            if (emailRegex.test(val)) {
                if (manualEmailStatusIcon) {
                    manualEmailStatusIcon.textContent = "✓";
                    manualEmailStatusIcon.style.color = "var(--color-primary-green-dark)";
                }
                if (manualEmailErrMsg) manualEmailErrMsg.classList.add("hidden");
                if (submitManualEmailBtn) submitManualEmailBtn.disabled = false;
            } else {
                if (manualEmailStatusIcon) {
                    manualEmailStatusIcon.textContent = val ? "✕" : "";
                    manualEmailStatusIcon.style.color = "var(--color-accent-red)";
                }
                if (manualEmailErrMsg) manualEmailErrMsg.classList.remove("hidden");
                if (submitManualEmailBtn) submitManualEmailBtn.disabled = true;
            }
        });
    }

    if (manualEmailForm) {
        manualEmailForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = manualEmailInputField.value.trim();
            if (!emailRegex.test(email)) {
                showToast("Please enter a valid email address.", "error");
                return;
            }

            try {
                if (submitManualEmailBtn) submitManualEmailBtn.disabled = true;
                const res = await fetch("/api/outreach/manual-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        email: email,
                        user_role: state.userRole
                    })
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || "Failed to set manual email");
                }

                const updatedSession = await res.json();
                state.finalEmail = updatedSession.final_email;
                state.emailSource = updatedSession.email_source;
                state.emailConfidence = updatedSession.email_confidence;
                state.message = updatedSession.message;
                state.stage = "message_draft";

                renderEmailComposerScreen();
                showScreen("messageEmail", 4);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                if (submitManualEmailBtn) submitManualEmailBtn.disabled = false;
            }
        });
    }

    if (manualCopyMessageBtn) {
        manualCopyMessageBtn.onclick = async () => {
            const text = manualCopyMessageBody ? manualCopyMessageBody.value.trim() : "";
            if (!text) return;
            try {
                await navigator.clipboard.writeText(text);
                if (manualCopyBtnText) {
                    manualCopyBtnText.textContent = "✓ Message copied";
                    setTimeout(() => { manualCopyBtnText.textContent = "📋 Copy Message"; }, 2500);
                }
                showToast("✓ Message copied to clipboard!");
            } catch (err) {
                if (manualCopyMessageBody) {
                    manualCopyMessageBody.select();
                    document.execCommand("copy");
                }
                showToast("✓ Message copied to clipboard!");
            }
        };
    }

    if (manualCopyRegenBtn) {
        manualCopyRegenBtn.onclick = () => {
            const c = state.creator || {};
            if (manualCopyMessageBody) {
                manualCopyMessageBody.value = generateConfirmationDraft(c.name || c.channel_name, c.video_title, state.userRole);
            }
            showToast("✓ Message reset");
        };
    }

    if (backFromManualEmailBtn) {
        backFromManualEmailBtn.onclick = () => {
            showScreen("creatorFound", 3);
        };
    }

    // --------------------------------------------------------------------------
    // SCREEN 4B: Render Outreach Email Composer (Matches User Request)
    // --------------------------------------------------------------------------
    function renderEmailComposerScreen() {
        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "Creator";
        const creatorHandle = c.channel_handle || `@${creatorName.toLowerCase().replace(/\s+/g, '')}`;
        const videoTitle = c.video_title || "your video";

        if (emailFlowHeading) emailFlowHeading.textContent = `Reaching out to ${creatorName}`;
        if (emailFlowBadge) emailFlowBadge.textContent = `Auto-sent by Arclent → ${creatorHandle}`;

        const currentRecipient = state.finalEmail || state.discoveredEmail?.email || "";
        if (workflowEmailRecipient) {
            workflowEmailRecipient.value = currentRecipient;
        }
        if (composerRecipientSourceTag) {
            composerRecipientSourceTag.textContent = state.emailSource || "Publicly Found";
        }

        const defaultDraft = generateConfirmationDraft(creatorName, videoTitle, state.userRole);
        const defaultSubject = `Collaboration confirmation for "${videoTitle}"`;

        if (workflowEmailSubject) {
            workflowEmailSubject.value = state.message?.subject || defaultSubject;
        }
        if (workflowEmailBody) {
            workflowEmailBody.value = state.message?.body || defaultDraft;
        }

        validateSendButton();
    }

    function validateSendButton() {
        if (!workflowSendEmailBtn) return;
        const recipientVal = workflowEmailRecipient ? workflowEmailRecipient.value.trim() : (state.finalEmail || "");
        const validRecipient = !!recipientVal && emailRegex.test(recipientVal);
        const canSend = state.gmailConnected && validRecipient && !state.isSending;
        workflowSendEmailBtn.disabled = !canSend;
    }

    if (workflowEmailRecipient) {
        workflowEmailRecipient.addEventListener("input", () => {
            const val = workflowEmailRecipient.value.trim();
            state.finalEmail = val;
            validateSendButton();
        });
    }

    if (regenerateEmailBtn) {
        regenerateEmailBtn.onclick = async () => {
            const c = state.creator || {};
            const creatorName = c.name || c.channel_name || "Creator";
            const videoTitle = c.video_title || "your video";
            
            workflowEmailSubject.value = `Collaboration confirmation for "${videoTitle}"`;
            workflowEmailBody.value = generateConfirmationDraft(creatorName, videoTitle, state.userRole);
            showToast("✓ Draft reset to standard confirmation template");
        };
    }

    // --------------------------------------------------------------------------
    // SCREEN 4C: Instagram Actions
    // --------------------------------------------------------------------------
    if (copyInstaMsgBtn) {
        copyInstaMsgBtn.onclick = () => {
            const text = instaMessageBody.value.trim();
            if (text) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast("✓ Message copied to clipboard!");
                });
            }
        };
    }

    if (openInstagramBtn) {
        openInstagramBtn.onclick = () => {
            const text = instaMessageBody.value.trim();
            if (text) {
                navigator.clipboard.writeText(text).then(() => {
                    showToast("✓ Message copied! Opening Instagram profile...");
                });
            }
            const username = state.instagramProfile?.username?.replace("@", "") || "";
            const profileUrl = state.instagramProfile?.url || `https://instagram.com/${username}`;
            window.open(profileUrl, "_blank", "noopener,noreferrer");
        };
    }

    if (backFromInstagramBtn) {
        backFromInstagramBtn.onclick = () => {
            showScreen("noEmailChoice", 3);
        };
    }

    // --------------------------------------------------------------------------
    // SCREEN 5: Email Submission & Live Verification Polling
    // --------------------------------------------------------------------------
    function renderVerificationSuccess() {
        if (verificationPollInterval) {
            clearInterval(verificationPollInterval);
            verificationPollInterval = null;
        }

        const c = state.creator || {};
        const creatorName = c.name || c.channel_name || "MrBeast";
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

        if (verificationPendingBox) verificationPendingBox.classList.add("hidden");
        if (verificationSuccessBox) verificationSuccessBox.classList.remove("hidden");

        showToast("✓ Response received! Confirmed by creator.");
    }

    function startVerificationPolling() {
        if (verificationPollInterval) clearInterval(verificationPollInterval);
        
        verificationPollInterval = setInterval(async () => {
            if (!state.sessionId) return;
            try {
                const res = await fetch(`/api/outreach/session-status?session_id=${state.sessionId}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.creator_response === "confirmed" || data.stage === "verified") {
                        renderVerificationSuccess();
                    }
                }
            } catch (e) {
                // Background polling
            }
        }, 2500);
    }

    if (simulateCreatorConfirmBtn) {
        simulateCreatorConfirmBtn.onclick = async () => {
            try {
                simulateCreatorConfirmBtn.disabled = true;
                const res = await fetch("/api/outreach/simulate-creator-response", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: state.sessionId,
                        action: "confirm"
                    })
                });
                if (res.ok) {
                    renderVerificationSuccess();
                } else {
                    showToast("Simulation failed", "error");
                }
            } catch (err) {
                showToast("Simulation error", "error");
            } finally {
                simulateCreatorConfirmBtn.disabled = false;
            }
        };
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
            const subject = workflowEmailSubject.value.trim();
            const body = workflowEmailBody.value.trim();
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

                if (verificationPendingBox) verificationPendingBox.classList.remove("hidden");
                if (verificationSuccessBox) verificationSuccessBox.classList.add("hidden");

                state.stage = "sent";
                showScreen("deliverySuccess", 4);
                showToast("✓ Email inquiry sent with Yes / No verification options!");

                startVerificationPolling();

            } catch (err) {
                showToast(err.message, "error");
            } finally {
                state.isSending = false;
                workflowSendEmailBtn.innerHTML = `<span>Send Email</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`;
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

        state.sessionId = null;
        state.stage = "input";
        state.creator = null;
        state.discoveredEmail = null;
        state.finalEmail = null;
        state.message = null;

        if (youtubeUrlInput) youtubeUrlInput.value = "";
        showScreen("input", 1);
        if (youtubeUrlInput) youtubeUrlInput.focus();
    }

    resetButtons.forEach((btn) => {
        btn.addEventListener("click", resetWorkflow);
    });

    // Initialize Gmail status on page load
    checkGmailStatus();
});
