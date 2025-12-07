# Arcade Mode Implementation Plan

**Feature:** Arcade Mode - Timed Chore Challenges with Leaderboards
**Priority:** High
**Status:** Planning Complete - Ready for Implementation
**Last Updated:** 2025-12-06

---

## Executive Summary

Arcade Mode adds an optional timed challenge system to ChoreBoard, allowing users to compete for the fastest completion times on chores. This gamification feature encourages speed and efficiency while maintaining the existing point system.

**Key Features:**
- Optional timed challenges for pool chores
- Per-chore leaderboards with top 3 rankings
- Judge approval system (honor-based, in-person)
- Bonus points for high scores
- User profiles visible in kiosk mode
- Comprehensive arcade statistics

---

## 1. Core Requirements

### 1.1 Applicability
- ✅ **Pool chores only** - Assigned chores use standard completion
- ✅ **All pool chores eligible** - No chore-level arcade toggle needed
- ✅ **Optional participation** - Users can still claim/complete normally

### 1.2 User Options
When clicking a pool chore, users see 3 options:
1. **Claim** - Reserve for later (standard)
2. **Complete** - Direct completion without timing (standard)
3. **Start Arcade** 🎮 - Begin timed challenge (NEW)

### 1.3 Constraints
- ✅ One active arcade chore per user at a time
- ✅ Arcade mode auto-claims the chore to user
- ❌ No helpers allowed in arcade mode (solo challenge)
- ✅ Unlimited retries with cumulative time
- ✅ Timer stored server-side (immune to client manipulation)

---

## 2. Arcade Mode Flow

### 2.1 Starting Arcade Mode

**User Actions:**
1. User clicks pool chore card
2. Dialog shows: [Claim] [Complete] [Start Arcade 🎮]
3. User clicks "Start Arcade"
4. Chore immediately claimed to user
5. Timer starts (visible, counting up)
6. Chore card updates to show arcade status

**System Actions:**
- Create `ArcadeSession` record with `status='active'`
- Set `start_time` to current timestamp
- Link to ChoreInstance
- Display global banner: "🎮 Active Arcade: [Chore Name] - [Timer]"

**UI State:**
```
┌─────────────────────────────────────────────┐
│ 🎮 Active Arcade: Clean Kitchen - 5:23     │
└─────────────────────────────────────────────┘
```

### 2.2 During Arcade Mode

**Timer Display:**
- Format: `MM:SS` for < 1 hour
- Format: `HH:MM:SS` for ≥ 1 hour
- Updates every second (client-side display)
- Persists across browser refresh (server calculates elapsed time)

**User Status:**
- User can see high score on chore card
- User can complete other non-arcade chores
- User cannot start another arcade chore
- Timer continues indefinitely (no max duration)

**Chore Card Appearance:**
```
┌─────────────────────────────────┐
│  🧹 Clean Kitchen               │
│  🎮 ARCADE MODE ACTIVE          │
│  Timer: 5:23                    │
│  Points: 15.00                  │
│                                 │
│  🏆 High Score: Jane - 4:15     │
│                                 │
│  [ Stop Arcade & Submit ]       │
└─────────────────────────────────┘
```

### 2.3 Stopping Arcade Mode

**User Actions:**
1. User clicks active arcade chore card
2. Clicks "Stop Arcade" button
3. Timer stops immediately
4. Final time displayed
5. Judge selection dialog appears

**Judge Selection Dialog:**
```
┌─────────────────────────────────┐
│  🎮 Arcade Mode Complete!       │
│  Time: 5 minutes 23 seconds     │
│                                 │
│  Select Judge:                  │
│  ( ) Jane                       │
│  ( ) Bob                        │
│  ( ) Admin                      │
│  [ ] John (You cannot judge     │
│      yourself)                  │
│                                 │
│  [ Submit for Approval ]        │
│  [ Cancel ]                     │
└─────────────────────────────────┘
```

**System Actions:**
- Update `ArcadeSession.status = 'stopped'`
- Set `ArcadeSession.end_time`
- Calculate `elapsed_seconds`
- Present judge selector (all active users except submitter)
- Create pending `ArcadeCompletion` record

---

## 3. Judge Approval System

