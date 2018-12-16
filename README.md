DC Register Unofficial Open Data
================================

This is a repository of open data for the District of Columbia Register, the DC government's collection of administrative issuances, October 2009-present, from https://dcregs.dc.gov/default.aspx. Why? Because the DC website provides a hopelessly bad interface for actually finding anything.

The notices in the Register have been converted into browser and search engine friendly formats using ocrmypdf and tesseract (for PDFs) and LibreOffice (for Word docs).

Development
-----------

To run the scripts in this repository to build your own copy of our open data, you'll need an Ubuntu 18.04 machine. Install:

	apt-get install ocrmypdf
	pip3 install rtyaml tqdm python-magic

Then download the notices & metadata into `notices/*.blob` and `notices/*.yaml`:

	python3 download_dc_register_notices.py

Make symbolic links at `documents/*.{pdf,doc,docx,html,rtf}` to the raw notices files by automatically determining the file type of each notice:

	python3 make_document_symlinks.py

Produce new document files in alternative formats (OCR'd PDFs, plain text, and HTML):

	python3 make_document_formats.py

And finally produce `index.json` that is loaded by the website in `index.html`:

	python3 make_index.py

Deployment
----------

The site is currently hosted statically on AWS S3. Upload with:

	s3cmd -P --no-preserve sync index.* s3://dcregisterer/
	s3cmd -P --no-preserve -F sync documents/ s3://dcregisterer/documents/
