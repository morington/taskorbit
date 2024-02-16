# Changelog

---

# v0.1.7a (not out yet!)
- Added `CHANGELOG.md` for easy tracking of changes in each version.

### Changes in API
- The following changes have been made to the `dispatching.dispatcher.Dispatcher` class:
    - The `context_data` field is now called `stream_data` for a clearer understanding of its purpose.
    - The `queue` field has been renamed `pool` to reflect a more precise purpose for this class.
- Name changes in `dispatching.router`:
    - `on_execution_timeout` changed to `on_execution_cb`
    - `on_close` changed to `on_close_cb`

#### Naming changes
- The `dispatching.queue.Queue` class has been renamed to `dispatching.pool.Pool` to improve the semantics and consistency of its functionality.

### Documentation
- Added doc-strings for all functions and classes to provide a more complete description of their purpose and usage.

### Other changes
- Made minor code formatting to improve readability and style.
- Fixing bugs in middleware