### 3.1 Judge Eligibility
- ✅ **Any active user** can be a judge
- ❌ **User who completed** cannot judge themselves
- ✅ **Only 1 judge** can be selected (single-select, not multi)
- ⚠️ **Honor system** - Judge physically present at kiosk with player

### 3.2 Judge Interface

**Judge Selection Flow:**
1. User selects judge from list
2. Clicks "Submit for Approval"
3. System navigates to judge approval screen
4. Judge sees pending approval request

**Judge Approval Screen:**
```
┌─────────────────────────────────────┐
│  🎮 Arcade Approval Request         │
│                                     │
│  Chore: Clean Kitchen               │
│  Completed by: John                 │
│  Time: 5 minutes 23 seconds         │
│                                     │
│  🏆 Current High Score:             │
│     Jane - 4:15                     │
│     (This would be 2nd place)       │
│                                     │
│  Did John complete this chore       │
│  satisfactorily?                    │
│                                     │
│  Notes (optional):                  │
│  [___________________________]      │
│                                     │
│  [ ✅ Approve ]   [ ❌ Deny ]       │
└─────────────────────────────────────┘
```

### 3.3 Approval Outcomes

**If Approved:**
1. `ArcadeCompletion` created with time record
2. Points awarded immediately (base + bonus)
3. High score table updated if applicable
4. Chore marked as completed (ChoreInstance.status = COMPLETED)
5. Success message: "🎮 Arcade mode approved! +[points]pts"
6. Chore removed from board

**If Denied:**
1. User notified: "Judge [Name] denied arcade completion"
2. Options presented:
   - **Continue Arcade** - Resume timer from stopped time
   - **Cancel Arcade** - Return chore to pool
   - **Complete Normally** - Standard completion (no arcade record)

**Continue Arcade (Retry):**
- Same `ArcadeSession` reactivated
- `status` changed back to `active`
- `end_time` cleared
- Timer resumes from previous `elapsed_seconds`
- Cumulative time tracked
- Can retry unlimited times

---

## 4. Leaderboard & High Scores

### 4.1 Leaderboard Scope
- ✅ **Per-chore leaderboards** (each chore has its own)
- ✅ **All-time records** (not time-windowed)
- ✅ **Top 3 rankings** per chore

### 4.2 High Score Display

**On Chore Card (Main Board):**
```
┌─────────────────────────────────┐
│  🧹 Clean Kitchen               │
│  Points: 15.00                  │
│                                 │
│  🏆 High Score: Jane - 4:15     │
│                                 │
│  [ Claim ]  [ Complete ]        │
│  [ Start Arcade 🎮 ]            │
└─────────────────────────────────┘
```
- Only shows **#1 fastest time** on chore card
- Format: "🏆 High Score: [Name] - [Time]"
- If no high score yet: "🏆 No high score yet - Be the first!"

**Arcade Leaderboard Page:**

New page accessible from main navigation: `/board/leaderboard/arcade/`

```
┌─────────────────────────────────────────────────┐
│  🎮 Arcade Leaderboard                          │
│                                                 │
│  🧹 Clean Kitchen                               │
│  🥇 1st: Jane - 4:15 (Dec 3, 2025)             │
│  🥈 2nd: John - 5:23 (Dec 6, 2025)             │
│  🥉 3rd: Bob - 6:07 (Dec 1, 2025)              │
│                                                 │
│  🧺 Laundry                                     │
│  🥇 1st: Bob - 12:45 (Nov 28, 2025)            │
│  🥈 2nd: Jane - 15:02 (Dec 4, 2025)            │
│  🥉 3rd: John - 18:30 (Dec 2, 2025)            │
│                                                 │
│  [Filter by Chore ▼] [Filter by User ▼]        │
└─────────────────────────────────────────────────┘
```

**Features:**
- Shows all chores with arcade completions
- Top 3 times per chore
- Date achieved
- Filterable by chore
- Filterable by user
- Shows medal emoji (🥇🥈🥉)

### 4.3 High Score Updates

When new arcade completion is approved:
1. Check if time beats any current top 3 times for that chore
2. If yes:
   - Insert new record into rankings
   - Shift lower rankings down
   - Remove 4th place if exists
   - Update `ArcadeHighScore` table
   - Set `is_high_score=True` on `ArcadeCompletion`
