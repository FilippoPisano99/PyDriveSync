import os.path
import sys
import mimetypes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly","https://www.googleapis.com/auth/drive.file"]
CREDENTAILS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

MAX_FILES = 10

FOLDER_NAME = sys.argv[1]
FILE_TO_UPLOAD = sys.argv[2]

#====================================================================

def loadGoogleCreds(scopes, credential_file, token_file):
	creds = None
	# The file token.json stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists(token_file):
		creds = Credentials.from_authorized_user_file(token_file, scopes)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				credential_file, scopes
			)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open(token_file, "w") as token:
			token.write(creds.to_json())
	return creds

#====================================================================

def getFolderID(service, folder_name):
	# Call the Drive v3 API
	print(f'Search folder {folder_name} ...',end='')
	results = (
		service.files()
		.list(
			pageSize=10
			, q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
			, fields="files(id, name)"
			)
		.execute()
	)
	items = results.get("files", [])

	print(f'OK',end='\n')
	print(f"FOLDER ID: {items[0]['id']}")
	return items[0]['id']

def searchSyncFiles(service, folder_id):
	print(f'Listing files of Folder {folder_id}')
	results = (
		service.files()
		.list(
			pageSize=10
			, q=f"'{folder_id}' in parents and trashed=false"
			, fields="files(id, name, createdTime, parents)"
			, orderBy="createdTime"
			)
		.execute()
	)
	items = results.get("files", [])

	print(f"Files ({len(items)}):")
	if len(items) > 0:
		print(f"{'NAME'.ljust(30,' ')}{'CREATED TIME'.ljust(30,' ')} ID")
	for item in items:
		print(f"{item['name'].ljust(30,' ')}{item['createdTime'].ljust(30,' ')} ({item['id']})")
	return items

def uploadFile(service, metadata, file_path, mime_type):
	print(f'Upload file {file_path} ...',end='')
	media = MediaFileUpload(file_path, mimetype=mime_type)

	file = (
		service.files()
		.create(
			body=metadata
			, media_body=media
			, fields="id"
		)
		.execute()
	)
	print(f'OK' ,end='\n')
	print(f'File ID: {file.get("id")}')

	return file.get("id")

def deleteFile(service, file_id):
	print(f'Delete file {file_id} ...',end='')
	response = service.files().delete(fileId=file_id).execute()
	print(f'OK' ,end='\n')

#====================================================================
def main():
	
	try:
		creds = loadGoogleCreds(SCOPES,CREDENTAILS_FILE,TOKEN_FILE)
		service = build("drive", "v3", credentials=creds)
		
		folder_id 	= getFolderID(service=service, folder_name=FOLDER_NAME)		
		files		= searchSyncFiles(service=service, folder_id=folder_id)
		
		if len(files) >= MAX_FILES:
			deleteFile(service=service, file_id=files[0]['id'])

		uploadFile(
			service=service
			, metadata={"name": os.path.basename(FILE_TO_UPLOAD), "parents":[folder_id]}
			, file_path=FILE_TO_UPLOAD
			, mime_type=mimetypes.guess_type(FILE_TO_UPLOAD)[0]
		)

		
	except HttpError as error:
		print(f"An error occurred: {error}")


if __name__ == "__main__":
	main()
