# Iframe Embedding Configuration

ChoreBoard is configured to **allow iframe embedding by default**, making it perfect for:
- Home automation dashboards (Home Assistant, SmartThings)
- Digital signage and kiosk displays
- Custom web dashboards
- Embedded family chore boards

---

## Configuration

### Environment Variable

Control iframe embedding via the `.env` file:

```bash
# Allow iframe embedding (default: True)
ALLOW_IFRAME_EMBEDDING=True

# To disable iframe embedding for security:
# ALLOW_IFRAME_EMBEDDING=False
```

### How It Works

When `ALLOW_IFRAME_EMBEDDING=True` (default):
- Django's `XFrameOptionsMiddleware` is **excluded** from the middleware stack
- No `X-Frame-Options` header is sent
- Pages can be embedded in iframes from any domain
- All pages (including minimal pages) are embeddable

When `ALLOW_IFRAME_EMBEDDING=False`:
- Django's `XFrameOptionsMiddleware` is **included** in the middleware stack
- `X-Frame-Options: DENY` header is sent with all responses
- Browser blocks all iframe embedding attempts
- Provides clickjacking protection

---

## Security Considerations

### Risks of Enabling Iframe Embedding

**Clickjacking Attacks:**
- Malicious sites could embed ChoreBoard in invisible iframes
- Users might unknowingly interact with ChoreBoard through the iframe
- Potential for unauthorized actions (claiming chores, completing tasks)

**Mitigation:**
- Only enable if you control the sites embedding ChoreBoard
- Use HTTPS to prevent man-in-the-middle attacks
- Consider using authentication for sensitive operations
- Monitor ActionLog for unusual activity

### When to Enable

✅ **Safe scenarios:**
- Embedding in your own Home Assistant dashboard
- Company/household intranet dashboards
- Trusted kiosk displays within your network
- Personal web dashboards you control

❌ **Unsafe scenarios:**
- Public websites you don't control
- Untrusted third-party services
- Open/shared hosting environments

---

## Usage Examples

### Home Assistant Lovelace Card

```yaml
type: iframe
url: http://your-choreboard-server:8000/pool/minimal/
aspect_ratio: 56%
```

### Home Assistant Webpage Card

```yaml
type: webpage
url: http://your-choreboard-server:8000/assigned/minimal/
```

### HTML Iframe

```html
<iframe src="http://your-choreboard-server:8000/pool/minimal/"
        width="100%"
        height="800px"
        frameborder="0"
        title="ChoreBoard Pool">
</iframe>
```

### Responsive Iframe (Scales with Container)

```html
<div style="position: relative; padding-bottom: 75%; height: 0; overflow: hidden;">
  <iframe src="http://your-choreboard-server:8000/leaderboard/minimal/"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
          frameborder="0">
  </iframe>
</div>
```

---

## Best Pages for Embedding

### Minimal Pages (Recommended)
These pages are optimized for iframe embedding with:
- No navigation chrome
- Auto-refresh every 30-60 seconds
- No authentication required
- Touch-friendly interface

**Available Minimal Pages:**
- `/pool/minimal/` - Pool chores for claiming
- `/assigned/minimal/` - All assigned chores by user
- `/users/minimal/` - User overview cards
- `/user/<username>/minimal/` - Single user's chores
- `/leaderboard/minimal/` - Points leaderboard
- `/arcade/leaderboard/minimal/` - Arcade time records
- `/arcade/judge-approval/minimal/` - Pending arcade approvals

### Regular Pages
Can also be embedded but include:
- Full navigation menu
- Page headers
- Back buttons
- May require authentication

---

## Testing Iframe Embedding

A test file is included at `test_iframe.html` in the project root:

1. Start ChoreBoard:
   ```bash
   python manage.py runserver
   ```

2. Open `test_iframe.html` in your browser (double-click the file)

3. Verify:
   - ChoreBoard pages load inside iframes
   - Navigation works within iframes
   - Interactions (clicking, claiming) function normally

If pages don't load:
- Check that `ALLOW_IFRAME_EMBEDDING=True` in `.env`
- Restart Django server after changing settings
- Check browser console for errors

---

## Troubleshooting

### "Refused to display in a frame"

**Cause:** Iframe embedding is disabled

**Solution:**
1. Check `.env` file: `ALLOW_IFRAME_EMBEDDING=True`
2. Restart Django server
3. Clear browser cache

### Mixed Content Warnings

**Cause:** HTTPS page embedding HTTP iframe

**Solution:**
- Serve ChoreBoard over HTTPS
- Or embed in HTTP page (not recommended for production)

### CORS Errors

**Note:** Iframes don't typically cause CORS errors. If you see CORS errors:
- These are from AJAX requests, not iframe embedding
- Add embedding domain to `ALLOWED_HOSTS` in settings
- Ensure API endpoints allow requests from embedding domain

---

## Production Recommendations

For production deployments with iframe embedding:

1. **Use HTTPS** - Prevents man-in-the-middle attacks
2. **Whitelist Domains** - Consider modifying settings to only allow specific domains
3. **Monitor Logs** - Check ActionLog for suspicious activity
4. **Authentication** - Keep authentication enabled for sensitive operations
5. **Regular Backups** - Use automated backup feature
6. **Update ALLOWED_HOSTS** - Include your server's domain

---

## Advanced: Per-View Control

If you need fine-grained control (allow some pages in iframes, block others):

**Option 1: Decorator on specific views**
```python
from django.views.decorators.clickjacking import xframe_options_exempt

@xframe_options_exempt
def my_embeddable_view(request):
    # This view can be embedded
    pass
```

**Option 2: Custom middleware**
Create middleware to check request path and set `X-Frame-Options` accordingly.

**Option 3: Content Security Policy**
Use `Content-Security-Policy: frame-ancestors` header for modern browsers with fine-grained control.

---

## Questions?

Refer to:
- **Admin Guide**: `docs/ADMIN_GUIDE.md` - Environment variables section
- **User Guide**: `docs/USER_GUIDE.md` - Kiosk mode section
- **Django Documentation**: https://docs.djangoproject.com/en/stable/ref/clickjacking/