3. If no:
   - Record completion but not in high scores
   - Set `is_high_score=False`

---

## 5. Points & Rewards

### 5.1 Standard Points
- ✅ **Full chore points** awarded regardless of ranking
- ✅ Points awarded **immediately** upon judge approval
- ✅ Points go into user's point balance instantly

### 5.2 Bonus Points

**Bonus Structure:**
- **+50% bonus** if user beats current #1 high score (new record)
- **+25% bonus** if user gets top 3 (but not new record)
- **No bonus** if outside top 3

**Examples:**
```
Chore: Clean Kitchen (15 points)
Current High Score: Jane - 4:15

Scenario 1: John completes in 4:00 (NEW RECORD)
→ Base: 15 pts
→ Bonus: 15 × 0.50 = 7.5 pts
→ Total: 22.5 pts

Scenario 2: Bob completes in 5:00 (3rd place)
→ Base: 15 pts
→ Bonus: 15 × 0.25 = 3.75 pts
→ Total: 18.75 pts

Scenario 3: Alice completes in 8:00 (outside top 3)
→ Base: 15 pts
→ Bonus: 0 pts
→ Total: 15 pts
```

### 5.3 Failed Attempts
- ❌ **No points** for denied attempts
- ✅ User can retry with cumulative time
- ✅ User can cancel and complete normally for full points

---

## 6. User Profiles in Kiosk Mode

### 6.1 Profile Access
- ✅ **Click username** anywhere it appears (chore cards, leaderboards, etc.)
- ✅ **New "Profiles" link** in main navigation
- ✅ Profile page shows comprehensive user stats

### 6.2 Profile Content

**URL:** `/board/user-profile/<username>/`

**Displayed Information:**
```
┌─────────────────────────────────────────────┐
│  👤 John's Profile                          │
│                                             │
│  📊 Overall Stats                           │
│  • Total Points: 1,245.50                   │
│  • Current Streak: 3 weeks 🔥               │
│  • Chores Completed: 87                     │
│                                             │
│  🎮 Arcade Stats                            │
│  • Arcade Attempts: 15                      │
│  • Arcade Completions: 12 (80% success)    │
│  • High Scores Held: 3 🏆                   │
│  • Total Arcade Points: 234.50              │
│                                             │
│  🏆 Personal Bests                          │
│  🧹 Clean Kitchen - 5:23 (#2)              │
│  🧺 Laundry - 18:30 (#3)                   │
│  🚗 Vacuum Car - 12:15 (#1) 🥇             │
│                                             │
│  📝 Arcade History                          │
│  Dec 6: Clean Kitchen - 5:23 ✅            │
│  Dec 5: Laundry - 18:30 ✅                 │
│  Dec 4: Clean Kitchen - 7:45 ❌ (denied)   │
│  Dec 3: Vacuum Car - 12:15 ✅ (NEW RECORD!)│
│                                             │
│  [View Full History]                        │
└─────────────────────────────────────────────┘
```

**Included Data:**
- ✅ Total points
- ✅ Current streak
- ✅ Total chores completed
- ✅ Arcade attempts (total started)
- ✅ Arcade completions (approved)
- ✅ Success rate percentage
- ✅ Number of high scores held
- ✅ Personal best times per chore
- ✅ Arcade history (all attempts with outcomes)
- ❌ NOT included: Standard completion history (only arcade)

---

## 7. Integration with Existing Features

### 7.1 Helper Selection
- ❌ **Arcade mode chores CANNOT have helpers** (solo challenge)
- ✅ If user wants helpers, must use standard "Complete"
- ✅ Helper dialog not shown for arcade completions

### 7.2 Skip/Reschedule
**If Admin Skips Chore:**
- Active arcade timer cancelled
- `ArcadeSession.status = 'cancelled'`
- User notified: "Arcade mode cancelled - chore was skipped"
- No points awarded
- Chore removed from board

**If Admin Reschedules Chore:**
- Active timer cancelled
- User can start arcade on new instance
- Previous arcade session remains in history

### 7.3 Overdue Chores
- ✅ **Arcade mode ALLOWED on overdue chores**
- ✅ Users can still compete for high scores even if late
- ⚠️ Chore marked overdue, but arcade timer continues
- ✅ Points still awarded (may affect weekly reset perfect week status)

