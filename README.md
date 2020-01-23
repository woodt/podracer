# Podracer: Analyze and "lint" a data.json resource

## Installation

Requires Python 3.6 or later, and pip 19.2 or later.

```
$ pip install git+https://github.com/woodt/podracer.git#egg=podracer
```

## Usage

```
$ podracer https://healthdata.gov/data.json

$ podracer --help
Usage: cli.py [OPTIONS] URL

Options:
  --verbose          Show more details about datasets and distributions
  --link-check       Check dataset landing page and distribution URLs
  --keyword-cluster  Enable (VERY) experimental keyword clustering.  Not great,
                     and slow for large # of keywords.
  --help             Show this message and exit.
```
