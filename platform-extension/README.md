# Arclent Instagram Outreach Assistant — Chrome Extension (Manifest V3)

The **Arclent Instagram Assistant** Chrome Extension provides 1-click Instagram DM auto-fill for collaboration verification on desktop Chrome.

---

## 🚀 How It Works

```text
Arclent Web App
      │
      │ 1. User clicks "Open Instagram & Send ↗"
      ▼
Chrome Extension (Background & Content Scripts)
      │
      │ 2. Opens/focuses creator's Instagram tab (e.g. instagram.com/creator123)
      │ 3. Automatically clicks the "Message" button
      │ 4. Locates the DM composer (contenteditable / textarea)
      │ 5. Inserts the prepared verification message with verification link
      ▼
Instagram Web Composer Populated
      │
      │ ⛔ STOP (Extension NEVER clicks Send)
      ▼
User manually reviews message and clicks "Send" inside Instagram
      │
      ▼
Arclent Dashboard updates to "Instagram DM Ready" → Real-time Verification Polling
```

---

## 🔒 Safety & Privacy Principles

1. **NEVER Clicks Send**: The extension strictly stops after populating the message into the composer. The final send action always remains 100% under user control.
2. **Zero Credentials Collected**: The extension never reads, intercepts, or requests Instagram passwords, cookies, or session tokens.
3. **No Automated Login**: If Instagram requires login, the standard Instagram login screen handles authentication directly.
4. **Minimum Permissions**: Uses only `storage` and `tabs` permissions, strictly scoped to `https://www.instagram.com/*` and Arclent origins.

---

## 📦 Universal Browser Installation Guide

This extension works across **all modern desktop browsers** (Windows, macOS, Linux). Follow the steps below for your browser:

### 1. Google Chrome & Brave Browser
1. In the URL bar, go to `chrome://extensions` (or `brave://extensions`).
2. Toggle **Developer mode** on (top-right corner).
3. Click **Load unpacked** (top-left).
4. Select the `ai-outreach/instagram-extension` folder.

### 2. Microsoft Edge
1. In the URL bar, go to `edge://extensions`.
2. Toggle **Developer mode** on (bottom-left sidebar or top-right).
3. Click **Load unpacked**.
4. Select the `ai-outreach/instagram-extension` folder.

### 3. Mozilla Firefox
1. In the URL bar, go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Select the `manifest.json` file inside the `ai-outreach/instagram-extension` folder.
4. The extension is now active in Firefox!

### 4. Opera & Opera GX
1. In the URL bar, go to `opera://extensions`.
2. Turn on **Developer mode** (top-right).
3. Click **Load unpacked extension**.
4. Select the `ai-outreach/instagram-extension` folder.

---

## 🧪 Testing the Integration

1. Open your live Arclent web app:
   ```text
   https://ai-outreach-production-8dcc.up.railway.app/
   ```
   (or locally at `http://localhost:8000`) in Google Chrome with the extension loaded.
2. Enter a YouTube URL (e.g., `https://www.youtube.com/watch?v=0e3GPea1Tyg`) and click **"Find the creator"**.
3. In **Step 2 (Instagram)**, confirm the creator's Instagram handle.
4. Click **"Open Instagram & Send ↗"**.
5. **Expected Result**:
   - Instagram opens directly to the creator's profile.
   - The Message button is clicked automatically.
   - The DM composer opens and the Arclent outreach message appears pre-filled.
   - A green floating banner appears: *"✓ Message Ready — Review your message and click Send in Instagram"*.
   - The extension stops and waits for you to click Send.
   - Arclent displays **"Instagram DM Ready"** with the **"I've Sent the Message"** button.

---

## 📁 File Structure

```text
instagram-extension/
├── manifest.json      # Manifest V3 configuration & permission boundaries
├── background.js     # Service worker managing tabs, storage, and message routing
├── content.js        # Injected on instagram.com to locate Message button & fill composer
├── bridge.js         # Injected on Arclent origins for handshake & event relays
├── popup.html        # Extension popup UI matching Arclent dark-emerald theme
├── popup.js          # Popup controller & active session status display
├── popup.css         # Popup styles
├── icons/            # Real PNG icon assets (16x16, 48x48, 128x128)
└── README.md         # Documentation & setup guide
```
