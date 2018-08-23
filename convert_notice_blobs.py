# Scan the blobs we downloaded, whose file types are unknown,
# and symlink the file to the appropriate extension.

import glob
import magic
import os, os.path
import subprocess
import re
import tempfile
import shutil

mime = magic.Magic(mime=True)

conversions = {
	("doc", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("doc", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("docx", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("docx", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("rtf", "txt"): lambda fn : ['lowriter', '--convert-to', 'txt:Text (encoded):UTF8', '--outdir', os.path.dirname(fn), fn],
	("rtf", "html"): lambda fn : ['lowriter', '--convert-to', 'html:XHTML Writer File:UTF8', '--outdir', os.path.dirname(fn), fn],
	("pdf", "txt"): lambda fn : ['pdftotext', fn],
}

for blobfn in glob.glob("notices/*.blob"):
	# Determine the actual file type.
	file_type = mime.from_file(blobfn)
	if file_type == "application/pdf":
		ext = "pdf"
	elif file_type == "application/msword":
		ext = "doc"
	elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
		ext = "docx"
	elif file_type == "text/html":
		ext = "html"
	elif file_type == "text/rtf":
		ext = "rtf"
	elif file_type == "inode/x-empty":
		continue # ?
	else:
		raise ValueError(file_type)

	# Create symbolic link.
	# Note that when we OCR PDFs, we'll have a PDF file present but it
	# won't be a symlink back to the blob file.
	linkfn = os.path.splitext(blobfn)[0] + "." + ext
	targetfn = os.path.basename(blobfn)
	if os.path.islink(linkfn) and os.readlink(linkfn) != targetfn:
		# There is a link here already and it's pointing to the wrong place.
		os.unlink(linkfn)
	if not os.path.exists(linkfn):
		# There's no link or file yet, so create it.
		os.symlink(targetfn, linkfn)

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
			in_fn = os.path.splitext(blobfn)[0] + "." + in_format
			out_fn = os.path.splitext(blobfn)[0] + "." + out_format
			if os.path.exists(in_fn) and not os.path.exists(out_fn):
				subprocess.run(commandfunc(in_fn))
				did_conversion = True

				# If we just converted from pdf to text and the text layer
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
