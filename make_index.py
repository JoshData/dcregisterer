# Make "index.json" for use in index.html.

import os
import os.path
import json
import tqdm
import rtyaml
import dateutil.parser

# Get a list of notice documents.
notices = [fn.replace(".blob", "")
           for fn in os.listdir("notices")
           if fn.endswith(".blob")]

def parse_date(datestr):
	return {
		"iso": dateutil.parser.parse(datestr).isoformat(),
		"str": datestr,
	}

# Build the index.
table = []
for noticeId in tqdm.tqdm(notices):
	# Load metadata.
	with open("notices/{}.yaml".format(noticeId)) as f:
		metadata = rtyaml.load(f)

	# Scan for available file formats.
	has_formats = []
	file_formats = ("pdf", "html", "txt", "doc")
	for fmt in file_formats:
		fmtfn = "documents/{}.{}".format(noticeId, fmt)
		if os.path.exists(fmtfn):
			has_formats.append([fmt.upper(), fmtfn])
	has_formats.append(["DC.gov", metadata["File"]])

	table.append({
		"category": metadata["RegCat"],
		"subcategory": metadata.get("SubCat"),
		"agency": metadata.get("AgencyName"),
		"title": metadata["Subject"],
		"pubDate": parse_date(metadata["PubDate"]),
		"issueDate": parse_date(metadata["RegIssueDate"]),
		"links": has_formats,
	})

# Sort the index.
table.sort(key = lambda notice : (notice['pubDate']['iso'], notice['title']))

# Write the index.
with open("index.json", "w") as f:
	json.dump(table, f, indent=1)