# ScirtScan
## Attack Surface Reduction and Compliance Scan  

> N.B. This is work in progress, changes happen fast, your mileage may vary

This tool takes a list of websites and performs the following checks:

* TLS/SSL check based on the Qualys SSL Scanner or TestSSL.sh
* Check on precense of robots.txt with only Allow statements (of DisAllow: /)
* Check on HTTP headers, certain headers should be present
* Check on absence of version info in HTTP headers check
* Check on absence of no product information and/of version information in the HTML Error page
* Check on redirects from HTTP to HTTPS
* Check on presence of .well-known/security.txt see [https://securitytxt.org/](https://securitytxt.org/)
* Check on Cerificate validity lifetime left
* Check on HSTS lifetime (if present)
* Check for remnants of installation files (Readme.md, Changelog.txt, etc)
* Check for the word "debug" in the returned HTTP headers
* Log all DNS info about the site

<br />
Information is stored in a Sqlite database and can be parsed with these tools: 

* sql2html.py creates a nice overview from that database.  
* sql2excel.py creates an excel file from that database.
* sql2csv.py creates a dump of a sqlite db into semicolon separated output.  
  
All checks have debug logging which is stored in the output directory in a per website name,<br />
this can be usefull to review the status at a certain point in time.

## Requirements
See requirements.txt and as usual perform the following command to satisfy those:  
`pip3 install -r requirements.txt`
 
(or use your OS package management tools)
Default is to use Qualys ssltest (online) to determine the TLS Score, ranging from F to A++. However it is also possible to use [ssltest.sh](https://github.com/drwetter/testssl.sh) ( using the -t switch), but it needs to be installed on the system and if it's not in /usr/local/bin you need to alter the location in scirtscan.py 

## Input file
The input file is required it takes the form of a list of website names, e.g. :  

```
www.some-boring-website.com
www.another-dull-website.com
www.you-get-the-gist.com
``` 

## Output
Output is generated in a newly created directory. The directory name is based on the date (YYYYMMDD). The output directory contains the sqlite file websites.db and the per website results log. 

## Usage
Run from the directory where the files are located:  
`./scirtscan.py -d websites.txt`

The qualys ssltest can take up some time. The default in the script is to specify usecache, so the second time you run the script it will just get the results from the cache. Optional you can specify -xq to skip the Qualys check, for instance:  
`./scirtscan.py -d -xq websites.txt`

all commandline switches as of v2.1c:  

```
usage: scirtscan.py [-h] [-d] [-a] [-v] [-nq] [-oq] [-t] [-ot] [-nc] [-ndf] [FILENAME]

check websites

positional arguments:
  FILENAME              filename with list of websites

options:
  -h, --help            show this help message and exit
  -d, --debug           print debug messages to stderr
  -a, --anon            don't modify user-agent to show who is scanning
  -v, --version         show version info and exit
  -nq, --no_qualys      exclude qualys ssltest
  -oq, --only_qualys    only do qualys ssltest (skip other tests)
  -t, --testssl         use locally installed testssl.sh instead of qualys
  -ot, --only_testssl   only do testssl.sh checks on websites
  -nc, --no_cache       always request fresh tests from qualys
  -ndf, --no_debugfile  Don't save debug output to debug.log in the YYYYMMDD directory
```

if all goes well scirtscan.py will create a directory with the name of todays date in the format YYYYMMDD. The sqlite database with all results and the per website debug log files will be stored in that directory. Next run:  
`./sql2html.py -d`

And that will create an index.html in that directory. Default sql2html.py will read the directory with today's date and write the index.html there If you want to proces another directory, you can specify that with the -p (path) option, for instance:  
`./sql2html.py -d -p 20221231`

If you want to open that index file to view it in your browser and you're on a mac, type:  
`open yyyymmdd/index.html (and yes, replace yyyymmdd with the current date)`

for linux use:  
`xdg-open yyyymmdd/index.html`

If you want to put the files on a webserver, copy the yyyymmdd directory(s) to the webserver root. The file styles.css is used by sql2html.py to generate the index.html, once that's done it's not necessary anymore.

The webpage will look something like this:
![](https://raw.githubusercontent.com/beamzer/ScirtScan/main/scirtscan-table.png)
and if you click on the check_date link for a specific website (on the far right), you will see the detail logs from all checks for that website.

## Structure
The main python script (scirtscan.py) works with functions, you can easily comment out functions to test a single one, or add a new function for new checks.  

## Features realised & Upcoming features
* see [changelog.txt](https://github.com/beamzer/ScirtScan/blob/main/changelog.txt)

## How to obtain the list of websites for your company/institution
Ideally you have a CMDB (Configuration Management Database) and with one press on the right button it spits out a list of all your websites. If you don't have that, i suggest you work on that inventory. In the meantime there are some other tricks that can help you:

* Use [Shodan](https://www.shodan.io/) and query your ip-range
* Use [Censys](https://censys.io/) and query your ip-range
* Best option: use both to make sure you don't miss anything
* [Subfinder](https://github.com/projectdiscovery/subfinder) and [httpx](https://github.com/projectdiscovery/httpx) are **GREAT** tools to help you discover sites based on ip-range or domain name, below are some examples:

> echo 8.8.4.0/24 | httpx -title -tech-detect -status-code -ip -location -fc 403  
> subfinder -d google.com -silent | httpx -title -tech-detect -status-code -ip -location  
> subfinder -silent -d google.com | httpx |& grep ^http > sites_google.txt
 
These tools are used by bugbounty hunters as well, so why wait untill they come knocking with results that you would have liked to find out yourself? On the other hand, laws vary per country so use these tools and the software in this repository in accordance with local law and company policy.

## Oracle free tier
You might not have access to a Linux server or a Mac to run this code. Oracle has an offer where you get access to two of it's cloud servers without cost and they claim this will be free forever. Of course these servers are limited in CPU and memory, but they are more than sufficient to run this code. You can sign up for the free tier on: [https://www.oracle.com/cloud/free/](https://www.oracle.com/cloud/free/)

## Bugs
probably, in fact almost certainly, please let me know
 

## License and Disclaimer
This software is licensed under GPL v3.0 as stated in [LICENSE](https://github.com/beamzer/ScirtScan/blob/main/LICENSE)
