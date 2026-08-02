# DLsite Utilities

Assorted utilities for managing DLsite works.
Mainly provided as example of ways to use [dlsite-async].

Utilities are opinionated towards author's use case and provided as-is.

## Features

- `dlsite autotag`: Automatically tag `.mp3` and `.m4a` audio files based on DLsite work.
  - Requires `dlsite-utils[mutagen]` extras.
- `dlsite dl`: Download `.zip` or `.rar` files for supported works from DLsite.
  - Requires valid account with credentials set via netrc.
- `dlsite dl-play`: Download browser versions of supported works from DLsite Play.
  - Requires valid account with credentials set via netrc.
- `dlsite rename`: Rename files/directories based on DLsite work circle/title
  - Only supports works which are visible in the DLsite API (does not check Play API for
    Play exclusive works).
- `dlsite vc2mp4`: Convert DLsite Play voicecomics to `.mp4` video.
  - Requires `ffmpeg` in your environment `PATH`.

## Requirements

- Python 3.12+

## Installation

Must be installed from source.

[pipx] can be used to install in a standalone environment directly from Github:

```console
$ pipx install "dlsite-async[mutagen] @ git+https://github.com/bhrevol/dlsite-utils.git"
```

Alternatively, clone this git repository and then install using [pdm] or [pip].

```console
$ git clone https://github.com/bhrevol/dlsite-utils
$ cd dlsite-utils
$ pdm install
```

```console
$ pip install .[mutagen]
```

## Usage

```console
$ dlsite --help
Usage: dlsite [OPTIONS] COMMAND [ARGS]...

  DLsite utilities.

Options:
  --version          Show the version and exit.
  -c, --config FILE  Use the specified configuration file instead of the
                     default config file.
  --help             Show this message and exit.

Commands:
  autotag    Tag .mp3 and .m4a audio files based on DLsite work.
  config     Print the config file location.
  dl         Download purchased work(s) from DLsite.
  dl-play    Download supported work(s) from DLsite Play.
  rename     Rename paths based on DLsite work information.
  vc2mp4     Convert DLsite Play voicecomic(s) to mp4 video.
```

### Configuration

Configuration to adjust `autotag` and `rename` behavior is done via a config file.
See the default config file (which can be found using `dlsite config`).

## License

Distributed under the terms of the [MIT license][license],
_DLsite Utilities_ is free and open source software.

[Mutagen][mutagen] is licensed under the terms of the GNU General Public
License v2.0 or later. If you redistribute _dlsite-utils_ with the optional
`mutagen` extra included, your redistribution must comply with the terms of the
GPL v2.0 or later.

## Credits

This project was generated from [@cjolowicz]'s [Hypermodern Python Cookiecutter] template.

[@cjolowicz]: https://github.com/cjolowicz
[pypi]: https://pypi.org/
[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/bhrevol/dlsite-utils/issues
[pip]: https://pip.pypa.io/
[pdm]: https://pdm-project.org/
[mutagen]: https://github.com/quodlibet/mutagen
[dlsite-async]: https://github.com/bhrevol/dlsite-async

<!-- github-only -->

[license]: https://github.com/bhrevol/dlsite-utils/blob/main/LICENSE
[contributor guide]: https://github.com/bhrevol/dlsite-utils/blob/main/CONTRIBUTING.md
[command-line reference]: https://dlsite-utils.readthedocs.io/en/latest/usage.html
