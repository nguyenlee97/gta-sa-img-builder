# ⚡ GTA SA IMG Builder

**Multi-threaded GTA San Andreas IMG v2 archive builder with ThreadPoolExecutor.**

Enhanced version of [IMG Archive Creator](https://github.com/nguyenlee97/gta-sa-img-archive-creator) with parallel processing support.

## Features

- **Parallel multi-threaded building** — uses `ThreadPoolExecutor` with all logical CPUs
- **Tkinter GUI** — same intuitive interface as the basic creator
- **Queue-based workflow** — add multiple folders for batch conversion
- **4 MB copy buffer** — optimized for large file operations
- **Save/Load configurations** — INI config file support

## Improvements Over Basic Creator

| Feature | Basic Creator | IMG Builder |
|---------|--------------|-------------|
| Threading | Single-threaded | ThreadPoolExecutor (all CPUs) |
| Copy Buffer | Default | 4 MB optimized |
| Performance | Sequential | Parallel workers |

## Requirements

- **Python 3.6+**
- **tkinter** (included with Python on Windows)
- No additional pip dependencies

## Usage

```bash
python img_builder.py
```

## Technical Details

- `BLOCK_SIZE = 2048` — standard GTA SA IMG block alignment
- `COPY_BUFFER_SIZE = 4 * 1024 * 1024` — 4 MB buffer for file I/O
- Uses `concurrent.futures.ThreadPoolExecutor` for parallel archive building

## License

MIT License — see [LICENSE](LICENSE).

## Credits

- Built as part of **Project Eagle** by [@nguyenlee97](https://github.com/nguyenlee97)
