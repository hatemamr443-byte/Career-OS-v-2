# Auth Testing Playbook (Emergent Google OAuth)

Test user pre-created in MongoDB. See /app/memory/test_credentials.md.

## Step 1: Use existing test session
session_token: `test_session_career_os`
user_id: `user_testseed01`

## Step 2: Test Backend
```
curl -X GET "$REACT_APP_BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer test_session_career_os"
```

Should return user JSON.

## Step 3: Test protected endpoints
- GET /api/jobs
- GET /api/missions/today
- GET /api/insights
- GET /api/emails
- POST /api/seed-me  (idempotent: seeds CV + sample emails)

All require `Authorization: Bearer test_session_career_os` header.

## Step 4: Browser testing (Playwright)
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "test_session_career_os",
    "domain": "<host without https>",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto(f"{BASE_URL}/dashboard")
```
