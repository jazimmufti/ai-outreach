/**
 * Arclent Instagram Assistant — Popup Controller
 */

document.addEventListener("DOMContentLoaded", async () => {
    const sessionBadge = document.getElementById("session-badge");
    const sessionEmptyText = document.getElementById("session-empty-text");
    const sessionDetails = document.getElementById("session-details");
    const sessionUsername = document.getElementById("session-username");
    const sessionStatusText = document.getElementById("session-status-text");
    const sessionMessagePreview = document.getElementById("session-message-preview");
    const btnReTrigger = document.getElementById("btn-re-trigger");

    // Fetch active session from background
    try {
        const res = await chrome.runtime.sendMessage({ type: "GET_OUTREACH_STATUS" });
        const session = res?.session;

        if (session && session.username) {
            sessionEmptyText.classList.add("hidden");
            sessionDetails.classList.remove("hidden");

            sessionUsername.textContent = session.username.startsWith("@") ? session.username : `@${session.username}`;
            sessionMessagePreview.textContent = session.message || "";

            if (session.status === "ready") {
                sessionBadge.textContent = "READY";
                sessionBadge.className = "badge ready";
                sessionStatusText.textContent = "✓ Message Inserted in Instagram";
                sessionStatusText.style.color = "#00D26A";
            } else if (session.status === "pending") {
                sessionBadge.textContent = "PENDING";
                sessionBadge.className = "badge pending";
                sessionStatusText.textContent = "Navigating to Creator DM...";
                sessionStatusText.style.color = "#F59E0B";
            } else {
                sessionBadge.textContent = "ACTIVE";
                sessionBadge.className = "badge";
                sessionStatusText.textContent = session.status || "Active";
            }

            if (btnReTrigger) {
                btnReTrigger.onclick = async () => {
                    const tabs = await chrome.tabs.query({ url: "https://www.instagram.com/*" });
                    if (tabs.length > 0) {
                        await chrome.tabs.update(tabs[0].id, { active: true });
                        await chrome.tabs.sendMessage(tabs[0].id, { type: "TRIGGER_DM_AUTOFILL" }).catch(() => {});
                    } else {
                        await chrome.tabs.create({ url: `https://www.instagram.com/${session.username.replace('@','')}/`, active: true });
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
