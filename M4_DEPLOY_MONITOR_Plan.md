# M4: DEPLOY & MONITOR — Implementation Plan

**Phase**: DAD-M DEPLOY & MONITOR
**Milestone**: M4 (Week 5-6)
**Objective**: Build, test in staging, deploy to production, setup monitoring

---

## Overview

M4 focuses on moving the M3 implementation from development → staging → production with comprehensive testing and monitoring setup.

### Current State
- ✅ All code merged to `main`
- ✅ Docker infrastructure in place (PostgreSQL, Redis, Nginx)
- ✅ Book UI fully implemented (page-turn nav, forms, accessibility)
- ❌ No staging environment testing yet
- ❌ No cross-browser testing conducted
- ❌ No production monitoring configured

### Deliverables for M4
1. Local Docker build verified ✓
2. Staging environment tests completed ✓
3. Cross-browser compatibility confirmed ✓
4. Mobile device testing validated ✓
5. Performance baseline established ✓
6. Monitoring and alerting configured ✓
7. Production deployment completed ✓

---

## Phase 1: Build & Local Testing

### 1.1 Build Docker Image

**Command**:
```bash
cd /home/admin/projects/roll-drauf-vtt
docker build -t roll-drauf-vtt:m3-latest .
```

**Expected Output**:
```
Building roll-drauf-vtt:m3-latest
Step 1/8 : FROM python:3.12-slim
Step 2/8 : ENV PYTHONDONTWRITEBYTECODE=1
...
Successfully built [image-hash]
Successfully tagged roll-drauf-vtt:m3-latest
```

**Verification**:
```bash
docker images | grep roll-drauf-vtt
```

### 1.2 Verify Build Contents

Check that new CSS/JS files are included:
```bash
docker run --rm roll-drauf-vtt:m3-latest \
  ls -la vtt_app/static/css/components.css \
         vtt_app/static/js/book-scene.js
```

**Expected**: Both files present in Docker image

### 1.3 Test Local Docker Compose

**Setup**:
```bash
# Create .env.local for testing
cat > .env.local << 'EOF'
FLASK_ENV=development
FLASK_DEBUG=0
DATABASE_URL=postgresql://vtt:vtt@db:5432/vtt
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=http://localhost,http://127.0.0.1:8000
EOF

# Start services
docker-compose -f docker-compose.vtt.roll-drauf.de.yml up -d
```

**Verification Steps**:
1. Check PostgreSQL health: `docker-compose exec db pg_isready`
2. Check Redis health: `docker-compose exec redis redis-cli ping`
3. Check Flask app logs: `docker-compose logs app`
4. Access app: `curl http://localhost` (should not error)

**Expected Results**:
- All services start successfully
- Database initializes
- Flask app listens on :5000
- Nginx reverse proxy on :80/:443

---

## Phase 2: Staging Environment Testing

### 2.1 Test Login Flow

**Steps**:
1. Navigate to `http://staging.vtt.local/login.html`
2. Verify:
   - [ ] Book opens automatically on page load
   - [ ] Login form visible after animation
   - [ ] No console errors
   - [ ] GSAP animations smooth (60fps)

**Expected**:
- Book opening animation smooth
- Form fully interactive after 2s
- No network errors

### 2.2 Test Page Navigation

**Steps**:
1. Log in successfully
2. Test all navigation paths:
   - [ ] Dashboard → Campaigns (page-turn animation)
   - [ ] Campaigns → Characters (page-turn animation)
   - [ ] Characters → Dashboard (via button or ESC key)

**Expected**:
- All page-turn animations smooth (0.6s)
- No lag or jank
- Correct page numbers visible (1–2, 3–4, 5–6)
- Bookmark moves to correct position

### 2.3 Test Keyboard Navigation

**Steps**:
1. Open any page
2. Test keyboard shortcuts:
   - [ ] **Right Arrow**: Navigate to next page
   - [ ] **Left Arrow**: Navigate to previous page
   - [ ] **ESC**: Return to dashboard
   - [ ] **Tab**: Focus through form fields

**Expected**:
- All keyboard shortcuts work
- Focus indicators visible (gold outline)
- Navigation smooth and responsive

### 2.4 Test Form Interactions

**Steps**:
1. Log in / Create new campaign
2. Test form elements:
   - [ ] Input focus states (gold glow)
   - [ ] Form validation (error messages appear)
   - [ ] Button hover effects (shadow lift)
   - [ ] Error message styling (red, visible)

**Expected**:
- All form elements styled correctly
- Validation messages appear/disappear appropriately
- No form submission delays

### 2.5 Test Responsive Design

**Viewport Sizes**:
```
Mobile:    320px × 568px (iPhone SE)
Tablet:    768px × 1024px (iPad)
Desktop:   1440px × 900px
Large:     1920px × 1080px
```

**Steps** (for each viewport):
1. [ ] Login page renders correctly
2. [ ] Book dimensions appropriate for screen
3. [ ] Forms readable without zoom
4. [ ] Page numbers visible (desktop) / hidden (mobile)
5. [ ] Buttons touch-friendly (44px+ targets)
6. [ ] No horizontal scroll

