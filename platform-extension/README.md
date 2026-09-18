# Arclent Outreach Assistant — Multi-Platform Chrome Extension (Manifest V3)

The **Arclent Outreach Assistant** Chrome Extension provides 1-click DM auto-fill for collaboration verification across **Instagram, X (Twitter), Discord, and Facebook (Messenger)** on desktop browsers.

---

## 🚀 How It Works

```text
Arclent Web App
      │
      │ 1. User selects platform (Instagram, X, Discord, Facebook) & clicks Outreach
      ▼
Chrome Extension (Background & Content Scripts)
      │
      │ 2. Opens/focuses creator's profile or DM tab
      │ 3. Automatically detects login state (guides login + auto-redirects if needed)
      │ 4. Clicks "Message" button to open DM composer
      │ 5. Inserts prepared verification message with single-instance safety
      ▼
Social Platform Web Composer Populated
      │
      │ ⛔ STOP (Extension NEVER clicks Send)
      ▼
User manually reviews message and clicks "Send" inside the social platform
      │
      ▼
Arclent Dashboard updates to "DM Ready" → Real-time Verification Polling
```

---

## 🔒 Safety & Privacy Principles

1. **NEVER Clicks Send**: The extension strictly stops after populating the message into the composer. The final send action always remains 100% under user control.
2. **Zero Credentials Collected**: The extension never reads, intercepts, or requests passwords, cookies, or session tokens.
3. **No Automated Login**: If a platform requires login, the standard login screen handles authentication directly.
4. **Minimum Permissions**: Uses only `storage` and `tabs` permissions, strictly scoped to the supported social platforms and Arclent origins.
5. **No Public Comment Infiltration**: Strictly verifies that target elements are genuine DM composers and never posts into public comment feeds.

---

## 📦 Universal Browser Installation Guide

This extension works across **all modern desktop browsers** (Windows, macOS, Linux). Follow the steps below for your browser:

### 1. Google Chrome & Brave Browser
1. In the URL bar, go to `chrome://extensions` (or `brave://extensions`).
2. Toggle **Developer mode** on (top-right corner).
3. Click **Load unpacked** (top-left).
4. Select the `ai-outreach/platform-extension` folder.

### 2. Microsoft Edge
1. In the URL bar, go to `edge://extensions`.
2. Toggle **Developer mode** on (bottom-left sidebar or top-right).
3. Click **Load unpacked**.
4. Select the `ai-outreach/platform-extension` folder.

### 3. Mozilla Firefox
1. In the URL bar, go to `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on...**.
3. Select the `manifest.json` file inside the `ai-outreach/platform-extension` folder.
4. The extension is now active in Firefox!

### 4. Opera & Opera GX
1. In the URL bar, go to `opera://extensions`.
2. Turn on **Developer mode** (top-right).
3. Click **Load unpacked extension**.
4. Select the `ai-outreach/platform-extension` folder.

---

## 🧪 Testing the Integration

1. Open your live Arclent web app:
   ```text
   https://ai-outreach-production-8dcc.up.railway.app/
   ```
   (or locally at `http://localhost:8000`) in Google Chrome with the extension loaded.
2. Enter a YouTube URL and find creator contacts.
3. Select any social platform (Instagram, X, Discord, Facebook) and click outreach.
4. **Expected Result**:
   - Platform opens directly to the creator's profile / DM.
   - The Message button is clicked automatically if needed.
   - The DM composer opens and the Arclent outreach message appears pre-filled.
   - A floating banner appears: *"✓ Message Ready — Please review the message and click Send"*.
   - The extension stops and waits for you to click Send.
   - Arclent displays **"DM Ready"** with the **"I've Sent the Message"** button.

---

## 📁 File Structure

```text
platform-extension/
├── manifest.json      # Manifest V3 configuration & permission boundaries
├── background.js     # Service worker managing tabs, storage, and message routing
├── content.js        # Injected on social platforms to locate Message button & fill composer
├── bridge.js         # Injected on Arclent origins for handshake & event relays
├── popup.html        # Extension popup UI matching Arclent dark-emerald theme
├── popup.js          # Popup controller & active session status display
├── popup.css         # Popup styles
├── icons/            # Real PNG icon assets (16x16, 48x48, 128x128)
└── README.md         # Documentation & setup guide
```
