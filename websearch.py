#!/usr/bin/env python2
import argparse
import re
import socket
import sys
from collections import deque

BUFFER_SIZE = 4096
TIMEOUT = 5


def get_domain_resource(url):
    """Return domain and resource for the given URL."""
    domain = re.search('([^/]+)', url).group(1)
    resource = re.search('([^/]+(.*))', url).group(2)
    if resource == '':
        resource = '/'
    return domain, resource


def is_below(root_domain, root_resource, domain, resource):
    """Return whether the given domain and resource are hierarchically below the root."""
    if domain != '' and (domain != root_domain or not resource.startswith(root_resource)):
        return False
    return True


def search(url, query, root_domain, root_resource, requested, queue):
    """Perform search for query string at given URL.
    
    args:
    url -- the URL of the site to search in
    query -- the string to search for
    root_domain -- the domain of the root search URL
    root_resource -- the resource of the root search URL
    requested -- a set containing all URLs previously visited
    queue -- a deque of URLs to search in recursively
    """
    if ':' in url:
        if not url.startswith('http://'):
            return
        url = url[7:]  # Remove the protocol for ease of later parsing
    if url in requested:
        return
    requested.add(url)
    domain, resource = get_domain_resource(url)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        s.connect((domain, 80))

        message = 'GET {} HTTP/1.1\r\nHost: {}\r\nAccept: text/html\r\n\r\n'.format(resource, domain).encode()
        bytes_sent = s.send(message)
        if bytes_sent == 0:
            print('Could not send to {} using message: {}'.format(domain, repr(message)))
            s.close()
            return

        page = s.recv(BUFFER_SIZE)

        header = page.split(b'\r\n\r\n')[0]
        print(header)

        try:
            code = re.search('HTTP\S*\s+(\d{3})', header).group(1)
            if code[0] in '45':
                print('Error code {} for URL {}\n'.format(code, url))
                return
            if code[0] == '3':
                location = re.search('Location:\s*(\S+)', header, re.I).group(1)
                if ':' in location:
                    if not location.startswith('http://'):
                        print('Redirect location ({}) does not use http\n'.format(location))
                        return
                    location = location[7:]  # Remove the protocol for ease of later parsing
                new_domain, new_resource = get_domain_resource(location)
                if not is_below(root_domain, root_resource, new_domain, new_resource):
                    print('Redirect location ({}) not below root location ({})\n'.format(url, location))
                    return
                print('Redirecting from {} to {}'.format(url, location))
                search(location, query, root_domain, root_resource, requested, queue)
                return
            if code != '200':
                print('Unexpected code {} for URL {}\n'.format(code, url))
                return

            content_length = int(re.search('Content-Length:\s*(\d+)', header, re.I).group(1))
            if content_length > 50000:
                print('Page size ({}) of {} exceeds limit\n'.format(content_length, url))
                s.close()
                return

            content_type = re.search('Content-Type:\s*(\S+)', header, re.I).group(1)
            if content_type[-1] == ';':
                content_type = content_type[:-1]
            if content_type != 'text/html':
                print('Invalid content type ({}) for {}\n'.format(content_type, url))
                s.close()
                return

        except AttributeError as e:  # Could be another issue, but very likely to be a malformed or incomplete header
            print('Error: invalid header for URL {}\n{}\n'.format(url, header))
            return

        page = page[len(header) + 4:]  # Remove the header from the rest of the page
        while len(page) < content_length:
            page += s.recv(BUFFER_SIZE)

        matches = re.findall(query, page)
        if matches is None:
            total = 0
        else:
            total = len(matches)
        print('Found {} occurrences of "{}" at URL {}\n'.format(total, query, url))

        if recursive:
            new_urls = re.findall('<[^(<>)]*(src|href)=\"(.+?)\"[^(<>)]*>', page, re.I)
            for i in range(len(new_urls)):
                new_url = new_urls[i][1]
                if ':' in new_url:
                    if not new_url.startswith('http://'):
                        continue
                    absolute = True
                    new_url = new_url[7:]
                else:
                    absolute = False

                if absolute:
                    new_domain, new_resource = get_domain_resource(new_url)
                elif new_url[0] == '/':
                    new_domain = root_domain
                    new_resource = new_url
                else:
                    new_domain = root_domain
                    new_resource = re.search('(.*/)', resource).group(1) + new_url


                # Check if below current root
                if not is_below(root_domain, root_resource, new_domain, new_resource):
                    continue
                queue.append(root_domain + new_resource)

    except socket.timeout as e:
        print('Conection to {} timed out'.format(domain))
        s.close()
        return

    except socket.error as e:
        print('Could not connect to {}\n{}'.format(domain, e))
        s.close()
        return

    s.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', action='store_true', help='perform recursive search')
    parser.add_argument('-q', '--query', help='term to query in pages', required=True)
    parser.add_argument('roots', nargs='+')
    args = parser.parse_args()
    recursive = args.r

    requested = set()  # Keeps track of all URLs visited

    for root in args.roots:
        root_url = root
        if ':' in root_url:
            if not root_url.startswith('http://'):
                continue
            root_url = root_url[7:]  # Remove the protocol for ease of later parsing
        root_domain, root_resource = get_domain_resource(root_url)
        
        queue = deque([root_url])

        while len(queue) > 0:
            url = queue.popleft()
            if len(requested) > 1000:
                print('Page limit exceeded. Exiting')
                sys.exit()
            if len(url) > 500:
                print('URL length ({}) exceeds limit'.format(len(url)))
                continue

            search(url, args.query, root_domain, root_resource, requested, queue)