**Expected**:
- Perfect responsive behavior at all breakpoints
- Content legible without magnification
- Touch targets adequate on mobile

---

## Phase 3: Cross-Browser Testing

### 3.1 Browser Coverage Matrix

| Browser | Version | OS | Status |
|---------|---------|----|----|
| Chrome | Latest | Windows/Mac/Linux | ✓ |
| Firefox | Latest | Windows/Mac/Linux | ✓ |
| Safari | Latest | macOS | ✓ |
| Edge | Latest | Windows | ✓ |
| Chrome | Latest | iOS | ✓ |
| Safari | Latest | iOS | ✓ |
| Chrome | Latest | Android | ✓ |

### 3.2 Test Cases per Browser

For each browser, test:
1. **Book Animation**
   - [ ] Opens smoothly on page load
   - [ ] Cover flip animation plays correctly
   - [ ] Login form appears after animation

2. **Page-Turn Navigation**
   - [ ] Rotation animation smooth (60fps)
   - [ ] Page transition seamless
   - [ ] No flickering or artifacts

3. **Form Elements**
   - [ ] Input focus states visible
   - [ ] Button hover effects work
   - [ ] Validation messages display
   - [ ] Placeholder text visible

4. **Keyboard Navigation**
   - [ ] Tab order logical
   - [ ] Focus indicators visible
   - [ ] Arrow keys work for page turns
   - [ ] ESC key works

5. **Visual Appearance**
   - [ ] Colors render correctly
   - [ ] Fonts load (Cinzel, Segoe UI)
   - [ ] Shadows/effects display
   - [ ] Page numbers visible (desktop)
   - [ ] Bookmarks positioned correctly

### 3.3 Known Browser Issues to Watch For

- **Safari**: GSAP 3D transforms may need testing
- **Mobile Safari**: Touch events, focus management
- **Firefox**: Font loading timing
- **Edge**: CSS custom properties support

---

## Phase 4: Mobile Device Testing

### 4.1 Physical Device Testing

**Devices to Test**:
- [ ] iPhone 12 mini (320px - smallest)
- [ ] iPhone 14 Pro (390px - typical)
- [ ] iPad Air (820px - tablet)
- [ ] Android device (Samsung Galaxy S21 - 360px)

**Testing Checklist** (per device):
1. **Touch Interactions**
   - [ ] Book cover clickable (tap to open)
   - [ ] Form inputs properly sized
   - [ ] Buttons easy to tap (44px+)
   - [ ] No zoom needed for interaction

2. **Book UI on Mobile**
   - [ ] Single-page view (right page hidden)
   - [ ] Book fills screen appropriately
   - [ ] Page numbers hidden (mobile only)
   - [ ] Bookmark visible on edge

3. **Form on Mobile**
   - [ ] Keyboard appears for inputs
   - [ ] Inputs remain in view while typing
   - [ ] Submit button accessible
   - [ ] Error messages visible

4. **Navigation on Mobile**
   - [ ] Page-turn animation works
   - [ ] Bookmark moves correctly
   - [ ] Keyboard shortcuts accessible
   - [ ] No layout shift on nav

### 4.2 Performance on Mobile

Test with network throttling:
- **Slow 3G**: 400 kbps down, 400 kbps up, 400ms latency
- **Fast 3G**: 1.6 Mbps down, 750 kbps up, 150ms latency

**Metrics to Monitor**:
- Page load time: < 3s on Fast 3G
- Time to interactive: < 5s on Slow 3G
- Animation frame rate: ≥ 50fps on mobile devices

---

## Phase 5: Performance Profiling

### 5.1 Baseline Metrics

**JavaScript Performance**:
```javascript
// Measure page-turn animation performance
const startTime = performance.now();
BookScene.pageTurn('/campaigns');
const duration = performance.now() - startTime;
console.log('Page-turn time:', duration, 'ms');
```

**Expected**:
- Animation frames: 60fps (0ms frame time on average)
- Page-turn setup: < 50ms
- Navigation: immediate (< 100ms)

### 5.2 Memory Usage

Monitor using Chrome DevTools:
1. Open DevTools → Memory tab
2. Load page, interact with forms
3. Navigate through pages
4. Check for memory leaks

**Expected**:
- Initial heap: ~5-10MB
- After interactions: no growth > 2MB
- No memory leaks detected

### 5.3 Network Performance

Using Chrome DevTools Network tab:
1. Load login page
2. Measure critical assets:
   - [ ] CSS files: < 100ms total
   - [ ] JS files: < 200ms total
   - [ ] HTML: < 50ms
   - [ ] Images/fonts: < 500ms total

**Expected**:
- Total page load: < 2s on Fast 3G
- Largest Contentful Paint (LCP): < 2.5s
- Cumulative Layout Shift (CLS): < 0.1

### 5.4 Animation Performance

Using Chrome DevTools Performance tab:
1. Record page-turn animation (0.6s)
2. Check frame rate
3. Look for jank/dropped frames