### 7.4 Standard Completion During Arcade
If user starts arcade but then clicks "Complete" from assigned chores:
- Timer stops and discarded
- `ArcadeSession.status = 'cancelled'`
- Standard completion flow proceeds
- Full points awarded (no bonus)
- No judge needed
- No leaderboard entry

### 7.5 Weekly Reset
- Arcade completions count as regular completions
- Affects perfect week status (if overdue)
- Points already awarded (not pending)
- High scores persist across weeks

---

## 8. Technical Specification

### 8.1 Data Models

#### ArcadeSession
```python
class ArcadeSession(models.Model):
    """Tracks active and completed arcade mode attempts."""

    STATUS_ACTIVE = 'active'
    STATUS_STOPPED = 'stopped'
    STATUS_APPROVED = 'approved'
    STATUS_DENIED = 'denied'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_STOPPED, 'Stopped - Awaiting Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DENIED, 'Denied'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='arcade_sessions')
    chore_instance = models.ForeignKey(ChoreInstance, on_delete=models.CASCADE, related_name='arcade_sessions')
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='arcade_sessions')  # Denormalized for queries

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.IntegerField(default=0)  # Calculated field

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_active = models.BooleanField(default=True)  # Quick lookup for active sessions

    # Retry tracking
    attempt_number = models.IntegerField(default=1)  # 1st attempt, 2nd attempt, etc.
    cumulative_seconds = models.IntegerField(default=0)  # Total time across all retries

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arcade_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['status']),
            models.Index(fields=['chore']),
        ]

    def get_elapsed_time(self):
        """Calculate elapsed time based on start/end times."""
        if self.end_time:
            delta = self.end_time - self.start_time
        else:
            delta = timezone.now() - self.start_time
        return int(delta.total_seconds())

    def format_time(self):
        """Format elapsed time as HH:MM:SS or MM:SS."""
        seconds = self.elapsed_seconds if self.elapsed_seconds else self.get_elapsed_time()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
```

#### ArcadeCompletion
```python
class ArcadeCompletion(models.Model):
    """Records approved arcade mode completions."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='arcade_completions')
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='arcade_completions')
    arcade_session = models.OneToOneField(ArcadeSession, on_delete=models.CASCADE, related_name='completion')
    chore_instance = models.ForeignKey(ChoreInstance, on_delete=models.CASCADE, related_name='arcade_completion')

    completion_time_seconds = models.IntegerField()
    judge = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='judged_arcades')
    approved = models.BooleanField(default=True)  # Always true for this model (denials don't create records)
    judge_notes = models.TextField(blank=True, default='')

    # Points
    base_points = models.DecimalField(max_digits=5, decimal_places=2)
    bonus_points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_points = models.DecimalField(max_digits=5, decimal_places=2)

    # High score status at time of completion
    is_high_score = models.BooleanField(default=False)
    rank_at_completion = models.IntegerField(null=True, blank=True)  # 1, 2, 3, or None

    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arcade_completions'
        indexes = [
            models.Index(fields=['user', 'chore']),
            models.Index(fields=['chore', 'completion_time_seconds']),
            models.Index(fields=['is_high_score']),
        ]
        ordering = ['completion_time_seconds']  # Fastest first

    def format_time(self):
        """Format completion time as HH:MM:SS or MM:SS."""
        seconds = self.completion_time_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
```

#### ArcadeHighScore
```python
class ArcadeHighScore(models.Model):
    """Maintains top 3 high scores per chore."""

    RANK_CHOICES = [
        (1, '1st Place'),
        (2, '2nd Place'),
        (3, '3rd Place'),
    ]

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name='high_scores')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='high_scores')
    arcade_completion = models.ForeignKey(ArcadeCompletion, on_delete=models.CASCADE, related_name='high_score_entry')

    time_seconds = models.IntegerField()
    rank = models.IntegerField(choices=RANK_CHOICES)
    achieved_at = models.DateTimeField()

    class Meta:
        db_table = 'arcade_high_scores'
        unique_together = ['chore', 'rank']  # Only one record per rank per chore
        indexes = [
            models.Index(fields=['chore', 'rank']),
            models.Index(fields=['user']),
        ]
        ordering = ['chore', 'rank']

    def format_time(self):
        """Format time as HH:MM:SS or MM:SS."""
        seconds = self.time_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
```

