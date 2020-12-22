# websearch
Basic web crawler that searches pages within a domain.

## Basic info
Takes root URLs and searches the given pages for the query term. Can be set to recursively search any links on the page, provided that they are below the root URL.  

(from the help text)  

usage: findweb.py [-h] [-r] -q QUERY roots [roots ...]  

positional arguments:  
&nbsp;&nbsp;roots  

optional arguments:  
&nbsp;&nbsp;-h, --help | show this help message and exit  
&nbsp;&nbsp;-r | perform recursive search  
&nbsp;&nbsp;-q QUERY, --query QUERY | term to query in pages  