**Expected**:
- Consistent 60fps
- No dropped frames
- GPU acceleration enabled (force3D: true in GSAP)

---

## Phase 6: Monitoring & Alerting Setup

### 6.1 Application Monitoring

**Tools**: Sentry, New Relic, or Datadog

**Setup**:
```python
# In app initialization
import sentry_sdk

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/project-id",
    environment="production",
    traces_sample_rate=1.0,
)
```

**Metrics to Monitor**:
- Application errors (rate, type, frequency)
- Page load times (frontend)
- API response times (backend)
- Database query performance
- Redis cache hit rate

### 6.2 Error Tracking

**Track**:
- [ ] JavaScript console errors
- [ ] GSAP animation failures
- [ ] Form validation errors
- [ ] API failures
- [ ] Network timeouts

**Alerts**:
- Error rate > 0.1% (alert immediately)
- Page load time > 3s (warning)
- Database response time > 500ms (warning)

### 6.3 Performance Monitoring

**Metrics**:
- Page load time (P50, P95, P99)
- Time to interactive
- Animation frame rate
- API endpoint latencies
- Database query times

**Dashboards**:
```
[VTT Production Dashboard]
├── Overview
│   ├── Active users (real-time)
│   ├── Requests per second
│   ├── Error rate %
│   └── Average response time
├── Performance
│   ├── Page load time
│   ├── Database query times
│   ├── Redis hit rate
│   └── CPU/Memory usage
└── Errors
    ├── Top errors (by frequency)
    ├── New errors (last hour)
    └── Error trend (7-day)
```

### 6.4 Uptime Monitoring

**Service Checks**:
- [ ] Web server responds (HTTP 200)
- [ ] Database is reachable
- [ ] Redis is reachable
- [ ] Page load < 5s
- [ ] Form submission works

**Schedule**: Every 5 minutes

**Alerts**:
- Service down: immediate SMS/email
- Degraded performance: email

---

## Phase 7: Production Deployment

### 7.1 Pre-Deployment Checklist

- [ ] All staging tests passed
- [ ] Cross-browser testing complete
- [ ] Mobile testing validated
- [ ] Performance baseline established
- [ ] Monitoring configured
- [ ] Backups created
- [ ] Rollback plan documented

### 7.2 Deployment Steps

**1. Create Backup**:
```bash
docker-compose -f docker-compose.vtt.roll-drauf.de.yml exec db \
  pg_dump -U vtt -d vtt > vtt_backup_$(date +%Y%m%d_%H%M%S).sql
```

**2. Build & Push Image**:
```bash
docker build -t roll-drauf-vtt:production .
docker tag roll-drauf-vtt:production your-registry/roll-drauf-vtt:latest
docker push your-registry/roll-drauf-vtt:latest
```

**3. Deploy to Production**:
```bash
# SSH to production server
ssh deployment@vtt.roll-drauf.de

# Pull latest image
docker-compose -f docker-compose.vtt.roll-drauf.de.yml pull

# Restart services (zero-downtime if using health checks)
docker-compose -f docker-compose.vtt.roll-drauf.de.yml up -d
```

**4. Verify Deployment**:
```bash
# Check all services running
docker-compose -f docker-compose.vtt.roll-drauf.de.yml ps

# Check application logs
docker-compose -f docker-compose.vtt.roll-drauf.de.yml logs app | tail -50

# Test endpoint
curl https://vtt.roll-drauf.de/health
```

### 7.3 Rollback Plan

If issues occur:

**Immediate Rollback** (< 1 minute):
```bash
# Revert to previous image
docker-compose -f docker-compose.vtt.roll-drauf.de.yml down
docker-compose -f docker-compose.vtt.roll-drauf.de.yml up -d
```

**Full Rollback** (with database):
```bash
# Restore from backup
psql -h localhost -U vtt -d vtt < vtt_backup_YYYYMMDD_HHMMSS.sql

# Restart containers
docker-compose -f docker-compose.vtt.roll-drauf.de.yml restart
```

---

## Success Criteria

### M4 Complete When:

✅ **Build & Testing**:
- Docker image builds without errors
- Local Docker Compose starts successfully
- All staging tests pass

✅ **Browser Compatibility**:
- Chrome, Firefox, Safari, Edge all work
- iOS Safari and Android Chrome tested
- No critical JavaScript errors in any browser

✅ **Mobile**:
- Tested on 4+ physical devices
- Touch interactions work smoothly
- Responsive layout perfect at all breakpoints

✅ **Performance**:
- Page load: < 2s on Fast 3G
- Animation: Consistent 60fps
- No memory leaks detected

✅ **Monitoring**:
- Error tracking configured
- Performance dashboards setup
- Alerts configured and tested

✅ **Production**:
- Deployed successfully
- All services running
- Health checks passing
- No errors in first hour

---

## Next Steps

1. **Start Build Process** → Run Docker build command
2. **Run Staging Tests** → Use test checklist above
3. **Fix Any Issues** → Create hotfix commits as needed
4. **Deploy to Production** → Follow deployment steps
5. **Monitor First 24 Hours** → Watch dashboards, respond to alerts

