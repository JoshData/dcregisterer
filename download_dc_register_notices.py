import base64
import os
import urllib.request
import urllib.parse, urllib.error
import re
import lxml.html
import tqdm
from datetime import datetime
import rtyaml
import time

def scrape_with_retry(f):
	# The DC.gov website gives a lot of intermittent
	# Connection Reset errors, so when we get that
	# wait two seconds and then try again, up to five
	# times, and if we get it six times then raise
	# the error.
	def g(*args, **kwargs):
		counter = 0
		while True:
			try:
				return f(*args, **kwargs)
			except (ConnectionResetError, urllib.error.URLError):
				time.sleep(3)
				counter += 1
				if counter > 6:
					raise
	return g


@scrape_with_retry
def download_url(url):
	return urllib.request.urlopen(url).read().decode("utf8")


@scrape_with_retry
def download_postback(url, targetid, pagesource):
	# Unfortunately since the site is generated using ASP.NET "postback" forms,
	# we have to craft a POST body that works. We copy all of the hidden form
	# fields, and then add EVENTTARGET holding the id of the "View text" link.
	form = { }
	for key, value in re.findall('<input type="hidden" name="([^"\\s]*)".*value="([^"\\s]*)"', pagesource):
		form[key] = value
	form['__EVENTTARGET'] = targetid
	form['__EVENTARGUMENT'] = ''
	body = urllib.parse.urlencode(form).encode("utf8")
	return urllib.request.urlopen(urllib.request.Request(
		url,
		data=body,
		headers={
			"Content-Type": "application/x-www-form-urlencoded",
			"Content-Length": str(len(body)),
			}))


@scrape_with_retry
def download_dc_register_notice(noticeId):
	# Download the overview page for a DC Register notice, e.g.:
	# https://dcregs.dc.gov/Common/NoticeDetail.aspx?noticeId=N0072841
	url = "https://dcregs.dc.gov/Common/NoticeDetail.aspx?noticeId=" + noticeId
	page = urllib.request.urlopen(url)
	return download_dc_register_notice2(noticeId, page)


def download_dc_register_notice2(noticeId, page):
	# Read page.
	url = page.geturl()
	page = page.read().decode("utf8")

	# Parse the page.
	dom = lxml.html.fromstring(page)

	# Find metadata elements --- these elements all have id="MainContent_lbl...".
	metadata = { }
	for node in dom.xpath("//*[@id]"):
		m = re.match(r"MainContent_(lbl|lnk)([A-Za-z].*)", node.get("id"))
		if m:
			id = m.group(2)
			if id in ("SubCategory", "EffectiveDateLabel"):
				# these are actually labels and not values
				continue
			inner_text = (node.text or '') + ''.join(etree.tostring(e) for e in node)
			inner_text = re.sub(r'\s+', ' ', inner_text) # cleanse HTML whitespace
			metadata[id] = inner_text

	if not metadata or metadata['Subject'] == "":
		raise ValueError("Subject is empty? " + noticeId)

	# Follow the "View text" link to get the text of the notice.
	document = download_postback(url, 'ctl00$MainContent$lnkNoticeFile', page)

	# Update the metadata with the response headers of the download.
	metadata["textHttpHeaders"] = dict(document.info())

	# Save the metadata and the blob.
	os.makedirs("notices", exist_ok=True)
	with open("notices/" + noticeId + ".yaml", "w") as f:
		rtyaml.dump(metadata, f)
	with open("notices/" + noticeId + ".blob", "wb") as f:
		f.write(document.read())

	# TODO: Check that the blob does not contain "Oops!!" which probably
	# indicates we failed to actually get the file.

	return metadata

def download_mayors_orders_for_month_year(year, month):
	# Download the notice listing page.
	url = "https://dcregs.dc.gov/Common/MayorOrders.aspx?Type=MayorOrder&Date={}-{:02d}-01".format(year, month)
	print(url + "...")
	page = download_url(url)

	# Follow the "Order Number" links, which go to a Notice overview page.
	dom = lxml.html.fromstring(page)
	for link in dom.xpath("//a[@id]"):
		if link.get('id').startswith("MainContent_rpt_orderList_lnkFile_"):
			m = re.match(r"javascript:__doPostBack\('(.*\$lnkFile)',''\)", link.get("href"))
			if m:
				# At this point we would like to not follow the link to the notice if
				# we already have it, but on this page we don't have the notice ID,
				# only the mayor's order ID, and we don't have notices indexed by
				# mayor's order number, so we have to fetch it.
				doc = download_postback(url, m.group(1), page)
				m = re.match(r"https://dcregs.dc.gov/Common/NoticeDetail\.aspx\?noticeId=(N\d+)", doc.geturl())
				if m:
					download_dc_register_notice2(m.group(1), doc)

def download_all_mayors_orders():
	# The first month-year with records.
	year = 2009
	month = 10

	# Advance over months until we hit today.
	while (year < datetime.now().year) or (month < datetime.now().month):
		download_mayors_orders_for_month_year(year, month)
		month += 1
		if month == 13:
			month = 1
			year += 1

def download_dc_register_notices():
	# Use the per-agency listing pages to download all DC Register notices.
	# This is preferable to using the Mayor's Order listing page because only
	# on these pages do we have Notice IDs, so we can skip downloading notices
	# that we already have.

	# Get the agency list.
	url = "https://dcregs.dc.gov/default.aspx"
	print(url + "...")
	page = download_url(url)
	dom = lxml.html.fromstring(page)
	agencies = dom.xpath("//select[@id='MainContent_ddlDcmrAgency']/option")
	agencies = [node.text for node in agencies]
	
	# Get the complete set of notice IDs across all agencies.
	noticeids = set()
	for agency in tqdm.tqdm(agencies, desc="fetching notice IDs"):
		# Download the notice listing page for this agency.
		url = "https://dcregs.dc.gov/Common/DCR/SearchAgency.aspx?AgencyName=" + urllib.parse.quote(agency)

		# Try to get list from cache. Querying the remote server *and* parsing the
		# large HTML responses are both quite slow.
		cache_key = base64.b64encode(url.encode("utf8")).decode("ascii").replace("/", "+")
		cache_fn = "cache/" + cache_key + ".html"
		if os.path.exists(cache_fn):
			with open(cache_fn) as f:
				agency_noticeids = set(f.read().split("\n"))
				agency_noticeids -= { "" }

		# Fetch anew.
		else:
			page = download_url(url)
			dom = lxml.html.fromstring(page)
			agency_noticeids = set()
			for link in dom.xpath("//a[@id]"):
				if link.get('id').startswith("MainContent_rpt_AgencyList_lnkFile_"):
					agency_noticeids.add(link.text)

			# Write to cache.
			os.makedirs("cache", exist_ok=True)
			with open(cache_fn, "w") as f:
				f.write("\n".join(agency_noticeids))

		noticeids |= agency_noticeids

	# Remove notices that we already have.
	already_have_notice_ids = set(
		fn.replace(".yaml", "")
		for fn in os.listdir("notices")
		if fn.endswith(".yaml")
	)
	noticeids = set(noticeids) - already_have_notice_ids
	
	# Download notices.
	for noticeId in tqdm.tqdm(noticeids, desc="fetching notices"):
		download_dc_register_notice(noticeId)

#download_dc_register_notice("N0072841")
#download_all_mayors_orders()
download_dc_register_notices()
