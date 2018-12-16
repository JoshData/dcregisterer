# Create symbolic links from the documents directory to the
# .blob files in the notices directory. Basically, we're
# just giving every notice blob a proper file extension.

import magic
import os.path
import tqdm

mime = magic.Magic(mime=True)

for blobfn in tqdm.tqdm(os.listdir("notices"), desc="creating symlinks"):
	# Skip .yaml metadata files.
	if not blobfn.endswith(".blob"):
		continue

	# Determine the file type of the notice document.
	file_type = mime.from_file("notices/" + blobfn)
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
	else:
		print(blobfn, "is a", file_type, "which we don't know how to handle.")
		continue # ?

	# Create symbolic link.
	# Note that when we OCR PDF's, we replace the symbolic link PDF
	# with a new PDF that has been OCR'd. As a result, os.path.islink
	# will return False and we'll leave the new file in place.
	linkfn = "documents/" + os.path.splitext(blobfn)[0] + "." + ext
	targetfn = "../notices/" + blobfn
	if os.path.islink(linkfn) and os.readlink(linkfn) != targetfn:
		# There is a link here already and it's pointing to the wrong place.
		os.unlink(linkfn)
	if not os.path.exists(linkfn):
		# There's no link or file yet, so create it.
		os.symlink(targetfn, linkfn)