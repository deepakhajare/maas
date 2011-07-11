Build a cobbler image:
   $ time ./build-image -vv --preseed preseed.cfg oneiric amd64 8G

to use a proxy, edit preseed.cfg, add something like:
# Specifying the Mirror.
d-i   mirror/http/proxy string http://10.155.1.249:8000/

With correct IP and port.  This will work well with squid-deb-proxy
