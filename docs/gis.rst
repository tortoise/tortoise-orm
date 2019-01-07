FAQ
=========

Why do I get an error that `'sqlite3.Connection' object has no attribute 'enable_load_extension'`?
----------------

Some operating systems do not ship with sqlite extension support. So, to make things as easy as possible,
python ships without those features on specific platforms. So, to fix this, you need to explicitly install
sqlite with extension support and build python with the `enable-loadable-sqlite-extensions` flag to support it.