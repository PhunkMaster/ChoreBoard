# ChoreBoard User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Viewing the Board](#viewing-the-board)
3. [Claiming Chores](#claiming-chores)
4. [Completing Chores](#completing-chores)
5. [Viewing Points](#viewing-points)
6. [Pool vs Assigned Chores](#pool-vs-assigned-chores)
7. [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### Accessing ChoreBoard

1. **Open your web browser** and navigate to your ChoreBoard URL (e.g., `http://localhost:8000` or your deployed URL)
2. **Main Board**: Navigate to `/` to see all chores
3. **Your Personal View**: Navigate to `/user/<your-username>` to see only your chores
4. **Pool View**: Navigate to `/pool/` to see kiosk mode with only pool chores
5. **Leaderboard**: Navigate to `/leaderboard/` to see rankings

### Understanding the Dashboard

The main board shows:
- **Stats Cards**: Quick summary of your points (weekly and all-time)
- **Pool Chores**: Unclaimed chores anyone can take
- **Your Assigned Chores**: Chores specifically assigned to you
- **Other Users' Chores**: Chores assigned to other family members

---

## Viewing the Board

### Color-Coded Status

Chores are color-coded based on their status:

- **🟢 Green**: Completed chores (on time)
- **🟡 Amber**: Due today, not yet complete
- **🔴 Red**: Overdue chores (past due date, not completed)
- **🟣 Purple**: Assignment blocked (no eligible users, or all eligible users completed yesterday)

### Chore Information

Each chore card displays:
- **Chore Name**: What needs to be done
- **Points Value**: How many points you'll earn (or custom label like "stars", "coins")
- **Due Date**: When the chore is due
- **Status**: Current state (Pool, Assigned, Completed)
- **Assigned To**: Who is responsible (for assigned chores)

---

## Claiming Chores

### What is Claiming?

Claiming a chore reserves it for you, preventing others from taking it. You can claim chores from the **Pool** section.

### How to Claim a Chore

1. **Find a pool chore** you want to complete
2. **Click the "Claim" button** on the chore card
3. **Confirm** in the dialog that appears
4. The chore moves from Pool to your Assigned section

### Claim Limits

- By default, you can claim **1 chore per day**
- This limit resets at midnight
- Admins can adjust this limit in settings
- You cannot claim more chores once you've reached your daily limit

### Unclaiming a Chore

If you claimed a chore by mistake:
1. **Click the "Unclaim" button** on the chore card (only available on your claimed chores)
2. **Confirm** the action
3. The chore returns to the Pool
4. Your daily claim counter is decremented (you get your claim back!)

---

## Completing Chores

### Completing Your Own Chores

1. **Find the chore** in your Assigned section
2. **Click the "Complete" button**
3. **Select helpers** (optional):
   - Check boxes for any users who helped you
   - Points will be split evenly among you and helpers
   - If you select 2 helpers, each person gets 1/3 of the points
4. **Click "Complete"** to finish
5. The chore disappears from your list and points are awarded

### Completing Pool Chores Directly

You don't have to claim first! You can complete pool chores directly:

1. **Find a pool chore**
2. **Click "Complete"** (skip the claim step)
3. **Select yourself** as the completer
4. **Add helpers** if applicable
5. **Confirm** to complete

This is great for quick chores or when working together as a family.

### Point Splitting

When you add helpers:
- Points are **split evenly** among all participants
- Example: 10-point chore with 2 helpers = 3.33 points each
- Rounding may cause small losses (3.33 + 3.33 + 3.34 = 10.00)
- All participants get credit in their points history

---

## Viewing Points

### Stats Cards

At the top of the board, you'll see:
- **Weekly Points**: Points earned this week (resets Sunday midnight)
- **All-Time Points**: Total points earned ever
- **Current Rank**: Your position on the leaderboard

### Leaderboard

Navigate to `/leaderboard/` to see:

**Weekly Tab:**
- Points earned this week only
- 🥇 Gold medal for 1st place
- 🥈 Silver medal for 2nd place
- 🥉 Bronze medal for 3rd place

**All-Time Tab:**
- Total points earned since you started
- Same medal system for top 3 users

### Points History

Visit your personal page (`/user/<your-username>`) to see:
- Recent chore completions
- Points earned for each chore
- Chores shared with helpers
- Your perfect week streak (complete all chores on time!)

---

## Pool vs Assigned Chores

### Pool Chores

**What are they?**
- Unclaimed chores available to anyone
- First person to claim gets the chore
- Can be completed without claiming

**When to use:**
- Chores that don't require a specific person
- Flexible tasks that anyone can do
- Quick tasks you want to complete immediately

**How they work:**
1. Admin creates a pool chore
2. Chore appears in Pool section at midnight (or immediately when created)
3. Anyone can claim or complete
4. At 5:30 PM, system may auto-assign if still in pool

### Assigned Chores

**What are they?**
- Chores specifically assigned to you
- Only you can complete them (unless admin reassigns)
- Automatically assigned by the system or manually by admin

**When assigned:**
- Rotation chores (system picks fairly)
- Specific chores created with your name
- Auto-assigned from pool at 5:30 PM distribution time

**Your responsibility:**
- Complete all assigned chores by their due date
- Complete them on time to maintain your perfect week streak
- If you can't complete, ask admin to reassign

---

## Tips and Best Practices

### Maximize Your Points

1. **Complete chores on time**: Avoid red overdue status
2. **Claim early**: Get first pick of pool chores
3. **Check daily**: New chores appear at midnight
4. **Perfect weeks**: Complete ALL chores on time for streak bonuses

### Family Teamwork

1. **Add helpers**: Share credit when working together
2. **Communicate**: Let others know if you need help
3. **Fair claiming**: Don't hog all the high-point chores
4. **Help overdue**: Assist family members who have red chores

### Mobile Tips

1. **Bookmark** your personal page for quick access
2. **Refresh** the page to see real-time updates
3. **Portrait mode** works best on phones
4. **Landscape mode** works best on tablets

### Chore Notifications

If your admin has configured notifications:
- You may receive reminders for overdue chores
- Check your notification method (email, Home Assistant, etc.)
- Ask admin to adjust notification frequency if needed

### Understanding Due Dates

- **Due Today**: Shown in amber, complete before midnight
- **Overdue**: Shown in red, complete ASAP to avoid losing streak
- **Not Due Yet**: Future chores (if admin configured them)

### Perfect Week Streaks

**What is it?**
- Complete ALL your assigned chores ON TIME for an entire week
- Week runs Sunday midnight to Sunday midnight
- Tracked in your user profile

**Benefits:**
- Visible streak counter on your profile
- Bragging rights in your household
- May unlock special bonuses (ask your admin!)

**How to maintain:**
- Check board every day
- Complete chores by their due date (not after)
- Don't let any chore turn red

---

## Kiosk Mode & Minimal Pages

ChoreBoard includes **minimal pages** designed for kiosk displays, tablets, or dedicated chore stations. These pages remove navigation, headers, and extra chrome for a clean, focused interface.

### Why Use Minimal Pages?

- **Kiosk Stations**: Set up a dedicated tablet or screen for family members to check and complete chores
- **Embedded Displays**: Use in iframes, dashboards, or home automation interfaces
- **Simplified Interface**: Remove distractions and show only essential information
- **Auto-Refresh**: Pages automatically reload to show updated information
- **No Login Required**: Work without authentication for household use

### Available Minimal Pages

All minimal pages auto-refresh every 30-60 seconds to show the latest chore status.

#### 1. Pool Chores Minimal
**URL**: `/pool/minimal/`

**What it shows:**
- All unclaimed pool chores
- Arcade mode banner (if active)
- Claim and Complete buttons for each chore
- High score display for arcade-enabled chores

**Use case:**
- Kitchen tablet showing available chores
- Quick-claim station in common areas

**Features:**
- Responsive grid (1-4 columns based on screen size)
- User selection dialogs for claiming/completing
- Helper selection for shared completions

---

#### 2. User Board Minimal
**URL**: `/user/<username>/minimal/`

**What it shows:**
- Single user's assigned chores for today
- Overdue chores (red)
- On-time chores (blue)
- Arcade mode banner for that user

**Use case:**
- Personal tablet in bedroom showing only your chores
- Kids' room display with just their tasks

**Features:**
- Clean card layout
- Complete button on each chore
- Auto-refresh to track progress

---

#### 3. Assigned Chores Minimal
**URL**: `/assigned/minimal/`

**What it shows:**
- All users with their assigned chores
- Grouped by user in separate sections
- Each user's chore count
- Complete button per chore

**Use case:**
- Family room display showing everyone's status
- Central hub for viewing all household chores

**Features:**
- Responsive grid (1-4 columns per user section)
- Pre-selects assigned user in complete dialog
- Shows overdue vs on-time breakdown

---

#### 4. Users Overview Minimal
**URL**: `/users/minimal/`

**What it shows:**
- Grid of all user cards
- Each card displays:
  - User name
  - Chore count for today
  - Weekly points
  - All-time points

**Use case:**
- Quick overview of household status
- Points tracking display
- Navigation hub to user boards

**Features:**
- Responsive grid (2-6 columns based on screen size)
- Clickable cards navigate to user's minimal board
- Color-coded badges for chore counts

---

#### 5. Leaderboard Minimal
**URL**: `/leaderboard/minimal/`

**What it shows:**
- Ranked list of users by points
- Toggle between Weekly and All-Time
- Top 3 with medal emojis (🥇🥈🥉)
- Points for each user

**Use case:**
- Motivational display in common area
- Competition tracker for families
- Weekly standings board

**Features:**
- Gold/silver/bronze visual highlights
- Large, readable font sizes
- Auto-refresh to show live standings

---

#### 6. Arcade Leaderboard Minimal
**URL**: `/arcade/leaderboard/minimal/`

**What it shows:**
- Time records for arcade-enabled chores
- Top 3 times per chore
- User names and completion dates
- Completion times

**Use case:**
- Speed challenge display
- Record board for competitive chores
- Achievement showcase

**Features:**
- Grouped by chore type
- Medal emojis for top performers
- Live timer displays
- Shows all arcade records

---

#### 7. Judge Approval Minimal
**URL**: `/arcade/judge-approval/minimal/`

**What it shows:**
- Pending arcade completions awaiting approval
- Completion times and user info
- Current high score comparison
- "NEW RECORD!" indicators
- Approve/Deny buttons

**Use case:**
- Judge station for arcade mode
- Review screen for completed speed challenges
- Parent approval interface

**Features:**
- Large, clear action buttons
- Judge selection in approval dialog
- Optional notes for approval/denial
- Shows if submission beats current record
- Faster refresh (30 seconds)

---

### Setting Up a Kiosk Station

**Recommended Setup:**

1. **Hardware:**
   - Tablet (iPad, Android, Fire) mounted on wall or stand
   - Old phone or small touchscreen
   - Dedicated monitor with Raspberry Pi

2. **Browser Setup:**
   - Use kiosk mode browser or full-screen mode
   - Disable sleep/screen timeout
   - Enable auto-reload (pages already auto-refresh)
   - Bookmark your preferred minimal page

3. **Suggested Page Choices:**
   - **Kitchen/Common Area**: `/assigned/minimal/` or `/pool/minimal/`
   - **Personal Bedrooms**: `/user/<username>/minimal/`
   - **Family Leaderboard**: `/leaderboard/minimal/`
   - **Arcade Judge**: `/arcade/judge-approval/minimal/`

4. **Tips:**
   - Use portrait orientation for user boards
   - Use landscape orientation for pool/assigned views
   - Adjust tablet brightness for visibility
   - Consider using tablet stands with adjustable angles

5. **Embedding in Other Apps:**
   - ChoreBoard supports iframe embedding for dashboards and home automation interfaces
   - Works with Home Assistant, SmartThings, and custom web dashboards
   - Example iframe code:
     ```html
     <iframe src="http://yourserver:8000/pool/minimal/"
             width="100%" height="800px"
             frameborder="0"></iframe>
     ```
   - All minimal pages are optimized for iframe embedding

---

### Minimal Pages vs Regular Pages

| Feature | Regular Pages | Minimal Pages |
|---------|---------------|---------------|
| Navigation Menu | ✅ Yes | ❌ No |
| Header/Logo | ✅ Yes | ❌ No |
| Back Buttons | ✅ Yes | ❌ No |
| Auto-Refresh | ❌ No | ✅ Yes (30-60s) |
| Arcade Banner | ✅ Yes | ✅ Yes |
| Login Required | ✅ Yes | ❌ No |
| Responsive | ✅ Yes | ✅ Yes |
| Touch Friendly | ✅ Yes | ✅ Yes |

---

### Browser Recommendations for Kiosk

**iOS (iPad/iPhone):**
- Safari in Guided Access mode (Settings → Accessibility)
- Kiosk Pro app for advanced kiosk features

**Android:**
- Chrome with "Add to Home Screen" and full-screen
- Fully Kiosk Browser app (recommended)
- Kiosk Browser Lockdown

**Fire Tablet:**
- Silk Browser in full-screen mode
- Enable Show Mode for hands-free display

**Raspberry Pi:**
- Chromium in kiosk mode
- `chromium-browser --kiosk --app=http://yourserver/pool/minimal/`

---

## Common Questions

**Q: Why can't I claim more chores?**
A: You've reached your daily claim limit (default: 1). Wait until midnight for it to reset.

**Q: Can I unclaim a chore?**
A: Yes! Click the "Unclaim" button on any chore you claimed (before completing it).

**Q: What happens if I don't complete my chore?**
A: It turns red (overdue), breaks your perfect week streak, and may be reassigned by admin.

**Q: Can I complete someone else's assigned chore?**
A: No, only the assigned person can complete it. Ask admin to reassign if needed.

**Q: How are points split with helpers?**
A: Evenly! A 10-point chore with 3 people = 3.33 points each (rounding may vary).

**Q: When do I get paid for my points?**
A: That's up to your admin! Weekly snapshots are created Sunday midnight for conversion.

**Q: What if I accidentally completed the wrong chore?**
A: Contact your admin immediately. They can undo completions within 24 hours.

**Q: Why is a chore purple?**
A: Purple means assignment is blocked (no eligible users, or rotation restrictions).

---

## Keyboard Shortcuts

- **Tab**: Navigate between buttons and chores
- **Enter**: Activate buttons and links
- **Escape**: Close dialogs
- **Shift + Tab**: Navigate backward

---

## Accessibility

ChoreBoard is designed to be accessible:
- **Screen reader compatible**: All elements properly labeled
- **Keyboard navigation**: Full keyboard support
- **Skip links**: Jump to main content
- **Focus indicators**: Clear visual focus states
- **Color contrast**: WCAG 2.1 Level AA compliant

---

## Need Help?

- **Admin Issues**: Contact your household admin for chore assignments, point adjustments, or undo requests
- **Technical Issues**: Check the planning documentation or GitHub issues
- **Feature Requests**: Ask your admin to submit feature requests

---

**Happy Choring! 🎉**