### 8.2 API Endpoints

**Arcade Session Management:**
- `POST /board/action/arcade/start/` - Start arcade mode
- `POST /board/action/arcade/stop/` - Stop arcade timer
- `POST /board/action/arcade/cancel/` - Cancel arcade mode
- `GET /board/action/arcade/status/` - Get active session status

**Judge Approval:**
- `GET /board/arcade/pending-approvals/` - List pending approvals
- `POST /board/arcade/approve/<session_id>/` - Approve arcade completion
- `POST /board/arcade/deny/<session_id>/` - Deny arcade completion

**Leaderboard & Stats:**
- `GET /board/leaderboard/arcade/` - Arcade leaderboard page
- `GET /board/api/arcade/high-scores/<chore_id>/` - Get top 3 for specific chore
- `GET /board/user-profile/<username>/` - User profile page
- `GET /board/api/arcade/user-stats/<user_id>/` - Get user's arcade stats

**Admin:**
- `GET /board/admin-panel/arcade/sessions/` - List all arcade sessions
- `POST /board/admin-panel/arcade/cancel/<session_id>/` - Admin cancel session
- `POST /board/admin-panel/arcade/force-approve/<session_id>/` - Force approve

### 8.3 Database Migrations

**Migration 1: Create Arcade Models**
```bash
python manage.py makemigrations
python manage.py migrate
```

Creates:
- `arcade_sessions` table
- `arcade_completions` table
- `arcade_high_scores` table
- Indexes and foreign keys

### 8.4 Business Logic Services

**ArcadeService (chores/services/arcade.py):**
```python
class ArcadeService:
    @staticmethod
    def start_arcade(user, chore_instance):
        """Start arcade mode for a user on a chore instance."""

    @staticmethod
    def stop_arcade(arcade_session):
        """Stop arcade timer and prepare for judge approval."""

    @staticmethod
    def approve_arcade(arcade_session, judge, notes=''):
        """Judge approves arcade completion, award points, update leaderboard."""

    @staticmethod
    def deny_arcade(arcade_session, judge, notes=''):
        """Judge denies arcade completion, offer retry."""

    @staticmethod
    def continue_arcade(arcade_session):
        """Resume arcade timer after denial."""

    @staticmethod
    def cancel_arcade(arcade_session):
        """Cancel arcade mode, return chore to pool."""

    @staticmethod
    def update_high_scores(arcade_completion):
        """Update leaderboard after new completion."""

    @staticmethod
    def calculate_bonus_points(arcade_completion):
        """Calculate bonus points based on ranking."""
```

---

## 9. UI/UX Implementation

### 9.1 Chore Card Updates

**Pool Chore Dialog (main.html):**

Update the existing pool chore click dialog to add "Start Arcade" button:

```html
<!-- In the pool chore action dialog -->
<div class="flex flex-col space-y-3">
    <button onclick="claimChore({{ instance.id }})"
            class="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg">
        Claim
    </button>

    <button onclick="completeChore({{ instance.id }})"
            class="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg">
        Complete
    </button>

    <button onclick="startArcade({{ instance.id }})"
            class="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-3 px-6 rounded-lg">
        🎮 Start Arcade
    </button>
</div>
```

**Active Arcade Banner:**

Add to top of page (above main content):

```html
{% if active_arcade_session %}
<div class="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-4 mb-6 rounded-lg shadow-lg">
    <div class="flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <span class="text-2xl">🎮</span>
            <div>
                <p class="font-bold text-lg">Active Arcade: {{ active_arcade_session.chore.name }}</p>
                <p class="text-sm opacity-90">Timer: <span id="arcade-timer" class="font-mono">00:00</span></p>
            </div>
        </div>
        <button onclick="openArcadeChore({{ active_arcade_session.chore_instance.id }})"
                class="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition">
            View Chore
        </button>
    </div>
</div>
{% endif %}
```

**Chore Card with High Score:**

