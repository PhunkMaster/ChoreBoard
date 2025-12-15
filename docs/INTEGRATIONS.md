# ChoreBoard Integrations

ChoreBoard can be integrated with other systems to extend its functionality and bring chore management into your existing smart home ecosystem.

---

## 🏠 Home Assistant Integration

ChoreBoard offers first-class integration with Home Assistant, allowing you to view and manage chores directly from your Home Assistant dashboard.

### ChoreBoard Home Assistant Integration

**Repository:** [ChoreBoard-HA-Integration](https://github.com/PhunkMaster/ChoreBoard-HA-Integration)

The official Home Assistant integration for ChoreBoard provides:

#### Features

- **Real-time Chore Display** - View all active chores in Home Assistant
- **Sensor Entities** - Individual sensors for each chore with detailed attributes
- **Status Tracking** - Monitor chore status, due dates, and point values
- **User Integration** - See assigned users and track completions
- **Automatic Updates** - Real-time synchronization with your ChoreBoard instance
- **Multiple Instances** - Support for multiple ChoreBoard servers

#### Installation

1. **Install via HACS (Recommended)**
   - Add `https://github.com/PhunkMaster/ChoreBoard-HA-Integration` as a custom repository
   - Search for "ChoreBoard" in HACS
   - Install the integration
   - Restart Home Assistant

2. **Manual Installation**
   - Download the integration from GitHub
   - Copy to `custom_components/choreboard/`
   - Restart Home Assistant

3. **Configuration**
   - Go to Settings → Devices & Services
   - Click "+ Add Integration"
   - Search for "ChoreBoard"
   - Enter your ChoreBoard URL and API key

#### API Key Setup

To connect Home Assistant to ChoreBoard:

1. Log into ChoreBoard as admin
2. Go to Admin Panel → Settings
3. Find your API Key or generate a new one
4. Copy the API key to use in Home Assistant configuration

#### Available Entities

The integration creates the following entities:

- **Chore Sensors** - One sensor per active chore
  - Attributes: due date, status, points, assigned user, description
  - States: pool, assigned, overdue, completed
- **User Sensors** - Points and streak tracking per user
- **Summary Sensors** - Overall household statistics

---

## 📱 ChoreBoard Home Assistant Card

**Repository:** [ChoreBoard-HA-Card](https://github.com/PhunkMaster/ChoreBoard-HA-Card)

A beautiful custom Lovelace card for displaying ChoreBoard chores in your Home Assistant dashboard.

### Features

- **Beautiful UI** - Clean, modern design that matches Home Assistant's aesthetic
- **Color-coded Status** - Visual indicators for on-time, getting late, and overdue chores
- **Detailed Information** - View points, due dates, and assigned users at a glance
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Customizable** - Configure colors, layout, and displayed information
- **Real-time Updates** - Automatically updates when chores change

### Installation

1. **Install via HACS (Recommended)**
   - Open HACS in Home Assistant
   - Go to "Frontend"
   - Click the menu and select "Custom repositories"
   - Add `https://github.com/PhunkMaster/ChoreBoard-HA-Card`
   - Install "ChoreBoard Card"
   - Refresh your browser

2. **Manual Installation**
   - Download `choreboard-card.js` from the GitHub releases
   - Copy to `www/community/choreboard-card/`
   - Add the resource in Lovelace configuration
   - Refresh your browser

### Basic Configuration

Add the card to your Lovelace dashboard:

```yaml
type: custom:choreboard-card
entity: sensor.choreboard_chores
title: Household Chores
show_points: true
show_due_date: true
color_by_status: true
```

### Advanced Configuration

Customize the card to match your needs:

```yaml
type: custom:choreboard-card
entity: sensor.choreboard_chores
title: Today's Chores
show_points: true
show_due_date: true
show_assigned_user: true
color_by_status: true
filter:
  status:
    - pool
    - assigned
sort_by: due_date
max_chores: 10
colors:
  on_time: "#4caf50"
  getting_late: "#ff9800"
  overdue: "#f44336"
```

### Card Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **Required** | Entity ID of the ChoreBoard sensor |
| `title` | string | "Chores" | Card title |
| `show_points` | boolean | true | Show point values |
| `show_due_date` | boolean | true | Show due dates |
| `show_assigned_user` | boolean | true | Show assigned user |
| `color_by_status` | boolean | true | Color-code by status |
| `filter.status` | array | all | Filter by status (pool, assigned, overdue) |
| `sort_by` | string | "due_date" | Sort order (due_date, points, status) |
| `max_chores` | number | unlimited | Maximum chores to display |

---

## 🔗 Webhook Notifications

ChoreBoard can send webhook notifications to Home Assistant or other systems for real-time updates.

### Setup Webhook in ChoreBoard

1. **Configure in Admin Panel**
   - Go to Admin Panel → Settings
   - Find "Webhook URL" setting
   - Enter your Home Assistant webhook URL
   - Save settings

2. **Home Assistant Webhook URL Format**
   ```
   https://your-homeassistant.com/api/webhook/choreboard_webhook_id
   ```

3. **Create Webhook Automation in Home Assistant**
   ```yaml
   automation:
     - alias: "ChoreBoard Notification"
       trigger:
         platform: webhook
         webhook_id: choreboard_webhook_id
       action:
         service: notify.mobile_app
         data:
           title: "ChoreBoard Update"
           message: "{{ trigger.json.message }}"
   ```

### Webhook Events

ChoreBoard sends webhooks for the following events:

- **chore_completed** - When a chore is marked complete
- **chore_claimed** - When a user claims a pool chore
- **chore_overdue** - When a chore becomes overdue
- **chore_assigned** - When a chore is assigned to a user
- **perfect_week_achieved** - When a user completes a perfect week
- **weekly_reset** - When weekly points are reset
- **test_notification** - Manual test from admin panel

### Webhook Payload

Each webhook includes a JSON payload with event details:

```json
{
  "event": "chore_completed",
  "message": "Alice completed 'Clean Kitchen'",
  "timestamp": "2025-12-15T14:30:00Z",
  "data": {
    "chore_name": "Clean Kitchen",
    "user": "Alice",
    "points": 25.00,
    "was_late": false
  }
}
```

---

## 📊 REST API

ChoreBoard provides a REST API for custom integrations.

### Authentication

API requests require HMAC authentication:

```http
POST /api/complete-chore/
Authorization: HMAC-SHA256 timestamp:signature
Content-Type: application/json
```

### Available Endpoints

- `GET /api/chores/` - List all chores
- `GET /api/pool/` - List pool chores
- `POST /api/complete-chore/` - Complete a chore
- `POST /api/claim-chore/` - Claim a pool chore
- `GET /api/user-profile/<user_id>/` - Get user details

See the [Admin Guide](ADMIN_GUIDE.md) for complete API documentation.

---

## 🛠️ Custom Integrations

Want to build your own integration? ChoreBoard's REST API makes it easy.

### Example: Python Integration

```python
import requests
import hmac
import hashlib
import time

def complete_chore(instance_id, user_key, user_secret):
    timestamp = str(int(time.time()))
    message = f"POST:/api/complete-chore/:{timestamp}"
    signature = hmac.new(
        user_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'Authorization': f'HMAC-SHA256 {timestamp}:{signature}',
        'X-API-Key': user_key,
        'Content-Type': 'application/json'
    }

    data = {'instance_id': instance_id}

    response = requests.post(
        'http://your-choreboard.com/api/complete-chore/',
        headers=headers,
        json=data
    )

    return response.json()
```

### Example: Node.js Integration

```javascript
const crypto = require('crypto');
const axios = require('axios');

async function completeChore(instanceId, userKey, userSecret) {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const message = `POST:/api/complete-chore/:${timestamp}`;
    const signature = crypto
        .createHmac('sha256', userSecret)
        .update(message)
        .digest('hex');

    const response = await axios.post(
        'http://your-choreboard.com/api/complete-chore/',
        { instance_id: instanceId },
        {
            headers: {
                'Authorization': `HMAC-SHA256 ${timestamp}:${signature}`,
                'X-API-Key': userKey,
                'Content-Type': 'application/json'
            }
        }
    );

    return response.data;
}
```

---

## 🔐 Security Best Practices

When integrating ChoreBoard:

1. **Use HTTPS** - Always use HTTPS for API calls in production
2. **Protect API Keys** - Never commit API keys to version control
3. **Rotate Keys** - Regularly rotate API keys and secrets
4. **Limit Scope** - Create separate API keys for different integrations
5. **Monitor Usage** - Review Action Logs regularly for suspicious activity

---

## 🐛 Troubleshooting

### Integration Not Connecting

1. Verify ChoreBoard URL is correct and accessible
2. Check API key is valid (Admin Panel → Settings)
3. Ensure firewall allows connections
4. Check ChoreBoard logs for errors

### Webhooks Not Working

1. Test webhook URL manually
2. Verify webhook URL is accessible from ChoreBoard server
3. Check ChoreBoard Action Logs for webhook failures
4. Try sending a test notification from Admin Panel

### Home Assistant Entities Not Updating

1. Reload the ChoreBoard integration
2. Check Home Assistant logs for errors
3. Verify ChoreBoard API is responding
4. Restart Home Assistant if needed

---

## 📚 Additional Resources

- **[Home Assistant Integration Repository](https://github.com/PhunkMaster/ChoreBoard-HA-Integration)** - Full integration documentation
- **[Home Assistant Card Repository](https://github.com/PhunkMaster/ChoreBoard-HA-Card)** - Card configuration and examples
- **[ChoreBoard Admin Guide](ADMIN_GUIDE.md)** - Complete API documentation
- **[ChoreBoard User Guide](USER_GUIDE.md)** - Basic usage instructions

---

**Questions or Issues?**

- Report integration issues on the respective GitHub repositories
- Check ChoreBoard documentation for API details
- Review Home Assistant community forums for integration help
