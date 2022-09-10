# DLsite Utilities

[![PyPI](https://img.shields.io/pypi/v/dlsite-utils.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/dlsite-utils.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/dlsite-utils)][pypi status]
[![License](https://img.shields.io/pypi/l/dlsite-utils)][license]

[![Read the documentation at https://dlsite-utils.readthedocs.io/](https://img.shields.io/readthedocs/dlsite-utils/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/bhrevol/dlsite-utils/workflows/Tests/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/bhrevol/dlsite-utils/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi status]: https://pypi.org/project/dlsite-utils/
[read the docs]: https://dlsite-utils.readthedocs.io/
[tests]: https://github.com/bhrevol/dlsite-utils/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/bhrevol/dlsite-utils
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

Assorted utilities for managing DLsite works.

## Features

- `dlsite rename`: Rename files/directories based on DLsite work circle/title
- `dlsite dlst-extract`: Extract contents of DLST files.
  - Requires CypherTec DRM AES128 key and IV used to encrypt the file.
- `dlsite autotag`: Automatically tag audio files based on DLsite work.
  - Requires `dlsite-utils[mutagen]` extras.

## Requirements

- Python 3.9+

## Installation

You can install _DLsite Utilities_ via [pip] from [PyPI]:

```console
$ pip install dlsite-utils
```

To install _Dlsite Utilities_ with optional dependencies:

```console
$ pip install dlsite-utils[mutagen]
```

## Usage

Please see the [Command-line Reference] for details.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [MIT license][license],
_DLsite Utilities_ is free and open source software.

[Mutagen][mutagen] is licensed under the terms of the GNU General Public
License v2.0 or later. If you redistribute _dlsite-utils_ with the optional
`mutagen` extra included, your redistribution must comply with the terms of the
GPL v2.0 or later.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project was generated from [@cjolowicz]'s [Hypermodern Python Cookiecutter] template.

[@cjolowicz]: https://github.com/cjolowicz
[pypi]: https://pypi.org/
[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/bhrevol/dlsite-utils/issues
[pip]: https://pip.pypa.io/
[mutagen]: https://github.com/quodlibet/mutagen

<!-- github-only -->

[license]: https://github.com/bhrevol/dlsite-utils/blob/main/LICENSE
[contributor guide]: https://github.com/bhrevol/dlsite-utils/blob/main/CONTRIBUTING.md
[command-line reference]: https://dlsite-utils.readthedocs.io/en/latest/usage.html
