# ScirtScan
## This is work in progress, your mileage may vary

Python script to scan a list of websites with a number of checks:

* TLS/SSL check based on the Qualys SSL Scanner
* precense of robots.txt with only Allow statements
* HTTP headers check, certain headers should be present
* HTTP headers check, no version information should be divulged
* HTTP Error page, no product information and/of version information should be divulged

Information is stored in a Sqlite database and sql2html.py creates an index.html from that database

## Input file
The input file is required (-i) it takes the form of a list of website names, e.g. :
> www.google.com  
> www.microsoft.com  
> www.apple.com  

## Output
Output is generated in a newly created directory. The directory name is based on the date (YYYYMMDD). The output directory containss the sqlite file websites.db and the per website results log.

## Requirements
scirtscan.py assumes you have the following software in your path:
> https://github.com/santoru/shcheck  
> https://github.com/ssllabs/ssllabs-scan  

## Usage
Run from the directory where the files are located:
> ./scirtscan.py -d -i websites.txt

if all goes well this will create a directory with the name of todays date in the format YYYYMMDD. The sqlite database with all results and the per website debug log files will be stored in that directory. Next run:
> ./sql2html.py -d

And that will create an index.html in that directory. If you want to open that index file to view it in your browser and you're on a mac, type:
> open yyyymmdd/index.html (and yes, replace yyyymmdd with the current date)

for linux use:
> xdg-open yyyymmdd/index.html

If you want to put the files on a webserver, put the index.html one level up from the yyyymmdd directory so the links to the per website debug files still work. The file styles.css is used by sql2html.py to generate the index.html, so after that it's not used anymore.

## Structure
The main python script (scirtscan.py) works with functions, you can easily comment out functions to test a single one, or add a new function for new checks. I will add an commandline option for this soon. 

## Bugs
At the moment sql2html.py doesn't like it when fields in the database are empty. I will fix this.

## Upcoming features
* A check for the presence of `.well-known/security.txt `
* more output options (excel, pie-charts, ... ?)
* option for sql2html to tailor output to be put on a webserver
