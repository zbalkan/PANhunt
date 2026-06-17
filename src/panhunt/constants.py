# Maximum bytes read from a file in a single open() call.
# Sized to stay within typical L3 cache on a modern CPU.
BLOCK_SIZE_BYTES: int = 30 * 1024 * 1024   # 30 MB

# Chunk size used when streaming decompressed or binary content.
# Balances memory usage against system-call overhead.
STREAM_CHUNK_SIZE_BYTES: int = 8 * 1024 * 1024   # 8 MB

# Minimum character count for a string to be a valid PAN.
# ISO/IEC 7812: card numbers are 13–19 digits; 12 is the practical minimum due to Maestro.
MIN_PAN_LENGTH: int = 12

# Seconds to wait for available memory before aborting a large payload enqueue.
MEMORY_CHECK_TIMEOUT_SECONDS: int = 20
