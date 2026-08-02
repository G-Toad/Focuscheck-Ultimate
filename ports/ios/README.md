# FocusCheck iOS - YouTube Hypnosis Breaker

Break free from infinite scroll on your iPhone through **forced self-confrontation**. Not just prompts - you have to write out what you're doing and confront the consequences.

## 🎯 What It Does

**Your Problem:** You open YouTube on your phone and get hypnotized for hours until your battery dies or someone interrupts you.

**The Solution:** FocusCheck detects when you're on YouTube/browser and forces you to **write out** your thoughts every 2-5 minutes:
- Can't just click "I'm focused" - you have to **TYPE OUT** what you're working on
- Uses challenge questions like: *"How are you lying to yourself right now?"*
- Requires specific keywords in responses (e.g., must include "wasting" or "afraid")
- Validates text to prevent gibberish or mindless responses
- The act of **writing forces consciousness** - breaks the hypnotic trance

**Emergency Pause:** Quick disable via widget or Control Center for genuine emergencies (won't interfere with survival scenarios).

## ✨ Features

### Core Psychological Engine
- ✅ **Forced Written Reflection** - Can't just click buttons - must type out thoughts
- ✅ **Challenge System** - Questions require specific keywords to force genuine reflection
- ✅ **Spam Detection** - Rejects gibberish, keyboard mashing, or vague responses
- ✅ **Ego Confrontation** - Questions like "How are you lying to yourself?"

### Technical Features
- ✅ **YouTube/Browser Detection** - Automatically detects when you open distracting apps
- ✅ **Escalating Prompts** - Start at 3 minutes, escalate to 30 seconds if ignored
- ✅ **Critical Notifications** - Break through Do Not Disturb when needed
- ✅ **Emergency Pause** - One-tap disable via widget or lock screen
- ✅ **Live Activity** - Persistent countdown in Dynamic Island and Always-On Display
- ✅ **Daily Stats** - Track distraction time and response patterns

## 🧠 The Psychological Mechanism

### Why Writing Works

Simple buttons don't work - your brain can click "I'm focused" on autopilot while scrolling YouTube. But **writing forces consciousness**:

1. **You have to articulate** what you're doing
2. **You have to confront** the consequences
3. **You can't lie as easily** when you write it out
4. **The ego gets engaged** - you see your own words

### Challenge Questions

The app randomly selects from psychological barrier questions:

**If you say "I'm productive":**
- *"What EXACTLY are you learning right now?"* (must include "learning")
- *"What WILL you accomplish in the next 20 minutes?"* (must include "will")
- *"What specific OUTPUT will you have after this?"* (must include "finished/completed/done")

**If you admit "I'm distracted":**
- *"How are you lying to yourself right now?"* (must include "lying/pretending")
- *"What will TOMORROW you regret about RIGHT NOW you?"* (must include "tomorrow/regret")
- *"What are you ACTUALLY afraid of?"* (must include "scared/afraid/anxious")
- *"What are you doing instead of what you SHOULD do?"* (must include "should")

### Spam Detection

Can't type garbage to dismiss it:
- ❌ "aaa" → Rejected (low character diversity)
- ❌ "asdfgh" → Rejected (keyboard pattern detected)
- ❌ "idk stuff" → Rejected (banned vague words)
- ❌ Answered in 0.5s → Rejected (too fast)
- ❌ "not lying" when asked about lying → Rejected (denial pattern)

You HAVE to give a real answer.

### Escalation Levels
| Level | Check-in Interval | Effects |
|-------|------------------|---------|
| 0 | 3 minutes | Gentle notifications |
| 1 | 2 minutes | Time Sensitive notifications |
| 2 | 90 seconds | Critical alerts, screen shake |
| 3 | 60 seconds | Loud alarm sounds, red screen |
| 4+ | 30 seconds | Maximum intensity |

## 📱 Requirements

- iPhone running iOS 16.1+ (iOS 17+ recommended)
- iPhone 15 or newer for Dynamic Island features
- Xcode 15+ for building
- Apple Developer account (free tier works)

## 🚀 Setup Instructions

### 1. Open in Xcode

```bash
# Navigate to the project folder
cd FocusCheckiOS

# Open in Xcode
open FocusCheckiOS.xcodeproj
```

If you don't have an `.xcodeproj` file yet, create one:
1. Open Xcode
2. File → New → Project
3. Choose "iOS" → "App"
4. Product Name: `FocusCheckiOS`
5. Bundle Identifier: `com.yourname.focuscheck`
6. Interface: SwiftUI
7. Language: Swift

### 2. Add Source Files

Drag all the `.swift` files from this folder into your Xcode project:

```
FocusCheckiOS/
├── FocusCheckiOSApp.swift          (Main app)
├── Models/
│   └── AppState.swift              (State management)
├── Managers/
│   ├── NotificationManager.swift   (Notifications)
│   └── ActivityMonitorManager.swift (Screen Time monitoring)
├── Views/
│   ├── ContentView.swift           (Main UI)
│   └── CheckInView.swift           (Check-in dialog)
├── LiveActivity/
│   └── FocusCheckLiveActivity.swift (Dynamic Island)
├── DeepLinkHandler.swift           (Widget integration)
└── Info.plist
```

### 3. Add Capabilities in Xcode

**Signing & Capabilities Tab:**

1. **Screen Time** (Required)
   - Click "+ Capability"
   - Add "Family Controls"

2. **Push Notifications** (Required)
   - Add "Push Notifications"

3. **Background Modes** (Required)
   - Add "Background Modes"
   - Check "Background processing"

4. **App Groups** (For widget sharing)
   - Add "App Groups"
   - Create group: `group.com.focuscheck.shared`

### 4. Create Widget Extension

1. File → New → Target
2. Choose "Widget Extension"
3. Product Name: `FocusCheckWidget`
4. Include Configuration Intent: No
5. Add the widget code from `FocusCheckWidget/FocusCheckWidget.swift`
6. Add same App Group capability to widget target

### 5. Configure Info.plist

Make sure your `Info.plist` includes:

```xml
<key>NSUserNotificationsUsageDescription</key>
<string>FocusCheck needs notifications to prompt you when distracted by YouTube.</string>

<key>NSFamilyControlsUsageDescription</key>
<string>FocusCheck monitors app usage to help you stay focused.</string>

<key>NSSupportsLiveActivities</key>
<true/>
```

### 6. Request Permissions on First Launch

When you first run the app, it will request:
1. **Notification permissions** - Tap "Allow"
2. **Screen Time permissions** - Tap "Allow" in Settings

**Important:** Screen Time permission requires you to go to Settings → Screen Time → "Allow Access" and enable for FocusCheck.

### 7. Configure YouTube Monitoring

In the app:
1. Toggle "YouTube Monitoring" ON
2. The app will start monitoring immediately
3. Open YouTube to test (you'll get prompted after 2 minutes)

### 8. Add Widget to Lock Screen

**For Emergency Pause Access:**
1. Lock your iPhone
2. Long-press the lock screen
3. Tap "Customize" → "Lock Screen"
4. Add "FocusCheck Control" widget
5. Tap widget to pause/resume instantly

**For Dynamic Island (iPhone 15+):**
- Start monitoring
- You'll see a persistent countdown in the Dynamic Island
- Tap to expand and see stats

## 🎮 Usage

### Normal Flow

1. **Open YouTube/Browser**
   - FocusCheck detects you opened a distracting app
   - Starts monitoring session

2. **First Prompt (2 minutes)**
   - Notification: "Quick Check-In - Are you still focused?"
   - Tap notification → App opens to full-screen check-in

3. **Check-In Dialog**
   - **Step 1:** "Are you productive or distracted?" (buttons)
   - **Step 2:** Type out your answer to a reflection question

4. **Reflection Question Examples**
   - If productive: *"What EXACTLY are you learning right now?"*
   - If distracted: *"How are you lying to yourself right now?"*
   - Must include specific keywords (e.g., "learning", "lying")
   - Can't submit gibberish or vague answers

5. **Validation**
   - ✅ Valid response → Dialog closes, timer resets
   - ❌ Invalid response → Error message, must try again
   - Examples of rejection:
     - "aaa" → *"Low character diversity detected"*
     - "idk stuff" → *"Dismissive word detected: 'idk'"*
     - Missing keyword → *"You must include 'lying' and be specific"*

6. **If You Ignore Notification**
   - Escalation level increases
   - Next prompt comes faster (2min → 90s → 60s → 30s)
   - Notifications get more aggressive (louder, critical alerts)
   - Challenge questions become more confrontational

### Emergency Pause

**Quick Pause Options:**

1. **Via Widget** (Fastest)
   - Tap the lock screen widget
   - Instant pause/resume

2. **Via App**
   - Orange "EMERGENCY PAUSE" button
   - Choose duration: 5 min / 15 min / 1 hour / Indefinite

3. **Via Notification**
   - Swipe → "Snooze 5 min"

**When to Use:**
- Medical emergency
- Important phone call
- Need to look something up urgently
- Any situation where prompts would interfere

**Auto-Resume:**
- If you pause for X minutes, app auto-resumes after
- You'll get a warning notification 30s before resume

## 📊 Understanding the Stats

### Main Screen

- **Status Card**
  - Green dot = Monitoring active
  - Orange dot = Paused
  - Red triangle = High escalation level

- **Today's Activity**
  - Distracted: Minutes spent off-task
  - Ignored: Number of prompts you dismissed
  - Streak: Consecutive focused responses

### Live Activity (iPhone 15)

- **Compact (Dynamic Island)**
  - Left: Eye icon (monitoring) or Pause icon
  - Right: Countdown timer to next check-in

- **Expanded**
  - Current status and level
  - Minutes wasted today
  - Quick pause/check-in buttons

## 🔧 Customization

### Change Check-In Frequency

Edit `AppState.swift`:

```swift
// Base interval (Level 0)
checkInIntervalSeconds = 180  // 3 minutes (change to 120 for 2 min, etc.)
```

### Add More Distracting Apps

Edit `AppState.swift`:

```swift
distractingAppsBlockList: Set<String> = [
    "com.google.ios.youtube",
    "com.brave.ios.browser",
    "com.twitter.twitter",        // Add Twitter
    "com.instagram.instagram",    // Add Instagram
    // Add more bundle IDs here
]
```

To find an app's bundle ID:
1. Install the app
2. Use Xcode → Window → Devices and Simulators
3. Select your device → Installed Apps → find the app

### Adjust Escalation Thresholds

Edit `AppState.swift` → `updateCheckInInterval()`:

```swift
switch escalationLevel {
case 0:
    checkInIntervalSeconds = 180  // Modify intervals here
case 1:
    checkInIntervalSeconds = 120
// etc.
}
```

## 🐛 Troubleshooting

### Notifications Not Appearing

1. Check Settings → Notifications → FocusCheck
   - Allow Notifications: ON
   - Critical Alerts: ON (if available)
   - Time Sensitive Notifications: ON

2. Check Do Not Disturb
   - Settings → Focus → Do Not Disturb
   - Allow notifications from FocusCheck

### Screen Time Monitoring Not Working

1. Settings → Screen Time
   - Enable Screen Time if disabled
   - Scroll down → "Allow Access for Apps"
   - Enable FocusCheck

2. If still not working:
   - Delete app
   - Reinstall
   - Re-grant permissions

### Widget Not Updating

1. Remove and re-add widget
2. Check App Groups capability matches in both targets
3. Verify bundle identifier: `group.com.focuscheck.shared`

### Live Activity Not Showing

1. Settings → FocusCheck → Live Activities: ON
2. iPhone 15+ required for Dynamic Island
3. iOS 16.1+ required for any Live Activity

### App Draining Battery

- Normal: ~5-10% per day with active monitoring
- If higher:
  - Check Background App Refresh is OFF
  - Reduce check-in frequency
  - Use Pause when not needed

## 🔒 Privacy

- **All data stays on your device** - No cloud sync
- **No tracking or analytics** - We don't collect anything
- **Screen Time data** - Only used to detect app opens, not recorded
- **Notification content** - Never leaves your phone

## 📝 Notes

### iOS Limitations

- Can't force-block apps (by design, for emergencies)
- Can't prevent notification dismissal
- Can't run continuously in background forever

### What This Solves

✅ Breaking YouTube/social media trances
✅ Gentle reminders without hard blocks
✅ Emergency access maintained
✅ Self-awareness of time wasted

### What This Doesn't Do

❌ Hard app blocks (use Screen Time limits for that)
❌ Parent controls (use Screen Time for kids)
❌ Complete lockdown (intentional - safety first)

## 🚨 Safety Features

**Why Emergency Pause Exists:**

- Medical emergencies (calling 911, looking up symptoms)
- Navigation (Maps, ride-sharing apps)
- Important communications (texts from family)
- Time-sensitive work (checking flight times, etc.)

**The pause is easy to access** because your safety > productivity gains.

## 🎨 Customization Ideas

### Change Colors

Edit `ContentView.swift` and `CheckInView.swift`:

```swift
// Background gradient
LinearGradient(
    colors: [Color.black, Color.purple.opacity(0.3)],  // Customize here
    startPoint: .top,
    endPoint: .bottom
)
```

### Add Sounds

1. Add `.mp3` file to project (named `alarm.mp3`)
2. `CheckInView.swift` will play it at escalation level 3+

### Custom Messages

Edit `NotificationManager.swift` → `scheduleCheckIn()`:

```swift
case 0:
    content.title = "Your Custom Title"
    content.body = "Your custom message"
```

## 📈 Future Enhancements

Potential additions:
- [ ] Task/goal tracking integration
- [ ] Export analytics to CSV
- [ ] Shortcuts actions
- [ ] Apple Watch companion
- [ ] Focus mode integration
- [ ] Custom app categories

## 🤝 Contributing

This is a personal tool made for breaking YouTube addiction. Feel free to:
- Fork and customize for your needs
- Share improvements
- Report bugs

## 📄 License

Free to use and modify for personal use.

## 💬 Questions?

Check the Windows FocusCheck implementation in `/focuscheck` for inspiration on additional features.

---

**Remember:** The goal isn't perfection - it's breaking the hypnotic trance. Even responding to 50% of prompts is a huge win over hours of mindless scrolling.

Stay focused! 🎯