```html
<div class="chore-card">
    <h3>{{ instance.chore.name }}</h3>
    <p>Points: {{ instance.points_value }}</p>

    {% if high_score %}
    <div class="high-score-badge">
        🏆 High Score: {{ high_score.user.get_display_name }} - {{ high_score.format_time }}
    </div>
    {% endif %}

    <!-- Action buttons -->
</div>
```

### 9.2 Judge Approval Interface

**New Page: templates/board/arcade/judge_approval.html**

Shows pending arcade approvals with approve/deny buttons.

### 9.3 Arcade Leaderboard Page

**New Page: templates/board/arcade/leaderboard.html**

Shows all chores with top 3 times, filterable by chore and user.

### 9.4 User Profile Page

**New Page: templates/board/user_profile.html**

Shows user stats, arcade history, personal bests.

### 9.5 Navigation Updates

Add to main navigation:
- "🎮 Arcade Leaderboard" link
- "👤 Profiles" link

---

## 10. Implementation Phases

### Phase 1: Core Arcade Mode (MVP)
**Estimated Effort:** 8-10 hours

**Tasks:**
- [ ] Create data models (ArcadeSession, ArcadeCompletion, ArcadeHighScore)
- [ ] Write database migrations
- [ ] Create ArcadeService with core business logic
- [ ] Add "Start Arcade" button to pool chore dialog
- [ ] Implement start_arcade endpoint and view
- [ ] Implement stop_arcade endpoint
- [ ] Build judge selection dialog
- [ ] Implement arcade timer display (JavaScript)
- [ ] Add active arcade banner
- [ ] Create judge approval interface
- [ ] Implement approve/deny endpoints
- [ ] Test basic arcade flow end-to-end

**Success Criteria:**
- User can start arcade mode
- Timer displays and updates
- User can stop and select judge
- Judge can approve/deny
- Points awarded on approval

### Phase 2: Leaderboard & High Scores
**Estimated Effort:** 4-6 hours

**Tasks:**
- [ ] Implement high score calculation logic
- [ ] Build arcade leaderboard page
- [ ] Display high score on chore cards
- [ ] Add bonus points calculation
- [ ] Update high scores table on completion
- [ ] Add rank badges (🥇🥈🥉)
- [ ] Implement leaderboard filters
- [ ] Test high score updates

**Success Criteria:**
- High scores display correctly
- Leaderboard shows top 3
- Bonus points awarded correctly
- Rankings update properly

### Phase 3: User Profiles
**Estimated Effort:** 3-4 hours

**Tasks:**
- [ ] Create user profile page
- [ ] Display overall stats
- [ ] Display arcade stats
- [ ] Show personal bests
- [ ] Show arcade history
- [ ] Add profile links throughout UI
- [ ] Add "Profiles" to navigation
- [ ] Test profile accuracy

**Success Criteria:**
- Profiles accessible in kiosk mode
- Stats display correctly
- History shows all attempts

### Phase 4: Retry & Edge Cases
**Estimated Effort:** 3-4 hours

**Tasks:**
- [ ] Implement continue_arcade logic
- [ ] Handle cumulative time tracking
- [ ] Implement cancel_arcade
- [ ] Handle standard completion during arcade
- [ ] Handle admin skip during arcade
- [ ] Handle admin reschedule during arcade
- [ ] Test all edge cases
- [ ] Add error handling

**Success Criteria:**
- Retries work with cumulative time
- Cancellation returns chore to pool
- Edge cases handled gracefully

### Phase 5: Admin Tools
**Estimated Effort:** 2-3 hours

**Tasks:**
- [ ] Add arcade management section to admin panel
- [ ] Show all active arcade sessions
- [ ] Add admin cancel button
- [ ] Add admin force approve
- [ ] Add arcade session logs
- [ ] Test admin tools

**Success Criteria:**
- Admins can view all sessions
- Admins can intervene when needed

### Phase 6: Polish & Testing
**Estimated Effort:** 2-3 hours

**Tasks:**
- [ ] Add loading states
- [ ] Add error messages
- [ ] Improve mobile responsiveness
- [ ] Add animations/transitions
- [ ] Write comprehensive tests
- [ ] User acceptance testing
- [ ] Bug fixes

**Success Criteria:**
- Smooth user experience
- No critical bugs
- Mobile-friendly

