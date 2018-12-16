# Run conversions to generate browser- and search-engine-
# friendly formats of notices.

import os, os.path
import subprocess
import re
import tempfile
import shutil
import tqdm

conversions = {
	("doc", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("doc", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("docx", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("docx", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("rtf", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("rtf", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("pdf", "txt"): lambda fn : ['pdftotext', fn],
}

# Get a list of notice documents.
notices = [fn.replace(".blob", "")
           for fn in os.listdir("notices")
           if fn.endswith(".blob")]

# Process them out of order.
import random
random.shuffle(notices)

# Process each notice.
for noticeId in tqdm.tqdm(notices, desc="converting formats"):
	# Convert file to alternate file formats. Loop until there are no
	# converions on a pass over all of the possible conversions we
	# can do.
	did_conversion = True
	while did_conversion:
		did_conversion = False

		# For each "format => format" possible conversion, see if we
		# have a file in the input format and have not yet generated
		# (or acquired) a file in the output format.
		for (in_format, out_format), commandfunc in conversions.items():
			in_fn = "documents/" + noticeId + "." + in_format
			out_fn = "documents/" + noticeId + "." + out_format
			if os.path.exists(in_fn) and not os.path.exists(out_fn):
				# Run a conversion.
				subprocess.run(commandfunc(in_fn))
				if not os.path.exists(out_fn):
					print("File did not convert?", in_fn, "=>", out_format)
					print(" ".join(commandfunc(in_fn)))
					print()
					continue
				else:
					did_conversion = True

				# If we just converted from PDF to text and the text layer
				# is empty, attempt to OCR the PDF and then re-convert it.
				if (in_format, out_format) == ('pdf', 'txt') and os.stat(out_fn).st_size < 512:
					with open(out_fn) as f:
						if not re.search(r"\w", f.read()):
							# The converted file has no content. Try OCR'ing
							# the PDF. The PDF may be a symlink to the orginal
							# blob, and we don't want to overwrite the blob,
							# but we do want to replace the PDF with the OCR'd
							# PDF, so copy the PDF to a temporary file, then
							# unlink the PDF file, and then save the OCR'd
							# version back.
							with tempfile.NamedTemporaryFile() as tf:
								shutil.copy(in_fn, tf.name)
								os.unlink(in_fn)
								subprocess.run(["ocrmypdf", "-l", "eng", "--rotate-pages", "--deskew", tf.name, in_fn])

							# Now try converting the PDF to text again.
							subprocess.run(commandfunc(in_fn))
