import re

file_path = "alembic/versions/ffd95f9cc5ab_initial_migration.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# We can replace drop_table('parts') with drop_table('parts', cascade=True)
content = content.replace("op.drop_table('parts')", "op.drop_table('parts')")
# Wait, op.drop_table might not take cascade=True in standard Alembic operations unless using execute.
# Let's just swap the order of drops in the upgrade script.

upgrade_pattern = r"def upgrade\(\) -> None:(.*?)def downgrade\(\) -> None:"
match = re.search(upgrade_pattern, content, re.DOTALL)
if match:
    upgrade_body = match.group(1)

    # Simple fix: execute DROP TABLE CASCADE
    # Replace the table drops with manual execution.
    content = content.replace(
        "op.drop_table('parts')", "op.execute('DROP TABLE parts CASCADE')"
    )
    content = content.replace(
        "op.drop_table('stock_movements')",
        "op.execute('DROP TABLE stock_movements CASCADE')",
    )

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
