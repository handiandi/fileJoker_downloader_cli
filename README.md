# A CLI for downloading files from FileJoker.net
A CLI for downloading files from FileJoker.net (Premium - you need a paid account).
Suitable for use and downloading file on remote PC

## Installation
1. Clone/download the files from the repository
2. Install Pipy packages: `pip3 install -r requirements.txt`
3. Done! :)


## Quick-guide for use: 
The script takes 3 mandatory arguments: Login credentials (email and password) and one or more FileJoker link for wanted file(s). 
The script also take 1 optional argument: Relative path to save the wanted file

- -e [string]: Login email
- -p [string]: Login password
- -l [string]: FileJoker link
- -f [file]: Text file with FileJoker links (one per line)
- -path [string]: Relative path to save the wanted file. Must be an already created folder. Default: Same folder as the script is in

OBS: You must use minimum -l or -f. You can use both, if you like.

You can use --help for help. 


## Dependencies
- Requests


## Issues and to-do
- Can't download multiple files simultaneously.
- Can only be used on Unix file systems due to '/' in path. ('\\' is not supported)