---

## 11. Testing Requirements

### 11.1 Unit Tests

**Test ArcadeSession Model:**
- Test get_elapsed_time() calculation
- Test format_time() for various durations
- Test status transitions

**Test ArcadeService:**
- Test start_arcade creates session correctly
- Test stop_arcade calculates elapsed time
- Test approve_arcade awards points correctly
- Test deny_arcade doesn't award points
- Test continue_arcade resumes timer
- Test update_high_scores logic
- Test calculate_bonus_points (50%, 25%, 0%)

### 11.2 Integration Tests

**Test Arcade Flow:**
- User starts arcade → session created, chore claimed
- Timer runs → elapsed time updates
- User stops → session stopped, judge selection shown
- Judge approves → points awarded, high score updated
- Judge denies → retry offered, cumulative time tracked

**Test Leaderboard:**
- New record displaces old #1
- Rankings shift correctly
- Top 3 maintained
- Bonus points calculated correctly

**Test Edge Cases:**
- User cancels arcade → chore returns to pool
- Admin skips during arcade → session cancelled
- Standard complete during arcade → session cancelled
- Multiple retries → cumulative time accurate
- Browser refresh → timer persists

### 11.3 UI Tests

**Test User Experience:**
- Arcade banner displays for active sessions
- Timer updates every second
- Judge selection shows correct users
- High scores display on chore cards
- Leaderboard page loads correctly
- User profile shows accurate stats

---

## 12. Rollout Plan

### 12.1 Development
1. Create feature branch: `feature/arcade-mode`
2. Implement Phase 1 (MVP)
3. Test locally
4. Commit and push

### 12.2 Testing
1. Deploy to staging environment
2. User acceptance testing
3. Gather feedback
4. Iterate on improvements

### 12.3 Production
1. Merge to main branch
2. Run migrations
3. Deploy to production
4. Monitor for issues
5. Announce feature to users

### 12.4 Documentation
1. Update user guide with arcade mode instructions
2. Update README with new features
3. Add arcade mode to feature list
4. Create video tutorial (optional)

---

## 13. Future Enhancements

**Not in MVP, but consider for future versions:**

1. **Arcade Tournaments**
   - Weekly/monthly arcade challenges
   - Special event chores
   - Tournament brackets

2. **Achievements**
   - "Speed Demon" - Beat 10 high scores
   - "Perfectionist" - 100% approval rate
   - "Competitor" - Complete 50 arcade chores

3. **Social Features**
   - Challenge other users to beat your time
   - Share high scores
   - Arcade mode notifications

4. **Advanced Stats**
   - Average time per chore
   - Improvement trends
   - Head-to-head comparisons

5. **Difficulty Multipliers**
   - Harder chores get higher bonuses
   - Seasonal multipliers (holidays)

6. **Team Arcade**
   - Multiple users work together
   - Relay-style challenges
   - Team leaderboards

---

## 14. Open Questions & Decisions

### Resolved:
✅ Bonus points: 50% for new record, 25% for top 3
✅ Leaderboard: Top 3 per chore
✅ Judge consensus: Only 1 judge needed
✅ Timer visibility: Visible to user
✅ Profile content: Stats + points + streak, no completion history
✅ Judge notification: Honor system, in-person
✅ Active arcade indicator: Global banner
✅ Leaderboard access: Main navigation
✅ Long duration: Show hours (HH:MM:SS)
✅ Point awarding: Immediate
✅ Overdue chores: Arcade allowed
✅ Multiple attempts: Same instance

### Pending:
None - All requirements finalized!

---

## 15. Conclusion

This implementation plan provides a comprehensive roadmap for building Arcade Mode. The feature is well-defined with clear requirements, technical specifications, and phased implementation approach.

**Next Steps:**
1. Review and approve this plan
2. Create GitHub issues for each phase
3. Begin Phase 1 implementation
4. Iterate based on testing feedback

**Estimated Total Effort:** 22-30 hours across all phases

**Target Completion:** [To be determined based on team availability]

---

**Document Status:** ✅ Complete - Ready for Implementation
**Last Updated:** 2025-12-06
**Author:** Development Team
**Approved By:** [Pending User Approval]
