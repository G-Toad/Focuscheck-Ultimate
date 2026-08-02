# Quick Setup Guide - FocusCheck iOS

## Prerequisites Checklist

- [ ] Mac with macOS Ventura or later
- [ ] Xcode 15+ installed
- [ ] iPhone 15 with iOS 17+ (iOS 16.1+ minimum)
- [ ] Apple Developer account (free tier OK)
- [ ] USB cable to connect iPhone to Mac

## Step-by-Step Setup (30 minutes)

### Part 1: Create Xcode Project (10 min)

1. **Open Xcode**
   ```
   Applications → Xcode
   ```

2. **Create New Project**
   - File → New → Project
   - iOS → App
   - Product Name: `FocusCheckiOS`
   - Team: Select your Apple ID
   - Organization Identifier: `com.yourname` (use your name)
   - Bundle Identifier will be: `com.yourname.focuscheck`
   - Interface: **SwiftUI**
   - Language: **Swift**
   - Storage: None
   - Click "Next" → Choose save location

3. **Copy Source Files**
   - Delete the default `ContentView.swift` Xcode created
   - Drag all folders from this `FocusCheckiOS` directory into Xcode:
     - FocusCheckiOSApp.swift
     - Models/
     - Managers/
     - Views/
     - LiveActivity/
     - DeepLinkHandler.swift
   - When prompted: ✅ "Copy items if needed"

4. **Replace Info.plist**
   - Delete the default Info.plist in Xcode
   - Drag in the Info.plist from this folder

### Part 2: Add Capabilities (5 min)

1. **Select Project in Navigator**
   - Click the blue project icon at the top of the file list

2. **Select Target**
   - Click "FocusCheckiOS" under TARGETS (not PROJECTS)

3. **Go to "Signing & Capabilities" Tab**

4. **Add Capabilities** (click "+ Capability" button for each):

   **a) Family Controls**
   - Search "Family"
   - Add "Family Controls"

   **b) Push Notifications**
   - Search "Push"
   - Add "Push Notifications"

   **c) Background Modes**
   - Search "Background"
   - Add "Background Modes"
   - Check: ✅ "Background processing"

   **d) App Groups**
   - Search "App Groups"
   - Add "App Groups"
   - Click "+" under App Groups
   - Enter: `group.com.focuscheck.shared`
   - Click OK

### Part 3: Add Widget Extension (10 min)

1. **Create Widget Target**
   - File → New → Target
   - iOS → Widget Extension
   - Product Name: `FocusCheckWidget`
   - Include Configuration Intent: **NO** (uncheck)
   - Click "Finish"
   - Click "Activate" when asked about scheme

2. **Add Widget Code**
   - Xcode created: `FocusCheckWidget/FocusCheckWidget.swift`
   - Delete its contents
   - Copy contents from this folder's `FocusCheckWidget/FocusCheckWidget.swift`
   - Paste into Xcode's widget file

3. **Add App Groups to Widget**
   - Select project → TARGETS → FocusCheckWidget
   - Signing & Capabilities tab
   - Click "+ Capability"
   - Add "App Groups"
   - Click "+" under App Groups
   - Enter: `group.com.focuscheck.shared` (same as before)

### Part 4: Connect iPhone and Test (5 min)

1. **Connect iPhone via USB**

2. **Trust Computer**
   - iPhone will show "Trust This Computer?" → Trust
   - Enter your iPhone passcode

3. **Select Device in Xcode**
   - Top bar: Click device dropdown (says "iPhone 15" or similar)
   - Select your connected iPhone

4. **Run App**
   - Click the ▶ (Play) button in Xcode
   - Or press Cmd+R
   - First time: Enter your Apple ID password if asked

5. **Trust Developer Certificate on iPhone**
   - App will install but not launch
   - On iPhone: Settings → General → VPN & Device Management
   - Tap your Apple ID name
   - Tap "Trust"
   - Tap "Trust" again to confirm

6. **Launch App Again**
   - Press ▶ in Xcode again
   - App should launch on your iPhone

### Part 5: Grant Permissions (5 min)

**On your iPhone:**

1. **Notifications Permission**
   - App will ask: "FocusCheck Would Like to Send You Notifications"
   - Tap "Allow"

2. **Screen Time Permission** (Critical!)
   - Close the app
   - Go to iPhone Settings → Screen Time
   - If Screen Time is OFF → Turn it ON
   - Scroll down → Tap "App & Website Activity"
   - Turn ON "App & Website Activity"
   - Back → Tap "Content & Privacy Restrictions"
   - Scroll down → Tap "Screen Time"
   - Enable "FocusCheck"

3. **Critical Alerts** (Optional but recommended)
   - Settings → Notifications → FocusCheck
   - Toggle ON: "Critical Alerts"
   - This lets notifications break through Do Not Disturb

