# Browser Test Plan: Health Dashboard (Chunk 4.6)

**Date:** 2025-12-27
**Component:** Health Dashboard UI
**Location:** http://localhost:8888
**Tester:** David Jackson
**Status:** Not Started

---

## Prerequisites

### 1. Services Running
Ensure the following services are active:
```bash
docker-compose ps
# Should show: redis, vorpal, brain (all "Up")
```

### 2. Start Web UI
```bash
cd /home/davidjackson/Archive-AI/ui
python3 -m http.server 8888
```

### 3. Access Dashboard
Open browser to: http://localhost:8888

---

## Test Cases

### TC-4.6.1: Health Dashboard Panel Visibility ✅ / ❌

**Objective:** Verify the health dashboard panel is visible and properly positioned

**Steps:**
1. Load http://localhost:8888 in browser
2. Locate the "System Health" panel in the right sidebar
3. Verify panel appears below the "Memory Browser" panel

**Expected Results:**
- [ ] Panel titled "System Health" is visible
- [ ] Panel has light gray background
- [ ] Panel has rounded corners and shadow
- [ ] Panel is positioned in the right sidebar
- [ ] Panel is above the bottom of the viewport

**Actual Results:**
```
[Record observations here]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.2: System Metrics Display ✅ / ❌

**Objective:** Verify all four system metrics are displayed correctly

**Steps:**
1. Locate the 2x2 grid of metrics in the health panel
2. Verify each metric card displays:
   - Label (top)
   - Value (bottom, large and bold)

**Expected Results:**
- [ ] **Uptime** card shows time in seconds/minutes/hours format
- [ ] **Memories** card shows numeric count (should be ~107)
- [ ] **CPU** card shows percentage with % symbol
- [ ] **Memory** card shows percentage with % symbol
- [ ] All values are bold and 18px font size
- [ ] All labels are 11px and uppercase
- [ ] Grid layout is 2 columns

**Actual Results:**
```
Uptime: _______
Memories: _______
CPU: _______%
Memory: _______%
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.3: Progress Bars (CPU & Memory) ✅ / ❌

**Objective:** Verify progress bars display correctly with proper styling

**Steps:**
1. Locate the CPU metric card
2. Observe the progress bar below the percentage
3. Locate the Memory metric card
4. Observe the progress bar below the percentage

**Expected Results:**
- [ ] CPU progress bar exists with light gray background
- [ ] CPU progress bar fill is purple gradient
- [ ] CPU bar width matches the percentage value (e.g., 7% → 7% width)
- [ ] Memory progress bar exists with light gray background
- [ ] Memory progress bar fill is purple gradient
- [ ] Memory bar width matches the percentage value
- [ ] Both bars are 4px tall with rounded corners
- [ ] Smooth CSS transition visible (if value changes)

**Actual Results:**
```
CPU bar width: _____%
Memory bar width: _____%
Visual appearance: [describe]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.4: Service Health Status ✅ / ❌

**Objective:** Verify all service health statuses are displayed with correct colors

**Steps:**
1. Scroll down in the health panel to "Services" section
2. Locate the list of 4 services
3. Observe the status badge for each service

**Expected Results:**
- [ ] **Brain** service listed with status badge
- [ ] **Vorpal** service listed with status badge
- [ ] **Redis** service listed with status badge
- [ ] **Sandbox** service listed with status badge
- [ ] Healthy services show **green** badge with "healthy" text
- [ ] Degraded services show **orange** badge with "degraded" text
- [ ] Unhealthy services show **red** badge with "unhealthy" text
- [ ] Unknown services show **gray** badge with "unknown" text
- [ ] Service names are 13px font
- [ ] Badges are right-aligned

**Actual Results:**
```
Brain: [color] - [status text]
Vorpal: [color] - [status text]
Redis: [color] - [status text]
Sandbox: [color] - [status text]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.5: Auto-Refresh Functionality ✅ / ❌

**Objective:** Verify metrics auto-refresh every 5 seconds

**Steps:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter for "/metrics" requests
4. Watch for automatic requests
5. Note the uptime value increasing
6. Observe any visual transitions

**Expected Results:**
- [ ] Initial metrics load on page load
- [ ] New `/metrics` request appears every ~5 seconds
- [ ] Uptime value increments by ~5 seconds each refresh
- [ ] CPU/Memory values may change slightly
- [ ] No JavaScript errors in console
- [ ] Smooth transitions when values update
- [ ] No flickering or layout shifts

**Actual Results:**
```
Request interval: ______ seconds
Uptime progression: [t0]s → [t1]s → [t2]s → [t3]s
Console errors: YES / NO
Visual smoothness: [describe]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.6: Uptime Format Validation ✅ / ❌

**Objective:** Verify uptime displays in appropriate units based on duration

**Steps:**
1. Observe uptime immediately after service restart (< 60s)
2. Wait 1-2 minutes and observe format change
3. (Optional) Wait 60+ minutes and observe hour format

**Expected Results:**
- [ ] **< 60 seconds:** Shows "Xs" (e.g., "23s")
- [ ] **1-60 minutes:** Shows "Xm Ys" (e.g., "2m 15s")
- [ ] **> 60 minutes:** Shows "Xh Ym" (e.g., "1h 23m")
- [ ] Format changes automatically as time passes
- [ ] No decimal places shown

**Actual Results:**
```
At startup: _______
After 90s: _______
After 5m: _______
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.7: Responsive Layout ✅ / ❌

