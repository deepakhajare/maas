#!/bin/sh
#
# This script carries inside it multiple files.  When executed, it creates
# the files into a temporary directory, and then calls the 'main' function
#
# main does a run-parts of all "scripts" and then calls home to maas with
# maas-signal, posting output of each of the files added with add_script()
#
#### script setup ######
TEMP_D=$(mktemp -d "${TMPDIR:-/tmp}/${0##*/}.XXXXXX")
SCRIPTS_D="${TEMP_D}/scripts"
BIN_D="${TEMP_D}/bin"
OUT_D="${TEMP_D}/out"
PATH="$BIN_D:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
trap cleanup EXIT

mkdir -p "$BIN_D" "$OUT_D" "$SCRIPTS_D"

### some utility functions ####
writefile() {
   cat > "$1"
   chmod "$2" "$1"
}
add_bin() {
   cat > "${BIN_D}/$1"
   chmod "${2:-755}" "${BIN_D}/$1"
}
add_script() {
   cat > "${SCRIPTS_D}/$1"
   chmod "${2:-755}" "${SCRIPTS_D}/$1"
}
cleanup() {
   [ -n "${TEMP_D}" ] || rm -Rf "${TEMP_D}"
}

find_creds_cfg() {
   local config="" file="" found=""

   # if the config location is set in environment variable, trust it
   [ -n "${COMMISSIONING_CREDENTIALS_URL}" ] &&
      _RET="${COMMISSIONING_CREDENTIALS_URL}" && return

   # go looking for local files written by cloud-init
   for file in /etc/cloud/cloud.cfg.d/*cmdline*.cfg; do
      [ -f "$file" ] && _RET="$file" && return
   done

   local opt="" cmdline=""
   if [ -f /proc/cmdline ] && read cmdline < /proc/cmdline; then
      # search through /proc/cmdline arguments
      # cloud-config-url trumps url=
      for opt in $cmdline; do
         case "$opt" in
            url=*)
               found=${opt#url=};;
            cloud-config-url=*)
               _RET="${opt#*=}"
               return 0;;
         esac
      done
   fi
}

signal() {
   maas-signal "--config=${CRED_CFG}" "$@"
}

fail() {
   [ -z "$CRED_CFG" ] || signal FAILED "$1"
   echo "FAILED: $1" 1>&2;
   exit 1
}

main() {
   # the main function, actually execute stuff that is written below
   local script total=0 creds=""

   find_creds_cfg ||
      fail "failed to find credential config"
   creds="$_RET"

   # get remote credentials into a local file
   case "$creds" in
      http://*|https://*)
         wget "$creds" -O "${TEMP_D}/my.creds" ||
            fail "failed to get credentials from $cred_cfg"
         creds="${TEMP_D}/my.creds"
         ;;
   esac

   # use global name read by signal() and fail
   CRED_CFG="$creds"

   # just get a count of how many scripts there are for progress reporting
   for script in "${SCRIPTS_D}/"*; do
      [ -x "$script" -a -f "$script" ] || continue
      total=$(($total+1))
   done

   local cur=1 numpass=0 name="" failed=""
   for script in "${SCRIPTS_D}/"*; do
      [ -f "$script" -a -f "$script" ] || continue
      name=${script##*/}
      signal WORKING "starting ${script##*/} [$cur/$total]"
      "$script" > "${OUT_D}/${name}.out" 2> "${OUT_D}/${name}.err"
      ret=$?
      signal WORKING "finished $name [$cur/$total]: $ret"
      if [ $ret -eq 0 ]; then
          numpass=$(($numpass+1))
          failed="${failed} ${name}"
      fi
      cur=$(($cur+1))
   done

   # get a list of all files created, ignoring empty ones
   local fargs=""
   for file in "${OUT_D}/"*; do
      [ -f "$file" -a -s "$file" ] || continue
      fargs="$fargs --file=${file##*/}"
   done

   if [ $numpass -eq $total ]; then
      ( cd "${OUT_D}" &&
         signal $fargs OK "finished [$passed/$count]" )
      return 0
   else
      ( cd "${OUT_D}" &&
         signal $fargs OK "failed [$passed/$count] ($failed)" )
      return $(($count-$numpass))
   fi

}

### begin writing files ###
add_script "01-lshw" <<"END_LSHW"
#!/bin/sh
lshw -xml
END_LSHW

add_bin "maas-signal" <<"END_MAAS_SIGNAL"
#!/usr/bin/python

import mimetypes
import oauth.oauth as oauth
import os.path
import random
import string
import sys
import time
import urllib2
import yaml

MD_VERSION = "2012-03-01"
VALID_STATUS = ("OK", "FAILED", "WORKING")


def _encode_field(field_name, data, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"' % field_name,
            '', str(data))


def _encode_file(name, fileObj, boundary):
    return ('--' + boundary,
            'Content-Disposition: form-data; name="%s"; filename="%s"' %
                (name, name),
            'Content-Type: %s' % _get_content_type(name),
            '', fileObj.read())


def _random_string(length):
    return ''.join(random.choice(string.letters) for ii in range(length + 1))


def _get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


