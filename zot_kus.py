import requests
import boto3
from pyzotero import zotero

### API Configurations ###
# Zotero API key
api_key = 'XXX'
# Zotero library ID
library_id = '1234'
# What kind of library is it
library_type = 'user'  # or 'group'
# Kagi token
TOKEN = 'AbC_DefG'
# Kagi endpoint
base_url = 'https://kagi.com/api/v0/summarize'
# Linode Objects/S3 bucket name
bucket_name = 'zotsummariser'
# Linode Objects/S3 config:
s3 = boto3.client(
    's3',
    aws_access_key_id='XXX',
    aws_secret_access_key='XXX',
    region_name='us-southeast-1',
    endpoint_url='https://XXX.us-southeast-1.linodeobjects.com'
)

### API setup ###
zot = zotero.Zotero(library_id, library_type, api_key)
headers = {'Authorization': f'Bot {TOKEN}'}

### Function to send a publicly acessible URL to Kagi for summary ###
def summarize_pdf(pdf_url):
    params = {"url": pdf_url, "summary_type": "takeaway", "engine": "cecil"} # we want this as a takeaway because most articles have abstracts already; cecil is the default engine
    response = requests.get(base_url, headers=headers, params=params)
    response_json = response.json()
    # print(response_json)  # Debug line to print the entire response
    
    if 'error' in response_json:
        error_info = {
            'error': {
                'code': response_json['error'][0].get('code', 'Unknown code'),
                'msg': response_json['error'][0].get('msg', 'Unknown error')
            }
        }
        return error_info
    
    summary = response_json.get('data', {}).get('output', '')
    return {'summary': summary}

### Function to download a PDF from Zotero's private storage ### 
def download_pdf(zot, item_key, file_path):
    download_url = f"https://api.zotero.org/users/{library_id}/items/{item_key}/file/view"
    response = requests.get(download_url, headers={'Authorization': f'Bearer {api_key}'}, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    else:
        print(f"Failed to download PDF: {response.status_code}")
        

### Function to upload the downloaded PDF to an s3 equivalent ###
def upload_pdf(s3, file_path, bucket_name, object_name):
    try:
        s3.upload_file(file_path, bucket_name, object_name)
        #print(f"PDF uploaded to Linode: {object_name}")
    except Exception as e:
        print(f"Failed to upload PDF: {str(e)}")

### Function to get a publicly accessible URL out of said s3 service ###
def generate_presigned_url(s3, bucket_name, object_name, expiration=3600):
    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration
        )
        return response
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return None

### Function to remove summarised PDFs ###
def delete_pdf(s3, bucket_name, object_name):
    try:
        s3.delete_object(Bucket=bucket_name, Key=object_name)
        print(f"PDF deleted from Linode: {object_name}")
    except Exception as e:
        print(f"Failed to delete PDF: {str(e)}")

### Function to save the summary to Zotero ###
def save_summary_to_zotero(zot, parent_item_key, summary):
    try:
        note = {
            "itemType": "note",
            "note": summary,
            "tags": [],
            "parentItem": parent_item_key
        }
        # Wrapping the note dictionary in a list as create_items() expects a list of items
        response = zot.create_items([note])
        if response['successful']:
            for key, value in response['successful'].items():
                print(f"Summary saved to Zotero with key: {value['key']}")
        else:
            print(f"Failed to save summary to Zotero: {response}")
    except Exception as e:
        print(f"Error saving summary to Zotero: {str(e)}")
        
### Function to iterate over the library and ask the user for input if we want to get the attachment ###
def get_pdf_attachments(zot):
    items = zot.top(limit=150)  # how many items do we want to go through (newest to oldest)
    for item in items:
        # Get item details for user confirmation
        title = item['data'].get('title', 'Unknown Title')
        date = item['data'].get('date', 'Unknown Date')
        creators = item['data'].get('creators', [])
        authors = ", ".join([f"{author.get('firstName', 'Unknown')} {author.get('lastName', 'Unknown')}" for author in creators if author.get('creatorType') == 'author'])
        print(f"\nTitle: {title}\nAuthors: {authors}\nDate: {date}")
        user_input = input("Would you like to summarize this item y/n? ")
        if user_input.lower() == 'y':
            # find the PDF type child items if they exist (if not we just skip them unceremoniously)
            child_items = zot.children(item['key'])
            for child in child_items:
                if child['data']['itemType'] == 'attachment' and child['data']['contentType'] == 'application/pdf':
                    pdf_file_path = f"{child['key']}.pdf"
                    download_pdf(zot, child['key'], pdf_file_path)
                    object_name = f"pdfs/{pdf_file_path}"
                    upload_pdf(s3, pdf_file_path, bucket_name, object_name)
                    # pdf_linode_url = f"https://{bucket_name}.us-southeast-1.linodeobjects.com/{object_name}"
                    pdf_linode_url = generate_presigned_url(s3, bucket_name, object_name)
                    
                    # User verification step
                    print(f"PDF uploaded to Linode: {pdf_linode_url}")
                    
                    user_input = input("Please check the URL. Would you like to send this PDF to the summarizer? (y/n): ")
                    if user_input.lower() == 'y':
                        summary_response = summarize_pdf(pdf_linode_url)
                        if 'summary' in summary_response:
                            summary = summary_response['summary']
                            # Because the summariser gives us \n rather than linebreaks...
                            #save_summary_to_zotero(zot, item['key'], summary)
                            summary_html = summary.replace('\n', '<br><br>')
                            save_summary_to_zotero(zot, item['key'], summary_html)
                        else:
                            error_info = summary_response['error']
                            # the summariser is unfortunately bad at PDFs and often just tells us to try again later, so this catches that:
                            print(f"There was an issue with the summarizer. Error code: {error_info['code']}, Error message: {error_info['msg']}")
                        # after getting the summary, clean up:    
                        delete_pdf(s3, bucket_name, object_name)
                    else:
                        # user didn't want a summary so clean it up
                        print("Skipping summarization for this PDF.")
                        delete_pdf(s3, bucket_name, object_name)  # Optionally, still clean up if not summarizing
                    
# Call the function
get_pdf_attachments(zot)
