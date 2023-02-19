# ScirtScan
## This is work in progress, your mileage may vary

Python script to scan a list of websites with a number of checks:

* TLS/SSL check based on the Qualys SSL Scanner
* precense of robots.txt with only Allow statements
* HTTP headers check, certain headers should be present
* HTTP headers check, no version information should be divulged
* HTTP Error page, no product information and/of version information should be divulged

Information is stored in a Sqlite database and sql2html.py creates an index.html from that database

## Requirements
scirtscan.py assumes you have the following software in your path:
> https://github.com/santoru/shcheck  
> https://github.com/ssllabs/ssllabs-scan 

Also see requirements.txt and as usual perform the following command to satisfy those:
> pip3 install -r requirements.txt
 
(or use your OS package management tools)

## Input file
The input file is required it takes the form of a list of website names, e.g. :
> www.some-boring-website.com  
> www.another-dull-website.com  
> www.you-get-the-gist.com  

## Output
Output is generated in a newly created directory. The directory name is based on the date (YYYYMMDD). The output directory contains the sqlite file websites.db and the per website results log. 

## Usage
Run from the directory where the files are located:
> ./scirtscan.py -d websites.txt

The qualys ssltest can take up some time. The default in the script is to specify usecache, so the second time you run the script it will just get the results from the cache. Optional you can specify -xq to skip the Qualys check, for instance:
> ./scirtscan.py -d -xq websites.txt

if all goes well this will create a directory with the name of todays date in the format YYYYMMDD. The sqlite database with all results and the per website debug log files will be stored in that directory. Next run:
> ./sql2html.py -d

And that will create an index.html in that directory. Default sql2html.py will read the directory with today's date and write the index.html there If you want to proces another directory, you can specify that with the -p (path) option, for instance:
> ./sql2html.py -d -p 20221231

If you want to open that index file to view it in your browser and you're on a mac, type:
> open yyyymmdd/index.html (and yes, replace yyyymmdd with the current date)

for linux use:
> xdg-open yyyymmdd/index.html

If you want to put the files on a webserver, copy the yyyymmdd directory(s) to the webserver root. The file styles.css is used by sql2html.py to generate the index.html, after that it's not used anymore.

The webpage will look something like this:
![](https://raw.githubusercontent.com/beamzer/ScirtScan/main/scirtscan-table.png)

## Structure
The main python script (scirtscan.py) works with functions, you can easily comment out functions to test a single one, or add a new function for new checks. I will add an commandline option for this soon. 

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

## Upcoming features
* ~~A check for the presence of `.well-known/security.txt `~~
* A check for the precense of open directories
* more output options (excel, pie-charts, ... ?)

## License and Disclaimer
This software is licensed under GPL v3.0 as stated in [LICENSE](https://github.com/beamzer/ScirtScan/blob/main/LICENSE)
