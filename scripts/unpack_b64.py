import base64, gzip, hashlib, sys
src, dst = sys.argv[1], sys.argv[2]
data = gzip.decompress(base64.b64decode(open(src).read().strip()))
open(dst, "wb").write(data)
print(dst, hashlib.sha256(data).hexdigest())
