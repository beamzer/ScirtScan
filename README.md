# ScirtScan
Python script to scan a list of websites with a number of checks:
* TLS/SSL check based on the Qualys SSL Scanner
* precense of robots.txt with only Allow statements
* HTTP headers check, certain headers should be present
* HTTP headers check, no version information should be divulged
* HTTP Error page, no product information and/of version information should be divulged

Information is stored in a Sqlite database and sql2html.py creates an index.html from that database
