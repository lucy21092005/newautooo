#!/bin/bash
# QUICK START: Auto-Guardian-X with Heart Rate Tracking

echo "🚀 AUTO-GUARDIAN-X - HEART RATE INTEGRATION"
echo "==========================================="
echo ""

# Ensure we're in the right directory
cd /home/abhi/Desktop/autoguardian_x || exit 1

# Activate virtual environment
echo "[STEP 1] Activating Python environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate venv"
    exit 1
fi
echo "✅ Environment activated (venv)"
echo ""

# Run integration test
echo "[STEP 2] Verifying integration..."
python test_heart_rate_integration.py 2>&1 | grep -E "(✅|❌|Next)" | tail -5
echo ""

# Launch PyQt app
echo "[STEP 3] Launching AUTO-GUARDIAN-X UI..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📌 INSTRUCTIONS:"
echo "  1. Click '▶ Start Monitoring' button"
echo "  2. Wait ~5 seconds for heart rate to initialize"
echo "  3. Watch the real-time heart rate display update"
echo "  4. Monitor telemetry in: shared/dashboard_data.json"
echo ""
echo "🛑 To stop: Press the '⏸ Pause' button or click ✕"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python pyqt_app.py
