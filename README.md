# Zotero Kagi Summaries

This Python script helps you add `takeaway` summaries from Kagi's Universal Summarizer as child notes in your Zotero library.

## Requirements 

A few things we need: 

- An API key from Zotero and your library ID (this is a number displayed on the API key page)
- A token from Kagi (with some credits)
- An s3 compatible storage space (defaultly configured for Linode Objects) with bucket name, region name, access and secret keys
- `boto3` and `pyzotero` installed
- Python3 of some variety

## What?

The script will iterate through your online Zotero library and prompt you to send the attached PDF to the Kagi summarizer. Rather than the default summary which looks a lot like an abstract, we're using the "key moments" or `takeaway` setting to get a bulleted list of moments in the summarized PDF.

What we're doing is looping through your Zotero library and asking you if you want to send the attached item to Kagi. Because Zotero, for legal reasons, doesn't expose the PDFs in your library to the open internet, we're using an s3 compatible bridge in the middle – where we are temporarily storing PDFs to get summaries.

If the summarizer can work its mojo on your PDF, you will end up with a new child note containing the summary in your Zotero item in moments. 

## Why?

I found myself needing to summarize large numbers of PDFs as part of a literature review I was conducting. A twisted form of a title and abstract screening if you will. This process was tedious requiring middle-wear to upload PDFs, and manual copy-pasting to get child notes in Zotero. 

## The drawbacks

While this method is much faster than manually uploading and summarizing PDF files the API costs are rather extreme. I chewed through about $5USD doing maybe 12 articles.

Moreover, you'll likely run into several issues with the summarizer, because it's not that good at PDFs or academic articles – though this is not specific to this application.

## License

MIT

## What's next?

This works for my purposes for the moment. In the future I may be interested in turning this into something with a frontend and a simplified user experience accessing their Zotero library, etc. so this code may form the basis of something else I create.

## Ideas, problems?

Please submit issues/pull requests. Preferably if you know how to fix it, just do it, and I'll review and merge – I don't have any time to commit to this work. Everything is completely unsupported and I take no responsibility for breaking anything in your library, etc, etc. 

Thanks for looking :-) 