4. **Return to App**
   - Launch FocusCheck
   - Toggle "YouTube Monitoring" ON
   - You should see status change to "Monitoring"

## Testing the Setup

### Test 1: Basic Notification
1. In FocusCheck app, note the "Next check-in" time
2. Lock your phone
3. Wait for the check-in time
4. You should receive a notification: "Quick Check-In"
5. ✅ **Success!** Notifications are working

### Test 2: YouTube Detection
1. Toggle "YouTube Monitoring" ON in FocusCheck
2. Open YouTube app
3. Within 30 seconds, you should get a notification
4. ✅ **Success!** App detection is working

### Test 3: Widget
1. Lock iPhone
2. Long-press lock screen
3. Tap "Customize" → Lock Screen
4. Tap "+ Add Widget"
5. Scroll to "FocusCheck Control"
6. Add it
7. Tap "Done"
8. Tap the widget to pause/resume
9. ✅ **Success!** Widget is working

### Test 4: Check-In Dialog
1. When you get a notification, swipe and tap it
2. App should open to the check-in screen
3. Tap "✅ Yes, I'm Focused"
4. ✅ **Success!** Check-in flow works

## Troubleshooting Quick Fixes

### "Failed to install app" in Xcode
**Fix:**
- Disconnect iPhone
- In Xcode: Product → Clean Build Folder (Cmd+Shift+K)
- Reconnect iPhone
- Try again

### "Code signing error"
**Fix:**
- Project settings → Signing & Capabilities
- Team dropdown → Select your Apple ID
- If still fails: Create a new identifier
  - Change "com.yourname.focuscheck" to "com.yourname.focuscheck2"

### Notifications not appearing
**Fix:**
- Settings → Notifications → FocusCheck → Allow Notifications: ON
- Settings → Focus → Do Not Disturb → Allowed Notifications → Add "FocusCheck"
- Restart iPhone

### Screen Time permission denied
**Fix:**
- Settings → Screen Time → Turn OFF
- Wait 10 seconds
- Turn ON again
- Settings → Screen Time → Content & Privacy Restrictions → Screen Time → Enable FocusCheck
- Delete and reinstall app if needed

### Widget not showing up
**Fix:**
- Make sure you added App Groups to BOTH targets
- Group name must be identical: `group.com.focuscheck.shared`
- Delete app, clean build folder, reinstall

### App crashes immediately
**Fix:**
- Check Xcode console for error message
- Most common: Missing capability or wrong bundle ID
- Try: Product → Clean Build Folder → Run again

## Common Issues During Development

### "Cannot find 'FamilyControls' in scope"
- Did you add "Family Controls" capability?
- Make sure iOS deployment target is 15.0+

### "Cannot find 'ActivityKit' in scope"
- iOS 16.1+ required for Live Activities
- Check deployment target in project settings

### Widget shows "Unable to Load"
- App Groups not matching
- Check spelling: `group.com.focuscheck.shared`
- Must be added to both app target and widget target

## Final Checklist

Before you start using FocusCheck:

- [ ] App launches without crashing
- [ ] "Monitoring" shows green status
- [ ] Received at least one check-in notification
- [ ] Emergency pause button works
- [ ] Lock screen widget is added and functional
- [ ] Screen Time permission granted
- [ ] Notification permission granted
- [ ] Critical Alerts enabled (optional)

## Next Steps

1. **Customize for Your Needs**
   - Edit `AppState.swift` to change check-in intervals
   - Add more apps to `distractingAppsBlockList`

2. **Test Escalation**
   - Let a notification sit for 30+ seconds
   - See how the prompts get more aggressive

3. **Daily Use**
   - Keep monitoring ON during work hours
   - Use Emergency Pause for legitimate breaks
   - Check stats to see distraction patterns

## Need Help?

1. Check the main README.md for detailed docs
2. Look at the Windows version in `/focuscheck` for inspiration
3. Check Apple's documentation:
   - [Screen Time API](https://developer.apple.com/documentation/familycontrols)
   - [Live Activities](https://developer.apple.com/documentation/activitykit)
   - [User Notifications](https://developer.apple.com/documentation/usernotifications)

## Pro Tips

- **Build for Release** when you're done testing:
  - Product → Scheme → Edit Scheme → Run → Build Configuration → Release
  - This improves performance and battery life

- **TestFlight Distribution** if you want to use on multiple devices:
  - Xcode → Product → Archive
  - Upload to App Store Connect
  - Add to TestFlight
  - Install via TestFlight app

- **Backup Your Code**:
  - Initialize git: `git init`
  - Commit regularly: `git add . && git commit -m "message"`

---

**Estimated Total Time:** 30-45 minutes for first-time setup

**You're ready to break free from YouTube hypnosis!** 🎯
