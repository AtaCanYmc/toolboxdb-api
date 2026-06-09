from unittest.mock import MagicMock

m = MagicMock()
print(hasattr(m, "app"))
app_mock = m.app
print(hasattr(app_mock, "app"))
print(m.app is m.app.app)
