# A CLI for downloading files from FileJoker.net
A CLI for downloading files from FileJoker.net (Premium - you need a paid account).
Suitable for use and downloading file on remote PC


## Installation
1. Clone/download the files from the repository
2. Download and install PhantomJS version **2.1.1** (or higher) by following [this guide](phantomjs_guide.md).
3. Install Pipy packages: `pip3 install -r requirements.txt`
4. Done! :)


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

##### About the file flag (-f)
The file should contain one FileJoker link per line. 
More, you can comment out lines (links) if the script should ignore them. You this with '#'
You can also specify a new name for a file. By using '--> [new name]', the script will rename the file to '[new name]' after the download is finished. 

Example:
```
https://filejoker.net/link1
https://filejoker.net/link2 --> my_new_file
#https://filejoker.net/link3
```
In the example above, the following is happening:
- Link1 will be downloaded as is
- The file from link2 will be renamed to 'my_new_file'. The file will keep it's extension. 
- Link3 will be ignored.



## Dependencies
- Requests


## Issues and to-do
- Can't download multiple files simultaneously.
- Can only be used on Unix file systems due to '/' in path. ('\\' is not supported)

