import pysrt
import utils
from pathlib import Path

# input_dir = "input"
# output_dir = "output"

# for file in Path(input_dir).iterdir():
#   if file.is_file():
#     subs = pysrt.open( str(file) )
#     subs = utils.subs_add_notation(subs)
#     subs.save( str(output_dir) + "/" + str(file) )

# traditional way

input_file = "Game of Thrones - 2x08 - The Prince of Winterfell.720p.BluRay.ShAaNiG.HI.en.srt"
output_file = "OUT " + input_file

subs = pysrt.open( input_file )
subs = utils.subs_add_notation(subs)
subs.save( output_file )

