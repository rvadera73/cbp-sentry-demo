#!/bin/bash
# Diagnostic script to check if database is properly seeded

echo "🔍 CBP Sentry Database Diagnostic"
echo "======================================"
echo ""

# Check if database file exists
echo "1️⃣  Database File:"
if [ -f data/cbp_sentry.db ]; then
  echo "   ✅ Found: $(ls -lh data/cbp_sentry.db | awk '{print $5}')"
else
  echo "   ❌ NOT FOUND at data/cbp_sentry.db"
  exit 1
fi

# Check if seed data exists
echo ""
echo "2️⃣  Seed Data File:"
if [ -f services/data/seed_data/manifest_feb_march_2026_with_isf.json ]; then
  SIZE=$(ls -lh services/data/seed_data/manifest_feb_march_2026_with_isf.json | awk '{print $5}')
  COUNT=$(head -100 services/data/seed_data/manifest_feb_march_2026_with_isf.json | grep -c '"id"' || echo "?")
  echo "   ✅ Found: $SIZE (has $COUNT ID fields in first 100 lines)"
else
  echo "   ❌ NOT FOUND at services/data/seed_data/manifest_feb_march_2026_with_isf.json"
fi

# Query database for shipment IDs
echo ""
echo "3️⃣  Database Contents (first 10 shipments):"
sqlite3 data/cbp_sentry.db "SELECT id, shipper_name, risk_score FROM shipments LIMIT 10;" 2>/dev/null | while read line; do
  echo "   $line"
done

# Count records
echo ""
echo "4️⃣  Record Count:"
COUNT=$(sqlite3 data/cbp_sentry.db "SELECT COUNT(*) FROM shipments;" 2>/dev/null)
echo "   Total shipments: $COUNT"

if [ "$COUNT" -eq 0 ]; then
  echo "   ⚠️  EMPTY DATABASE - Seed data was not loaded!"
elif [ "$COUNT" -lt 100 ]; then
  echo "   ⚠️  Only $COUNT records - Expected 1,191 from manifest JSON"
elif [ "$COUNT" -gt 1000 ]; then
  echo "   ✅ Database properly seeded with ~$COUNT records"
fi

echo ""
echo "5️⃣  Sample IDs:"
echo "   From database:"
sqlite3 data/cbp_sentry.db "SELECT DISTINCT substr(id, 1, 20) as id FROM shipments LIMIT 5;" 2>/dev/null | sed 's/^/      /'

echo ""
echo "   Expected from manifest (SHP-*):"
head -20 services/data/seed_data/manifest_feb_march_2026_with_isf.json 2>/dev/null | grep '"id"' | head -3 | sed 's/.*"id": "/      /' | sed 's/".*//'

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Diagnosis:"
if [ "$COUNT" -eq 0 ]; then
  echo "❌ Database is EMPTY - seed function did not run or failed"
  echo "   → Run: docker-compose restart sentry-data"
  echo "   → Check logs: docker-compose logs sentry-data"
elif $(sqlite3 data/cbp_sentry.db "SELECT id FROM shipments LIMIT 1;" 2>/dev/null | grep -q "SHP-"); then
  echo "✅ Database seeded correctly with SHP-* IDs from manifest"
  echo "   All cases should be found"
else
  echo "⚠️  Database has hardcoded fallback IDs (shipment-*), not manifest IDs (SHP-*)"
  echo "   → Seed file was not loaded during container startup"
  echo "   → Try: bash scripts/unified-setup.sh local"
fi