**Objective:** Verify dashboard adapts to different viewport sizes

**Steps:**
1. Resize browser window to narrow width (< 800px)
2. Observe metric grid layout
3. Resize to wide width (> 1200px)
4. Check for overflow or truncation

**Expected Results:**
- [ ] Metric cards remain readable at all sizes
- [ ] 2x2 grid maintained on reasonable widths
- [ ] No horizontal scrolling within panel
- [ ] Text does not overflow cards
- [ ] Progress bars scale proportionally
- [ ] Service list remains visible

**Actual Results:**
```
Narrow width: [describe layout]
Wide width: [describe layout]
Issues: [list any problems]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.8: Error Handling ✅ / ❌

**Objective:** Verify graceful degradation when services are unavailable

**Steps:**
1. Stop the brain service: `docker-compose stop brain`
2. Reload the page in browser
3. Observe error behavior
4. Restart brain: `docker-compose start brain`
5. Verify recovery

**Expected Results:**
- [ ] Page loads without crashing
- [ ] Appropriate error message displayed (or metrics unavailable)
- [ ] No uncaught JavaScript exceptions
- [ ] After restart, metrics resume loading
- [ ] Service health reflects outage

**Actual Results:**
```
During outage: [describe behavior]
Console errors: [list errors]
After recovery: [describe behavior]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.9: Network Performance ✅ / ❌

**Objective:** Verify minimal network overhead from auto-refresh

**Steps:**
1. Open DevTools Network tab
2. Let dashboard refresh for 1 minute (12 refreshes)
3. Check total data transferred for /metrics requests

**Expected Results:**
- [ ] Each /metrics request is < 1KB
- [ ] Total data for 1 minute < 12KB
- [ ] Response time < 500ms per request
- [ ] No memory leaks in browser (check DevTools Memory tab)

**Actual Results:**
```
Bytes per request: ______ bytes
Total for 1 minute: ______ KB
Average response time: ______ ms
Memory stable: YES / NO
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.10: Cross-Browser Compatibility ✅ / ❌

**Objective:** Verify dashboard works in multiple browsers

**Steps:**
1. Test in Chrome/Chromium
2. Test in Firefox
3. Test in Safari (if available)

**Expected Results:**
- [ ] Chrome: All features working
- [ ] Firefox: All features working
- [ ] Safari: All features working
- [ ] Consistent visual appearance across browsers
- [ ] No browser-specific errors

**Actual Results:**
```
Chrome version: ______ - Status: PASS/FAIL
Firefox version: ______ - Status: PASS/FAIL
Safari version: ______ - Status: PASS/FAIL
Issues: [list any browser-specific problems]
```

**Status:** PASS / FAIL / BLOCKED

---

### TC-4.6.11: Visual Design Validation ✅ / ❌

**Objective:** Verify visual design matches specification

**Steps:**
1. Compare rendered UI against checkpoint specification
2. Verify color scheme
3. Check typography
4. Validate spacing and alignment

**Expected Results:**
- [ ] Background: Light gray (#f5f5f5 or similar)
- [ ] Progress bars: Purple gradient
- [ ] Health badges: Green (#22c55e), Orange (#f59e0b), Red (#ef4444), Gray (#9ca3af)
- [ ] Metric values: 18px bold
- [ ] Labels: 11px uppercase
- [ ] Service names: 13px
- [ ] Consistent padding and margins
- [ ] Professional, polished appearance

**Actual Results:**
```
Visual quality: [rate 1-10]
Color accuracy: PASS / FAIL
Typography: PASS / FAIL
Spacing: PASS / FAIL
Issues: [list any visual problems]
```

**Status:** PASS / FAIL / BLOCKED

---

## Summary

**Total Test Cases:** 11
**Passed:** ___ / 11
**Failed:** ___ / 11
**Blocked:** ___ / 11

**Overall Status:** PASS / FAIL / PARTIAL

---

## Defects Found

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BUG-4.6.1 | [High/Med/Low] | [Description] | [Open/Fixed] |
| BUG-4.6.2 | [High/Med/Low] | [Description] | [Open/Fixed] |

---

## Recommendations

**Critical Issues (must fix before moving to 4.7):**
- [List any critical bugs]

**Nice-to-Have Improvements:**
- [List any enhancements discovered during testing]

---

## Sign-Off

**Tester:** _______________
**Date:** _______________
**Browser:** _______________
**OS:** _______________

**Notes:**
```
[Additional observations or comments]
```

---

## Quick Test Command Reference

```bash
# Start services
docker-compose up -d redis vorpal brain

# Check service status
docker-compose ps

# View brain logs
docker logs brain -f

# Start web UI
cd ui && python3 -m http.server 8888

# Stop a service (for error testing)
docker-compose stop brain

# Restart a service
docker-compose start brain

# Check VRAM usage
nvidia-smi
```