def encode_multipart_data(data, files):
    """Create a MIME multipart payload from L{data} and L{files}.

    @param data: A mapping of names (ASCII strings) to data (byte string).
    @param files: A mapping of names (ASCII strings) to file objects ready to
        be read.
    @return: A 2-tuple of C{(body, headers)}, where C{body} is a a byte string
        and C{headers} is a dict of headers to add to the enclosing request in
        which this payload will travel.
    """
    boundary = _random_string(30)

    lines = []
    for name in data:
        lines.extend(_encode_field(name, data[name], boundary))
    for name in files:
        lines.extend(_encode_file(name, files[name], boundary))
    lines.extend(('--%s--' % boundary, ''))
    body = '\r\n'.join(lines)

    headers = {'content-type': 'multipart/form-data; boundary=' + boundary,
               'content-length': str(len(body))}

    return body, headers


def oauth_headers(url, consumer_key, token_key, token_secret, consumer_secret):
    consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
    token = oauth.OAuthToken(token_key, token_secret)
    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauth.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_token': token.key,
        'oauth_consumer_key': consumer.key,
    }
    req = oauth.OAuthRequest(http_url=url, parameters=params)
    req.sign_request(oauth.OAuthSignatureMethod_PLAINTEXT(),
        consumer, token)
    return(req.to_header())


def geturl(url, creds, headers=None, data=None):
    # takes a dict of creds to be passed through to oauth_headers
    #   so it should have consumer_key, token_key, ...
    if headers is None:
        headers = {}
    else:
        headers = dict(headers)

    if creds.get('consumer_key', None) != None:
        headers.update(oauth_headers(url,
            consumer_key=creds['consumer_key'], token_key=creds['token_key'],
            token_secret=creds['token_secret'],
            consumer_secret=creds['consumer_secret']))
    req = urllib2.Request(url=url, data=data, headers=headers)
    return(urllib2.urlopen(req).read())

def read_config(url, creds):
    if url.startswith("http://") or url.startswith("https://"):
        cfg_str = urllib2.urlopen(urllib2.Request(url=url))
    else:
        if url.startswith("file://"):
            url = url[7:]
        cfg_str = open(url,"r").read()

    cfg = yaml.load(cfg_str)

    # support reading cloud-init config for MAAS datasource
    if 'datasource' in cfg:
        cfg = cfg['datasource']['MAAS']

    for key in creds.keys():
        if key in cfg and creds[key] == None:
            creds[key] = cfg[key]

def fail(msg):
    sys.stderr.write("FAIL: %s" % msg)
    sys.exit(1)


def main():
    """
    Call with single argument of directory or http or https url.
    If url is given additional arguments are allowed, which will be
    interpreted as consumer_key, token_key, token_secret, consumer_secret
    """
    import argparse
    import pprint

    parser = argparse.ArgumentParser(
        description='send signal operation and optionally post files to MAAS')
    parser.add_argument("--config", metavar="file",
        help="specify config file", default=None)
    parser.add_argument("--ckey", metavar="key",
        help="the consumer key to auth with", default=None)
    parser.add_argument("--tkey", metavar="key",
        help="the token key to auth with", default=None)
    parser.add_argument("--csec", metavar="secret",
        help="the consumer secret (likely '')", default="")
    parser.add_argument("--tsec", metavar="secret",
        help="the token secret to auth with", default=None)
    parser.add_argument("--apiver", metavar="version",
        help="the apiver to use ("" can be used)", default=MD_VERSION)
    parser.add_argument("--url", metavar="url",
        help="the data source to query", default=None)
    parser.add_argument("--file", dest='files',
        help="file to post", action='append', default=[])

    parser.add_argument("status",
        help="status", choices=VALID_STATUS, action='store')
    parser.add_argument("message", help="optional message",
        default="", nargs='?')

    args = parser.parse_args()

    creds = {'consumer_key': args.ckey, 'token_key': args.tkey,
        'token_secret': args.tsec, 'consumer_secret': args.csec,
        'metadata_url': args.url}

    if args.config:
        read_config(args.config, creds)

    url = creds.get('metadata_url', None)
    if not url:
        fail("Url must be provided either in --url or in config\n")
    url = "%s/%s/" % (url, args.apiver)

    params = {
        "op": "signal",
        "status": args.status,
        "error": args.message}

    files = {}
    for fpath in args.files:
        files[os.path.basename(fpath)] = open(fpath, "r")

    data, headers = encode_multipart_data(params, files)

    exc = None
    msg = ""

    try:
        payload = geturl(url, creds=creds, headers=headers, data=data)
        if payload != "OK":
            raise TypeError("Unexpected result from call: %s" % payload)
        else:
            msg = "Success"
    except urllib2.HTTPError as exc:
        msg = "http error [%s]" % exc.code
    except urllib2.URLError as exc:
        msg = "url error [%s]" % exc.reason
    except socket.timeout as exc:
        msg = "socket timeout [%s]" % exc
    except TypeError as exc:
        msg = exc.message
    except Exception as exc:
        msg = "unexpected error [%s]" % exc
    
    sys.stderr.write("%s\n" % msg)
    sys.exit((exc is None))

if __name__ == '__main__':
    main()
END_MAAS_SIGNAL

main
exit
