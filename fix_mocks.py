import re

file_path = "tests/test_rate_limit_failopen_examples.py"
with open(file_path, "r") as f:
    content = f.read()


# Replace mock_redis.incr = AsyncMock(side_effect=...)
# with pipeline mock setup
def replacer(match):
    side_effect = match.group(1)
    return f"""mock_redis = MagicMock()
    pipe_mock = AsyncMock()
    pipe_mock.execute.side_effect = {side_effect}
    ctx = MagicMock()
    ctx.__aenter__.return_value = pipe_mock
    mock_redis.pipeline.return_value = ctx"""


content = re.sub(
    r"mock_redis = AsyncMock\(\)\s+mock_redis\.incr = AsyncMock\(side_effect=(.*?)\)",
    replacer,
    content,
)

with open(file_path, "w") as f:
    f.write(content)
