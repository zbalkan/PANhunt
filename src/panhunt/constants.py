# Maximum bytes read from a file in a single open() call.
# Sized to stay within typical L3 cache on a modern CPU.
BLOCK_SIZE_BYTES: int = 30 * 1024 * 1024   # 30 MB

# Chunk size used when streaming decompressed or binary content.
# Balances memory usage against system-call overhead.
STREAM_CHUNK_SIZE_BYTES: int = 8 * 1024 * 1024   # 8 MB

# Seconds to wait for available memory before aborting a large payload enqueue.
MEMORY_CHECK_TIMEOUT_SECONDS: int = 20
