/**
 * Creator Discovery & Email Outreach - Sequential SaaS Workflow Controller
 */

document.addEventListener("DOMContentLoaded", () => {
    // --------------------------------------------------------------------------
    // Utilities & Regex
    // --------------------------------------------------------------------------
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // --------------------------------------------------------------------------
    // State Management
    // --------------------------------------------------------------------------
    const state = {
        sessionId: null,
        stage: "input", // input | discovering | creator_found | no_email_choice | manual_email_input | message_draft | instagram_ready | manual_message_ready | sent
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

    // Step Tracker items
    const trackStep1 = document.getElementById("track-step-1");
    const trackStep2 = document.getElementById("track-step-2");
    const trackStep3 = document.getElementById("track-step-3");
    const trackStep4 = document.getElementById("track-step-4");
    const trackStep5 = document.getElementById("track-step-5");

    // Screens
    const screens = {
        input: document.getElementById("screen-input"),
        analyzing: document.getElementById("screen-analyzing"),
        creatorFound: document.getElementById("screen-creator-found"),
        noEmailChoice: document.getElementById("screen-no-email-choice"),
        manualEmail: document.getElementById("screen-manual-email"),
        messageEmail: document.getElementById("screen-message-email"),
        messageInstagram: document.getElementById("screen-message-instagram"),
        messageManual: document.getElementById("screen-message-manual"),
        deliverySuccess: document.getElementById("screen-delivery-success")
    };

    // Screen 1 Elements
    const discoveryForm = document.getElementById("discovery-form");
    const youtubeUrlInput = document.getElementById("youtube-url-input");
    const sampleChips = document.querySelectorAll(".sample-chip");

    // Screen 2 Stepper
    const progStep1 = document.getElementById("prog-step-1");
    const progStep2 = document.getElementById("prog-step-2");
    const progStep3 = document.getElementById("prog-step-3");
    const progStep4 = document.getElementById("prog-step-4");

    // Screen 3A Elements (Creator Found)
    const foundCreatorAvatar = document.getElementById("found-creator-avatar");
    const foundCreatorName = document.getElementById("found-creator-name");
    const foundSubscriberBadge = document.getElementById("found-subscriber-badge");
    const foundChannelHandle = document.getElementById("found-channel-handle");
    const foundVideoLink = document.getElementById("found-video-link");
    const foundVideoTitle = document.getElementById("found-video-title");
    const foundEmailStatusBadge = document.getElementById("found-email-status-badge");
    const foundEmailAddress = document.getElementById("found-email-address");
    const foundEmailSource = document.getElementById("found-email-source");
    const foundEmailVerification = document.getElementById("found-email-verification");
    const foundSocialsContainer = document.getElementById("found-socials-container");
    const foundSocialsList = document.getElementById("found-socials-list");
    const confirmYesBtn = document.getElementById("confirm-yes-btn");
    const confirmNoBtn = document.getElementById("confirm-no-btn");

    // Screen 3B Elements (Email-First Outreach & Discovered Socials Drawer)
    const noemailCreatorAvatar = document.getElementById("noemail-creator-avatar");
    const noemailCreatorName = document.getElementById("noemail-creator-name");
    const noemailSubscriberBadge = document.getElementById("noemail-subscriber-badge");
    const noemailChannelHandle = document.getElementById("noemail-channel-handle");
    const noemailVideoLink = document.getElementById("noemail-video-link");
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

    // Screen 4B Elements (Email Composer)
    const emailFlowConfirmedTitle = document.getElementById("email-flow-confirmed-title");
    const emailFlowConfirmedSub = document.getElementById("email-flow-confirmed-sub");
    const composerTargetEmail = document.getElementById("composer-target-email");
    const composerTargetSource = document.getElementById("composer-target-source");
    const composerTargetConfidence = document.getElementById("composer-target-confidence");
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

    // Screen 4D Elements (Manual Copy)
    const regenerateManualMsgBtn = document.getElementById("regenerate-manual-msg-btn");
    const copyManualMsgBtn = document.getElementById("copy-manual-msg-btn");
    const backFromManualMsgBtn = document.getElementById("back-from-manual-msg-btn");

    // Screen 5 Elements (Delivery Success)
    const resultSender = document.getElementById("result-sender");
    const resultRecipient = document.getElementById("result-recipient");
    const resultMessageId = document.getElementById("result-message-id");
    const resultTimestamp = document.getElementById("result-timestamp");

    const toastContainer = document.getElementById("toast-container");
    const resetButtons = document.querySelectorAll(".reset-workflow-btn");

    // --------------------------------------------------------------------------
    // Toast Notification Utility
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
    // Screen & Step Tracker Manager
    // --------------------------------------------------------------------------
    function setStepTracker(activeStepNum) {
        const trackItems = [trackStep1, trackStep2, trackStep3, trackStep4, trackStep5];
        trackItems.forEach((item, idx) => {
            const stepNum = idx + 1;
            item.classList.remove("active", "completed");
            if (stepNum === activeStepNum) {
                item.classList.add("active");
            } else if (stepNum < activeStepNum) {
                item.classList.add("completed");
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
    // Gmail OAuth & Status Handler
    // --------------------------------------------------------------------------
    async function checkGmailStatus() {
        try {
            const res = await fetch("/api/gmail/status");
            if (!res.ok) throw new Error("Status check failed");
            const data = await res.json();
            
            state.gmailConnected = data.connected;
            state.senderEmail = data.email;
            updateGmailUI();
        } catch (err) {
            state.gmailConnected = false;
            state.senderEmail = null;
            updateGmailUI();
        }
    }

    function updateGmailUI() {
        if (state.gmailConnected && state.senderEmail) {
            gmailStatusPill.className = "status-pill status-connected";
            gmailStatusText.textContent = `Gmail: ${state.senderEmail} ✓`;
            if (headerConnectBtn) headerConnectBtn.style.display = "none";
            if (headerDisconnectBtn) headerDisconnectBtn.style.display = "inline-block";

            if (composerSenderBadge) {
                composerSenderBadge.textContent = `${state.senderEmail} ✓ Connected`;
                composerSenderBadge.style.color = "var(--color-primary-green-dark)";
            }
            if (composerConnectGmailBtn) {
                composerConnectGmailBtn.style.display = "none";
            }
            if (composerDisconnectGmailBtn) {
                composerDisconnectGmailBtn.style.display = "inline-block";
            }
        } else {
            gmailStatusPill.className = "status-pill status-disconnected";
            gmailStatusText.textContent = "Gmail: Not connected";
            if (headerConnectBtn) headerConnectBtn.style.display = "inline-block";
            if (headerDisconnectBtn) headerDisconnectBtn.style.display = "none";

            if (composerSenderBadge) {
                composerSenderBadge.textContent = "Not connected (OAuth required)";
                composerSenderBadge.style.color = "var(--color-accent-amber)";
            }
            if (composerConnectGmailBtn) {
                composerConnectGmailBtn.style.display = "inline-block";
            }
            if (composerDisconnectGmailBtn) {
                composerDisconnectGmailBtn.style.display = "none";
            }
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
                    // Popup blocker detected -> redirect directly in main window
                    window.location.href = data.auth_url;
                    return;
                }

                // Poll status periodically until connected or window closed
                let pollCount = 0;
                const timer = setInterval(async () => {
                    pollCount++;
                    let isClosed = false;
                    try {
                        isClosed = authWindow.closed;
                    } catch (e) {
                        // Cross-origin restriction
                    }

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
            showToast("Gmail account disconnected. You can connect a new account anytime.");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    if (headerConnectBtn) headerConnectBtn.onclick = handleConnectGmail;
    if (headerDisconnectBtn) headerDisconnectBtn.onclick = handleDisconnectGmail;
    if (composerConnectGmailBtn) composerConnectGmailBtn.onclick = handleConnectGmail;
    if (composerDisconnectGmailBtn) composerDisconnectGmailBtn.onclick = handleConnectGmail;

    window.addEventListener("message", (event) => {
        if (event.data && event.data.type === "GMAIL_AUTH_SUCCESS") {
            showToast(`Connected Gmail: ${event.data.email}`);
            checkGmailStatus();
        } else if (event.data && event.data.type === "GMAIL_AUTH_FAILED") {
            showToast(`OAuth Error: ${event.data.error}`, "error");
            checkGmailStatus();
        }
    });

    // Check redirect query param on startup
    if (window.location.search.includes("gmail_connected=true")) {
        showToast("Gmail account connected successfully!");
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // --------------------------------------------------------------------------
    // URL Validation & Discovery (STEP 1 -> STEP 2)
    // --------------------------------------------------------------------------
    function isValidYouTubeUrl(url) {
        if (!url) return false;
        const u = url.trim().toLowerCase();
        return u.includes("youtube.com") || u.includes("youtu.be");
    }

    discoveryForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const url = youtubeUrlInput.value.trim();
        if (!isValidYouTubeUrl(url)) {
            showToast("Please enter a valid YouTube video or channel URL.", "error");
            youtubeUrlInput.focus();
            return;
        }
        startDiscovery(url);
    });

    sampleChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const sampleUrl = chip.getAttribute("data-url");
            youtubeUrlInput.value = sampleUrl;
            startDiscovery(sampleUrl);
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
                    stepEl.className = "progress-step-item running";
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

    function startDiscovery(youtubeUrl) {
        state.stage = "discovering";
        state.sessionId = null;
        state.creator = null;
        state.discoveredEmail = null;
        state.finalEmail = null;

        showScreen("analyzing", 1);
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
                body: JSON.stringify({ youtube_url: youtubeUrl })
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

        // Ensure state.creator is always fully populated from either nested creator or flat data
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
        state.socialProfiles = data.social_profiles || [];
        state.instagramProfile = data.instagram_profile || state.socialProfiles.find(s => s.platform === "Instagram");

        const hasReliableEmail = !!(state.discoveredEmail && state.discoveredEmail.email);

        if (hasReliableEmail) {
            // STEP 3A: Display Creator + Credible Email & Prompt Confirmation
            state.stage = "creator_found";
            renderCreatorFoundScreen();
            showScreen("creatorFound", 2);
        } else {
            // STEP 3B: No Reliable Email Found -> Show 3 Choices
            state.stage = "no_email_choice";
            renderNoEmailChoiceScreen();
            showScreen("noEmailChoice", 3);
        }
    }

    // --------------------------------------------------------------------------
    // SCREEN 3A: Render Creator Found
    // --------------------------------------------------------------------------
    function renderCreatorFoundScreen() {
        const c = state.creator || {};
        const email = state.discoveredEmail || {};

        foundCreatorName.textContent = c.name || c.channel_name || "Creator";
        foundChannelHandle.textContent = c.channel_handle || "@creator";
        foundSubscriberBadge.textContent = c.subscriber_count || "Active Creator";
        foundVideoTitle.textContent = `"${c.video_title || 'YouTube Video'}"`;
        foundVideoLink.href = c.video_url || "#";

        if (c.profile_image) {
            foundCreatorAvatar.src = c.profile_image;
        } else {
            foundCreatorAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name || 'Creator')}&background=00D26A&color=000&bold=true`;
        }

        // Email Details
        foundEmailAddress.textContent = email.email;
        foundEmailSource.textContent = email.source || "YouTube Description";
        foundEmailVerification.textContent = email.source_type === "inferred" ? "Inferred / Domain Match" : "Evidence Verified";

        const badgeClass = email.confidence === "high" ? "badge-high" : "badge-medium";
        foundEmailStatusBadge.className = `badge ${badgeClass}`;
        foundEmailStatusBadge.textContent = email.source_type === "inferred" ? "Inferred" : "Publicly Found";

        // Socials Strip (Instagram, X, Discord, Reddit, Facebook only)
        const allowed = new Set(["Instagram", "X", "X/Twitter", "Discord", "Reddit", "Facebook"]);
        const validSocials = (state.socialProfiles || []).filter(s => allowed.has(s.platform));

        if (validSocials.length > 0) {
            foundSocialsContainer.classList.remove("hidden");
            foundSocialsList.innerHTML = "";
            validSocials.forEach((s) => {
                const card = document.createElement("a");
                card.href = s.url;
                card.target = "_blank";
                card.rel = "noopener noreferrer";
                card.className = "social-card";
                const displayPlat = s.platform === "X/Twitter" ? "X" : s.platform;
                card.innerHTML = `
                    <div class="social-info">
                        <span class="social-platform">${escapeHtml(displayPlat)}</span>
                        <span class="social-username">${escapeHtml(s.username)}</span>
                    </div>
                    <span class="badge badge-high">${s.confidence}</span>
                `;
                foundSocialsList.appendChild(card);
            });
        } else {
            foundSocialsContainer.classList.add("hidden");
        }
    }

    // --------------------------------------------------------------------------
    // SCREEN 3B: Render Email-First Contact & Discovered Socials Drawer
    // --------------------------------------------------------------------------
    function renderNoEmailChoiceScreen() {
        const c = state.creator || {};

        // 1. Populate Creator Identity Strip
        if (noemailCreatorName) noemailCreatorName.textContent = c.name || c.channel_name || "Creator";
        if (noemailChannelHandle) noemailChannelHandle.textContent = c.channel_handle || "@creator";
        if (noemailSubscriberBadge) noemailSubscriberBadge.textContent = c.subscriber_count || "Active Creator";
        if (noemailVideoLink) noemailVideoLink.href = c.video_url || "#";

        if (noemailCreatorAvatar) {
            if (c.profile_image) {
                noemailCreatorAvatar.src = c.profile_image;
            } else {
                noemailCreatorAvatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name || 'Creator')}&background=00D26A&color=000&bold=true`;
            }
        }

        // 2. Reset and Setup Primary Manual Email Input (Top Priority)
        if (noemailManualEmailInput) {
            noemailManualEmailInput.value = "";
            if (noemailManualStatusIcon) noemailManualStatusIcon.textContent = "";
            if (noemailManualErrMsg) noemailManualErrMsg.classList.add("hidden");
            if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = true;
        }

        // 3. Populate Discovered Social Media Profiles & Drawer (Secondary Section)
        const allowed = new Set(["Instagram", "X", "X/Twitter", "Facebook", "LinkedIn", "Discord", "Reddit", "TikTok"]);
        const validSocials = (state.socialProfiles || []).filter(s => allowed.has(s.platform));

        if (socialsCountBadge) {
            socialsCountBadge.textContent = `${validSocials.length} ${validSocials.length === 1 ? 'profile' : 'profiles'} found`;
            socialsCountBadge.className = validSocials.length > 0 ? "badge badge-high" : "badge badge-low";
        }

        if (socialsAccordion) {
            socialsAccordion.open = false; // Closed by default to keep UI uncluttered
        }

        if (noemailSocialsGrid) {
            noemailSocialsGrid.innerHTML = "";
            if (validSocials.length > 0) {
                if (noemailSocialsEmpty) noemailSocialsEmpty.classList.add("hidden");
                validSocials.forEach(s => {
                    const card = document.createElement("div");
                    card.className = "social-profile-card";

                    let platKey = s.platform.toLowerCase();
                    let platIcon = "🔗";
                    let displayPlat = s.platform;

                    if (platKey.includes("twitter") || platKey === "x") {
                        platKey = "x";
                        platIcon = "𝕏";
                        displayPlat = "X / Twitter";
                    } else if (platKey.includes("insta")) {
                        platKey = "instagram";
                        platIcon = "📸";
                        displayPlat = "Instagram";
                    } else if (platKey.includes("face")) {
                        platKey = "facebook";
                        platIcon = "📘";
                        displayPlat = "Facebook";
                    } else if (platKey.includes("link")) {
                        platKey = "linkedin";
                        platIcon = "💼";
                        displayPlat = "LinkedIn";
                    } else if (platKey.includes("disc")) {
                        platKey = "discord";
                        platIcon = "💬";
                        displayPlat = "Discord";
                    } else if (platKey.includes("red")) {
                        platKey = "reddit";
                        platIcon = "🤖";
                        displayPlat = "Reddit";
                    } else if (platKey.includes("tik")) {
                        platKey = "tiktok";
                        platIcon = "🎵";
                        displayPlat = "TikTok";
                    }

                    const handleText = s.username ? (s.username.startsWith("@") ? s.username : `@${s.username}`) : c.name || "Creator Profile";
                    const cleanUrl = s.url ? s.url.replace(/^https?:\/\/(www\.)?/, '') : `${displayPlat.toLowerCase()}.com`;

                    card.innerHTML = `
                        <div class="social-card-top">
                            <span class="social-platform-badge-rich ${platKey}">
                                <span class="plat-icon">${platIcon}</span>
                                <span>${escapeHtml(displayPlat)}</span>
                            </span>
                            <span class="social-verified-tag">✓ Verified Profile</span>
                        </div>
                        <div class="social-card-body">
                            <strong class="social-card-handle">${escapeHtml(handleText)}</strong>
                            <span class="social-card-url-preview" title="${escapeHtml(s.url)}">${escapeHtml(cleanUrl)}</span>
                        </div>
                        <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-visit-profile" id="visit-btn-${platKey}">
                            <span>Visit ${escapeHtml(displayPlat)} →</span>
                        </a>
                    `;
                    noemailSocialsGrid.appendChild(card);
                });
            } else {
                if (noemailSocialsEmpty) noemailSocialsEmpty.classList.remove("hidden");
            }
        }

        // 4. Load or Generate Pitch Message
        loadNoEmailPitchMessage();
    }

    async function loadNoEmailPitchMessage() {
        if (!noemailCopyPitchBody) return;

        if (state.message && state.message.body) {
            noemailCopyPitchBody.value = state.message.body;
            return;
        }

        noemailCopyPitchBody.value = "Generating personalized pitch...";
        try {
            const res = await fetch("/api/outreach/generate-message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    channel: "manual",
                    tone: "conversational"
                })
            });

            if (res.ok) {
                const data = await res.json();
                state.message = data.message;
                noemailCopyPitchBody.value = data.message?.body || "";
            } else {
                const creatorName = state.creator?.name || "there";
                const videoTitle = state.creator?.video_title || "your recent video";
                noemailCopyPitchBody.value = `Hey ${creatorName},\n\nI really enjoyed "${videoTitle}". I'd love to connect regarding a sponsorship or collaboration opportunity that aligns with your audience.\n\nLooking forward to hearing from you!\n\nBest regards,\n[Your Name]`;
            }
        } catch (e) {
            const creatorName = state.creator?.name || "there";
            const videoTitle = state.creator?.video_title || "your recent video";
            noemailCopyPitchBody.value = `Hey ${creatorName},\n\nI really enjoyed "${videoTitle}". I'd love to connect regarding a sponsorship or collaboration opportunity that aligns with your audience.\n\nLooking forward to hearing from you!\n\nBest regards,\n[Your Name]`;
        }
    }

    // Pitch Copy Button Listener
    if (noemailPitchCopyBtn) {
        noemailPitchCopyBtn.onclick = async () => {
            const text = noemailCopyPitchBody ? noemailCopyPitchBody.value.trim() : "";
            if (!text) return;
            try {
                await navigator.clipboard.writeText(text);
                if (noemailPitchBtnText) {
                    noemailPitchBtnText.textContent = "✓ Message copied";
                    setTimeout(() => {
                        noemailPitchBtnText.textContent = "📋 Copy Message";
                    }, 2500);
                }
                showToast("✓ Message copied to clipboard!", "success");
            } catch (err) {
                if (noemailCopyPitchBody) {
                    noemailCopyPitchBody.select();
                    document.execCommand("copy");
                }
                if (noemailPitchBtnText) {
                    noemailPitchBtnText.textContent = "✓ Message copied";
                    setTimeout(() => {
                        noemailPitchBtnText.textContent = "📋 Copy Message";
                    }, 2500);
                }
                showToast("✓ Message copied to clipboard!", "success");
            }
        };
    }

    // Pitch Regenerate Button Listener
    if (noemailPitchRegenBtn) {
        noemailPitchRegenBtn.onclick = async () => {
            state.message = null;
            await loadNoEmailPitchMessage();
            showToast("✓ Pitch regenerated", "success");
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

    // Inline Manual Email Form Submit
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
                        email: email
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

                renderEmailComposerScreen("Contact email added ✓", "Outreach message draft generated for your custom recipient.");
                showScreen("messageEmail", 4);
            } catch (err) {
                showToast(err.message, "error");
            } finally {
                if (noemailManualSubmitBtn) noemailManualSubmitBtn.disabled = false;
            }
        });
    }

    // --------------------------------------------------------------------------
    // STEP 4 Decision Handlers (YES PATH vs NO PATH)
    // --------------------------------------------------------------------------
    confirmYesBtn.onclick = async () => {
        try {
            confirmYesBtn.disabled = true;
            const res = await fetch("/api/outreach/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    creator_confirmed: true
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Confirmation failed");
            }

            const updatedSession = await res.json();
            state.finalEmail = updatedSession.final_email;
            state.emailSource = updatedSession.email_source;
            state.emailConfidence = updatedSession.email_confidence;
            state.message = updatedSession.message;
            state.stage = "message_draft";

            renderEmailComposerScreen("Creator confirmed ✓", "Outreach email draft generated and ready to review.");
            showScreen("messageEmail", 4);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            confirmYesBtn.disabled = false;
        }
    };

    confirmNoBtn.onclick = async () => {
        try {
            confirmNoBtn.disabled = true;
            const res = await fetch("/api/outreach/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    creator_confirmed: false
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to register choice");
            }

            state.discoveredEmail = null;
            state.finalEmail = null;
            state.stage = "no_email_choice";

            renderNoEmailChoiceScreen();
            showScreen("noEmailChoice", 3);
        } catch (err) {
            showToast(err.message, "error");
        } finally {
            confirmNoBtn.disabled = false;
        }
    };

    // --------------------------------------------------------------------------
    // SCREEN 4B: Email Composer & Sending
    // --------------------------------------------------------------------------
    function renderEmailComposerScreen(title, subtitle) {
        emailFlowConfirmedTitle.textContent = title;
        emailFlowConfirmedSub.textContent = subtitle;

        composerTargetEmail.textContent = state.finalEmail;
        composerTargetSource.textContent = state.emailSource || "Manual Entry";
        composerTargetConfidence.textContent = (state.emailConfidence || "HIGH").toUpperCase();

        if (state.message) {
            workflowEmailSubject.value = state.message.subject || "Collaboration Opportunity";
            workflowEmailBody.value = state.message.body || "";
        }

        validateSendButton();
    }

    function validateSendButton() {
        if (!workflowSendEmailBtn) return;
        const canSend = state.gmailConnected && !!state.finalEmail && !state.isSending;
        workflowSendEmailBtn.disabled = !canSend;
    }

    regenerateEmailBtn.onclick = async () => {
        await loadGeneratedMessage("email");
    };

    workflowEmailForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!state.gmailConnected) {
            showToast("Gmail connection required. Connect your Gmail account to send this email.", "warning");
            handleConnectGmail();
            return;
        }

        const recipient = state.finalEmail;
        const subject = workflowEmailSubject.value.trim();
        const body = workflowEmailBody.value.trim();

        if (!recipient || !emailRegex.test(recipient)) {
            showToast("Invalid recipient email address.", "error");
            return;
        }

        state.isSending = true;
        workflowSendEmailBtn.disabled = true;
        workflowSendEmailBtn.innerHTML = `<span>Sending...</span><div class="analyzing-spinner" style="width:16px;height:16px;border-width:2px;"></div>`;

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

            const sendResult = await res.json();

            // Populate Step 5 Screen
            resultSender.textContent = sendResult.sender || state.senderEmail;
            resultRecipient.textContent = sendResult.recipient;
            resultMessageId.textContent = sendResult.message_id || "GMAIL_MSG_" + Math.random().toString(36).substring(2, 9);
            resultTimestamp.textContent = sendResult.timestamp || new Date().toLocaleString();

            state.stage = "sent";
            showScreen("deliverySuccess", 5);
            showToast("✓ Email sent successfully via Gmail API!");

        } catch (err) {
            showToast(err.message, "error");
        } finally {
            state.isSending = false;
            workflowSendEmailBtn.innerHTML = `<span>Send Email</span><svg class="btn-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`;
            validateSendButton();
        }
    });

    // --------------------------------------------------------------------------
    // SCREEN 4C: Instagram Actions
    // --------------------------------------------------------------------------
    copyInstaMsgBtn.onclick = () => {
        const text = instaMessageBody.value.trim();
        if (text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast("✓ Message copied to clipboard!");
            });
        }
    };

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

    backFromInstagramBtn.onclick = () => {
        showScreen("noEmailChoice", 3);
    };

    // --------------------------------------------------------------------------
    // SCREEN 4D: Manual Message Actions
    // --------------------------------------------------------------------------
    regenerateManualMsgBtn.onclick = async () => {
        await loadGeneratedMessage("manual");
    };

    copyManualMsgBtn.onclick = () => {
        const text = manualCopyMessageBody.value.trim();
        if (text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast("✓ Message copied to clipboard!");
            });
        }
    };

    backFromManualMsgBtn.onclick = () => {
        showScreen("noEmailChoice", 3);
    };

    // --------------------------------------------------------------------------
    // Message Generation Helper
    // --------------------------------------------------------------------------
    async function loadGeneratedMessage(channel) {
        try {
            const res = await fetch("/api/outreach/generate-message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    channel: channel
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Message generation failed");
            }

            const data = await res.json();
            state.message = data.message;

            if (channel === "email") {
                workflowEmailSubject.value = data.message.subject || "Collaboration Opportunity";
                workflowEmailBody.value = data.message.body || "";
            } else if (channel === "instagram") {
                instaMessageBody.value = data.message.body || "";
            } else if (channel === "manual") {
                manualCopyMessageBody.value = data.message.body || "";
            }

            showToast("✓ Message generated");
        } catch (err) {
            showToast(err.message, "error");
        }
    }

    // --------------------------------------------------------------------------
    // Reset / New Search
    // --------------------------------------------------------------------------
    function resetWorkflow() {
        state.sessionId = null;
        state.stage = "input";
        state.creator = null;
        state.discoveredEmail = null;
        state.finalEmail = null;
        state.message = null;

        youtubeUrlInput.value = "";
        showScreen("input", 1);
        youtubeUrlInput.focus();
    }

    resetButtons.forEach((btn) => {
        btn.addEventListener("click", resetWorkflow);
    });

    // Helper
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initial check
    checkGmailStatus();
});
