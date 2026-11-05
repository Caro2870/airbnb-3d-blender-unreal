# python cvars_dll.py <pattern> <dll...> : print UTF-16 strings in binaries that contain <pattern> (to find cvar names)
import re, sys

pat = sys.argv[1].encode("utf-16-le")
seen = set()
for path in sys.argv[2:]:
    data = open(path, "rb").read()
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){6,}", data):
        s = m.group()
        if pat in s:
            t = s.decode("utf-16-le")
            if t not in seen:
                seen.add(t)
                print(path.split("\\")[-1], "|", t[:200])
