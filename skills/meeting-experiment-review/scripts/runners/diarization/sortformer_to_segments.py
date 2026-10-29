"""Convert fluidaudiocli sortformer/lseend --output JSON to the segment format used by score.py."""
import json, sys

d = json.load(open(sys.argv[1]))
segs = [{"speaker_id": s["speaker"], "start_seconds": s["startTimeSeconds"], "end_seconds": s["endTimeSeconds"]}
        for s in d["segments"]]
json.dump(segs, open(sys.argv[2], "w"))
