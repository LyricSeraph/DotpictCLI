# Command Line Tool for Dotpict 
A CLI tool for collecting images from [Dotpict](https://dotpict.net/)

## Requirement
- python 3.6+
- requests

## Usage

1. Modify value of `prefix1` and `prefix2` in token-config.json
2. Run the python script

```
usage: python3 src/main.py <options>
options:
    --follower-user-id=
        Get dotpic records with this users follow list. e.g. --follower-user-id=123456
    --target-user-id=
        Get dotpic records uploaded by this user id. e.g. --target-user-id=123456
    --target-user-id-list-file=
        Get dotpic records by user id in the file row by row. e.g. --target-user-id-list-file=./userids.txt
    --verbose
        Log verbose messages
```

The script will output 2 files in a successful execution:

1. output{time}.json
    - Contains all the work records crawled in this execution in json list format.
    - Rewritten on each execution.
2. save.json
    - A maintained json map to max work id for each author.
    - Any work id not greater than specific value were ignored and let the script stop getting the next page. So you won't get duplicate records between successful executions.

## WARNING

Note that APIs from Dotpict are unstable. So __DO NOT__ rely on this project too much.
