# Make "index.json" for use in index.html.

import glob
import rtyaml
import os.path
import json
import tqdm

table = []
for fn in tqdm.tqdm(sorted(glob.glob("notices/*.yaml"))):
	# Load metadata.
	with open(fn) as f:
		metadata = rtyaml.load(f)

	# Scan for available file formats.
	has_formats = []
	file_formats = ("pdf", "html", "txt", "doc")
	for fmt in file_formats:
		fmtfn = os.path.splitext(fn)[0] + "." + fmt
		if os.path.exists(fmtfn):
			has_formats.append([fmt.upper(), fmtfn])
	has_formats.append(["DC.gov", metadata["File"]])

	table.append({
		"category": metadata["RegCat"],
		"subcategory": metadata.get("SubCat"),
		"agency": metadata.get("AgencyName"),
		"title": metadata["Subject"],
		"pubDate": metadata["PubDate"],
		"issueDate": metadata["RegIssueDate"],
		"links": has_formats,
	})

with open("index.json", "w") as f:
	json.dump(table, f, indent=1)