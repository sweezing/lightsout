"""GiST index for viewport queries (Feature 2, Table 3: p95 <= 300 ms at 10,000 cards).

Uses PostgreSQL's built-in point type, so no PostGIS extension is needed:
    CREATE INDEX ... USING gist (point(x, y)) WHERE status = 'published'
Skipped on non-PostgreSQL databases (SQLite in quick local tests).
"""
from django.db import migrations

CREATE = (
    "CREATE INDEX IF NOT EXISTS cards_card_published_point_gist "
    "ON cards_card USING gist (point(x, y)) WHERE status = 'published'"
)
DROP = "DROP INDEX IF EXISTS cards_card_published_point_gist"

def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE)

def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP)

class Migration(migrations.Migration):
    dependencies = [("cards", "0001_initial")]
    operations = [migrations.RunPython(forwards, backwards)]
