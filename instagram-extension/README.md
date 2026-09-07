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

## 📦 Installation (Developer Mode)

To install and use the extension locally in Google Chrome:

1. Open Google Chrome.
2. In the URL address bar, navigate to:
   ```text
   chrome://extensions
   ```
3. Enable **Developer mode** using the toggle in the top-right corner.
4. Click the **Load unpacked** button in the top-left corner.
5. Select the `instagram-extension/` directory from this project repository:
   ```text
   ai-outreach/instagram-extension
   ```
6. The extension **"Arclent Instagram Assistant"** will now appear in your list of active extensions with its green Arclent icon.

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
