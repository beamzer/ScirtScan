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
> www.amazon.com  

## Output
Output is generated in a newly created directory. The directory name is based on the date (YYYYMMDD). The output directory containss the sqlite file websites.db and the per website results log.

##Requirements
scirtscan.py assumes you have the following software in your path:
> https://github.com/santoru/shcheck  
> https://github.com/ssllabs/ssllabs-scan  


## Structure
The main python script (scirtscan.py) works with function, you can easily comment out functions to test a single one, or add a new function for new checks. I will add an commandline option for this in the very near future. 
